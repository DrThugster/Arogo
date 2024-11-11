// src/components/ChatInterface/VoiceVisualizer.js
import React, { useEffect, useRef } from 'react';
import { Box } from '@mui/material';
import { styled, keyframes } from '@mui/material/styles';

const Container = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '3px',
  height: '40px',
  padding: theme.spacing(1),
}));

const pulse = keyframes`
  0%, 100% { transform: scaleY(0.3); }
  50% { transform: scaleY(1); }
`;

const Bar = styled(Box)(({ theme, delay }) => ({
  width: '3px',
  height: '100%',
  backgroundColor: theme.palette.primary.main,
  animation: `${pulse} 1.5s ease-in-out infinite`,
  animationDelay: `${delay}ms`,
  transformOrigin: '50% 50%',
}));

const VoiceVisualizer = ({ isRecording }) => {
  const analyzerRef = useRef(null);
  const animationRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (isRecording) {
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          const audioContext = new (window.AudioContext || window.webkitAudioContext)();
          analyzerRef.current = audioContext.createAnalyser();
          const source = audioContext.createMediaStreamSource(stream);
          source.connect(analyzerRef.current);
          analyzerRef.current.fftSize = 256;
          
          const draw = () => {
            const bufferLength = analyzerRef.current.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            analyzerRef.current.getByteFrequencyData(dataArray);
            
            if (canvasRef.current) {
              const canvas = canvasRef.current;
              const ctx = canvas.getContext('2d');
              ctx.clearRect(0, 0, canvas.width, canvas.height);
              
              const barWidth = (canvas.width / bufferLength) * 2.5;
              let x = 0;
              
              for (let i = 0; i < bufferLength; i++) {
                const barHeight = (dataArray[i] / 255) * canvas.height;
                ctx.fillStyle = `rgb(29, 117, 212)`;
                ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                x += barWidth + 1;
              }
            }
            
            animationRef.current = requestAnimationFrame(draw);
          };
          
          draw();
        })
        .catch(err => console.error('Error accessing microphone:', err));
    } else {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (canvasRef.current) {
        const ctx = canvasRef.current.getContext('2d');
        ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
      }
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isRecording]);

  if (!isRecording) {
    return null;
  }

  return (
    <Box sx={{ width: '100%', height: '40px', position: 'relative' }}>
      <canvas
        ref={canvasRef}
        width={200}
        height={40}
        style={{
          width: '100%',
          height: '100%',
        }}
      />
      <Container>
        {[...Array(5)].map((_, i) => (
          <Bar key={i} delay={i * 100} />
        ))}
      </Container>
    </Box>
  );
};

export default VoiceVisualizer;