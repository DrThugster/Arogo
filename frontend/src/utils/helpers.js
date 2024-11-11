// src/utils/helpers.js
export const formatDate = (date) => {
  return new Date(date).toLocaleString();
};

export const getSeverityColor = (score) => {
  if (score <= 3) return '#4caf50'; // Green
  if (score <= 7) return '#ff9800'; // Orange
  return '#f44336'; // Red
};

export const getConfidenceLabel = (score) => {
  if (score >= 80) return 'High';
  if (score >= 50) return 'Medium';
  return 'Low';
};

export const downloadBlob = (blob, fileName) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', fileName);
  document.body.appendChild(link);
  link.click();
  link.parentNode.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const formatAudioDuration = (seconds) => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

export const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

export const validateMobile = (mobile) => {
  const re = /^\+?[\d\s-]{10,}$/;
  return re.test(mobile);
};

export const generateConsultationId = () => {
  return 'cons-' + Math.random().toString(36).substr(2, 9);
};