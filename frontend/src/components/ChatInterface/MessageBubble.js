// src/components/ChatInterface/MessageBubble.js
import React from 'react';
import { Paper, Typography, Box } from '@mui/material';
import { styled } from '@mui/material/styles';

const MessageContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: props => props.isUser ? 'flex-end' : 'flex-start',
  marginBottom: theme.spacing(1),
  width: '100%',
}));

const StyledPaper = styled(Paper)(({ theme, isUser }) => ({
  padding: theme.spacing(2),
  maxWidth: '70%',
  backgroundColor: isUser ? theme.palette.primary.main : theme.palette.grey[100],
  color: isUser ? theme.palette.primary.contrastText : theme.palette.text.primary,
  borderRadius: theme.spacing(2),
  borderTopRightRadius: isUser ? theme.spacing(0) : theme.spacing(2),
  borderTopLeftRadius: isUser ? theme.spacing(2) : theme.spacing(0),
}));

const MessageBubble = ({ message }) => {
  const isUser = message.type === 'user';

  return (
    <MessageContainer isUser={isUser}>
      <StyledPaper isUser={isUser} elevation={1}>
        <Typography variant="body1">{message.content}</Typography>
      </StyledPaper>
    </MessageContainer>
  );
};

export default MessageBubble;