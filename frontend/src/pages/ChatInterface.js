// frontend/src/pages/ChatInterface.js
import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { addChatMessage } from '../redux/slices/consultationSlice';
import {
  Container,
  Paper,
  Box,
  TextField,
  IconButton,
  Typography,
  CircularProgress,
  Fade,
} from '@mui/material';
import { styled, keyframes } from '@mui/material/styles';
import SendIcon from '@mui/icons-material/Send';
import MicIcon from '@mui/icons-material/Mic';
import StopIcon from '@mui/icons-material/Stop';

// Keyframes for mic animation
const pulse = keyframes`
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.8;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
`;

const AnimatedMicButton = styled(IconButton)(({ theme, isrecording }) => ({
  animation: isrecording === 'true' ? `${pulse} 1.5s infinite` : 'none',
  backgroundColor: isrecording === 'true' ? theme.palette.error.main : theme.palette.primary.main,
  color: 'white',
  '&:hover': {
    backgroundColor: isrecording === 'true' ? theme.palette.error.dark : theme.palette.primary.dark,
  },
}));

const MessageBubble = styled(Paper)(({ theme, isuser }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(1),
  maxWidth: '70%',
  wordWrap: 'break-word',
  backgroundColor: isuser === 'true' ? theme.palette.primary.main : theme.palette.grey[100],
  color: isuser === 'true' ? theme.palette.primary.contrastText : theme.palette.text.primary,
  alignSelf: isuser === 'true' ? 'flex-end' : 'flex-start',
  borderRadius: theme.spacing(2),
}));

const ChatContainer = styled(Box)({
  display: 'flex',
  flexDirection: 'column',
  height: 'calc(100vh - 200px)',
  overflow: 'hidden',
});

const MessagesContainer = styled(Box)({
  flexGrow: 1,
  overflow: 'auto',
  display: 'flex',
  flexDirection: 'column',
  padding: '20px',
  gap: '10px',
});

const ChatInterface = () => {
  const { consultationId } = useParams();
  const dispatch = useDispatch();
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef(null);
  const websocketRef = useRef(null);
  const mediaRecorderRef = useRef(null);

  const chatHistory = useSelector((state) => state.consultation.chatHistory);

  useEffect(() => {
    // Initialize WebSocket connection
    websocketRef.current = new WebSocket(`ws://localhost:8000/ws/${consultationId}`);
    
    websocketRef.current.onmessage = (event) => {
      const response = JSON.parse(event.data);
      dispatch(addChatMessage({
        type: 'bot',
        content: response.message,
        timestamp: new Date().toISOString()
      }));

      // Play audio response if available
      if (response.audioUrl) {
        const audio = new Audio(response.audioUrl);
        audio.play();
      }
    };

    return () => {
      if (websocketRef.current) {
        websocketRef.current.close();
      }
    };
  }, [consultationId, dispatch]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const handleSendMessage = async () => {
    if (!message.trim()) return;

    dispatch(addChatMessage({
      type: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }));

    websocketRef.current.send(JSON.stringify({
      type: 'message',
      content: message
    }));

    setMessage('');
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      const audioChunks = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        setIsProcessing(true);
        
        // Send audio to backend
        const formData = new FormData();
        formData.append('audio', audioBlob);
        
        try {
          const response = await fetch(`http://localhost:8000/api/consultation/speech-to-text`, {
            method: 'POST',
            body: formData,
          });
          
          const data = await response.json();
          if (data.text) {
            setMessage(data.text);
          }
        } catch (error) {
          console.error('Speech to text error:', error);
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <Container maxWidth="md">
      <ChatContainer>
        <Paper elevation={3} sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
          <Typography variant="h6" gutterBottom>
            Medical Consultation
          </Typography>
          
          <MessagesContainer>
            {chatHistory.map((msg, index) => (
              <MessageBubble
                key={index}
                isuser={msg.type === 'user' ? 'true' : 'false'}
                elevation={1}
              >
                <Typography>{msg.content}</Typography>
              </MessageBubble>
            ))}
            <div ref={messagesEndRef} />
          </MessagesContainer>

          <Box sx={{ display: 'flex', gap: 1, p: 2 }}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Type your message..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            />
            
            <AnimatedMicButton
              size="large"
              isrecording={isRecording ? 'true' : 'false'}
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <CircularProgress size={24} color="inherit" />
              ) : isRecording ? (
                <StopIcon />
              ) : (
                <MicIcon />
              )}
            </AnimatedMicButton>

            <IconButton
              color="primary"
              size="large"
              onClick={handleSendMessage}
              disabled={!message.trim()}
            >
              <SendIcon />
            </IconButton>
          </Box>
        </Paper>
      </ChatContainer>
    </Container>
  );
};

export default ChatInterface;