// src/utils/api.js
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const consultationApi = {
  startConsultation: async (userData) => {
    const response = await api.post('/api/consultation/start', userData);
    return response.data;
  },

  getSummary: async (consultationId) => {
    const response = await api.get(`/api/consultation/summary/${consultationId}`);
    return response.data;
  },

  getReport: async (consultationId) => {
    const response = await api.get(`/api/consultation/report/${consultationId}`, {
      responseType: 'blob'
    });
    return response.data;
  },

  submitFeedback: async (feedbackData) => {
    const response = await api.post('/api/feedback/submit', feedbackData);
    return response.data;
  },

  speechToText: async (audioBlob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    const response = await api.post('/api/consultation/speech-to-text', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }
};

export const WebSocketService = {
  connect: (consultationId, onMessage, onError) => {
    const ws = new WebSocket(`${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/ws/${consultationId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    ws.onerror = (error) => {
      onError(error);
    };

    return ws;
  }
};

export default api;