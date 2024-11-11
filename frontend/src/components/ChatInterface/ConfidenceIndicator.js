// src/components/ChatInterface/ConfidenceIndicator.js
import React from 'react';
import { Box, Typography, CircularProgress, Tooltip } from '@mui/material';
import { styled } from '@mui/material/styles';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

const IndicatorWrapper = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
}));

const ConfidenceCircle = styled(Box)(({ theme, confidence }) => ({
  position: 'relative',
  display: 'inline-flex',
  alignItems: 'center',
}));

const ConfidenceValue = styled(Typography)(({ theme, confidence }) => ({
  position: 'absolute',
  left: '50%',
  top: '50%',
  transform: 'translate(-50%, -50%)',
  fontSize: '0.75rem',
  fontWeight: 'bold',
  color: confidence >= 70 ? theme.palette.success.main :
         confidence >= 40 ? theme.palette.warning.main :
         theme.palette.error.main,
}));

const ConfidenceIndicator = ({ confidence, size = 40 }) => {
  const getConfidenceColor = (score) => {
    if (score >= 70) return 'success';
    if (score >= 40) return 'warning';
    return 'error';
  };

  const getConfidenceIcon = (score) => {
    if (score >= 70) return <CheckCircleOutlineIcon color="success" />;
    if (score >= 40) return <WarningAmberIcon color="warning" />;
    return <ErrorOutlineIcon color="error" />;
  };

  const getTooltipText = (score) => {
    if (score >= 70) return 'High confidence in analysis';
    if (score >= 40) return 'Moderate confidence - may need verification';
    return 'Low confidence - please provide more details';
  };

  return (
    <Tooltip title={getTooltipText(confidence)} arrow>
      <IndicatorWrapper>
        <ConfidenceCircle confidence={confidence}>
          <CircularProgress
            variant="determinate"
            value={confidence}
            size={size}
            color={getConfidenceColor(confidence)}
          />
          <ConfidenceValue confidence={confidence}>
            {Math.round(confidence)}%
          </ConfidenceValue>
        </ConfidenceCircle>
        {getConfidenceIcon(confidence)}
      </IndicatorWrapper>
    </Tooltip>
  );
};

export default ConfidenceIndicator;