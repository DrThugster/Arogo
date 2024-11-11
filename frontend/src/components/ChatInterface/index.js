// src/components/ChatInterface/index.js
import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import {
  Container,
  Paper,
  Box,
  TextField,
  IconButton,
  Typography,
  CircularProgress,
  Alert,
  Fab,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import MicIcon from '@mui/icons-material/Mic';
import { styled, keyframes } from '@mui/material/styles';
import MessageBubble from './MessageBubble';
import VoiceVisualizer from './VoiceVisualizer';

// Keyframes for mic animation
const pulse = keyframes`
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(25, 118, 210, 0.4);
  }
  70% {
    transform: scale(1.1);
    box-shadow: 0 0 0 15px rgba(25, 118, 210, 0);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(25, 118, 210, 0);
  }
`;

const AnimatedMicButton = styled(Fab)(({ theme, isrecording }) => ({
  position: 'absolute',
  bottom: theme.spacing(3),
  right: theme.spacing(3),
  width: 64,
  height: 64,
  animation: isrecording === 'true' ? `${pulse} 1.5s infinite` : 'none',
  backgroundColor: isrecording === 'true' ? theme.palette.error.main : theme.palette.primary.main,
  color: theme.palette.common.white,
  '&:hover': {
    backgroundColor: isrecording === 'true' ? theme.palette.error.dark : theme.palette.primary.dark,
  },
  '& svg': {
    width: 28,
    height: 28,
  },
}));

const ChatContainer = styled(Box)({
  position: 'relative',
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
});

const MessagesContainer = styled(Box)(({ theme }) => ({
  flexGrow: 1,
  overflow: 'auto',
  padding: theme.spacing(2),
  display: 'flex',
  flexDirection: 'column',
  gap: theme.spacing(2),
  '&::-webkit-scrollbar': {
    width: '8px',
  },
  '&::-webkit-scrollbar-track': {
    background: theme.palette.grey[100],
    borderRadius: '4px',
  },
  '&::-webkit-scrollbar-thumb': {
    background: theme.palette.grey[400],
    borderRadius: '4px',
  },
}));

const ChatInterface = () => {
  const { consultationId } = useParams();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [wsInstance, setWsInstance] = useState(null);
  const [wsError, setWsError] = useState(null);
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioPlayerRef = useRef(null);

  const detectSilence = (stream, onSilence, silenceDelay = 2000, minDecibels = -45) => {
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const microphone = audioContext.createMediaStreamSource(stream);
    const scriptProcessor = audioContext.createScriptProcessor(2048, 1, 1);

    analyser.minDecibels = minDecibels;

    microphone.connect(analyser);
    analyser.connect(scriptProcessor);
    scriptProcessor.connect(audioContext.destination);

    let lastSound = Date.now();
    scriptProcessor.addEventListener('audioprocess', () => {
      const array = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(array);
      const arraySum = array.reduce((a, value) => a + value, 0);
      const average = arraySum / array.length;

      if (average > 0) {
        lastSound = Date.now();
      } else if (Date.now() - lastSound > silenceDelay) {
        onSilence();
        microphone.disconnect();
        scriptProcessor.disconnect();
        audioContext.close();
      }
    });
  };

  useEffect(() => {
    const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/ws/${consultationId}`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket Connected');
      setWsError(null);
    };

    ws.onmessage = async (event) => {
      try {
        console.log('Received message:', event.data);
        const data = JSON.parse(event.data);
        
        // Add message to chat
        setMessages(prev => [...prev, {
          type: data.type || 'bot',
          content: data.content,
          timestamp: new Date(data.timestamp || Date.now())
        }]);

        // Play audio if available
        if (data.audio) {
          const audio = new Audio(`data:audio/mp3;base64,${data.audio}`);
          audioPlayerRef.current = audio;
          try {
            await audio.play();
          } catch (error) {
            console.error('Error playing audio:', error);
          }
        }

      } catch (error) {
        console.error('Error processing message:', error);
        setWsError('Error processing message');
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsError('Connection error occurred');
    };

    ws.onclose = () => {
      console.log('WebSocket Disconnected');
      setWsError('Connection closed. Please refresh the page.');
    };

    setWsInstance(ws);

    return () => {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
      }
      if (ws) {
        ws.close();
      }
    };
  }, [consultationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        try {
          setIsProcessing(true);
          
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append('audio', audioBlob, 'recording.webm');

          console.log('Sending audio data to server...');
          
          const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/consultation/speech-to-text`, {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
          }

          const data = await response.json();
          console.log('Server response:', data);

          if (data.text) {
            handleSendMessage(data.text);
          }
        } catch (error) {
          console.error('Speech to text error:', error);
          setWsError('Failed to process voice input: ' + error.message);
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);

      detectSilence(stream, () => {
        if (mediaRecorderRef.current?.state === 'recording') {
          stopRecording();
        }
      });

    } catch (error) {
      console.error('Error accessing microphone:', error);
      setWsError('Failed to access microphone: ' + error.message);
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleSendMessage = (text = inputMessage) => {
    if (!text.trim() || !wsInstance) return;

    const message = {
      type: 'message',
      content: text.trim()
    };

    console.log('Sending message:', message);

    try {
      setMessages(prev => [...prev, {
        type: 'user',
        content: text.trim(),
        timestamp: new Date()
      }]);

      wsInstance.send(JSON.stringify(message));
      setInputMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
      setWsError('Failed to send message: ' + error.message);
    }
  };

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ height: 'calc(100vh - 100px)', p: 2 }}>
        <ChatContainer>
          {wsError && (
            <Alert severity="error" onClose={() => setWsError(null)} sx={{ mb: 2 }}>
              {wsError}
            </Alert>
          )}

          <MessagesContainer>
            {messages.map((message, index) => (
              <MessageBubble 
                key={index} 
                message={message}
                isUser={message.type === 'user'}
              />
            ))}
            <div ref={messagesEndRef} />
          </MessagesContainer>

          <Box sx={{ display: 'flex', gap: 1, mb: isRecording ? 8 : 0 }}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Type your message..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              disabled={isRecording || isProcessing}
            />

            <IconButton
              color="primary"
              onClick={() => handleSendMessage()}
              disabled={!inputMessage.trim() || isProcessing}
            >
              {isProcessing ? <CircularProgress size={24} /> : <SendIcon />}
            </IconButton>
          </Box>

          {isRecording && (
            <Box sx={{ position: 'absolute', bottom: 80, left: 0, right: 0, px: 2 }}>
              <VoiceVisualizer />
            </Box>
          )}

          <AnimatedMicButton
            isrecording={isRecording.toString()}
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isProcessing}
            color={isRecording ? "error" : "primary"}
          >
            <MicIcon />
          </AnimatedMicButton>
        </ChatContainer>
      </Paper>
    </Container>
  );
};

export default ChatInterface;