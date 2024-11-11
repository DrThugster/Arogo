// src/pages/ConsultationPage.js
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import {
  Container,
  Paper,
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material';
import ChatInterface from '../components/ChatInterface';
import axios from 'axios';

const ConsultationPage = () => {
  const { consultationId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [consultation, setConsultation] = useState(null);

  useEffect(() => {
    const fetchConsultation = async () => {
      try {
        console.log('Fetching consultation:', consultationId);
        const response = await axios.get(`http://localhost:8000/api/consultation/status/${consultationId}`);
        console.log('Consultation data:', response.data);
        
        setConsultation(response.data);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching consultation:', err);
        setError(err.response?.data?.detail || 'Failed to load consultation. Please try again.');
        setLoading(false);
      }
    };

    if (consultationId) {
      fetchConsultation();
    }
  }, [consultationId]);

  const handleEndConsultation = async () => {
    try {
      await axios.get(`http://localhost:8000/api/consultation/summary/${consultationId}`);
      navigate(`/consultation/summary/${consultationId}`);
    } catch (err) {
      setError('Failed to end consultation. Please try again.');
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
        <Button
          variant="contained"
          onClick={() => navigate('/')}
          sx={{ mt: 2 }}
        >
          Return Home
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 2, mb: 2 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            Medical Consultation
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={handleEndConsultation}
          >
            End Consultation
          </Button>
        </Box>
        
        {consultation && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Patient: {consultation.userDetails.firstName} {consultation.userDetails.lastName}
            </Typography>
          </Box>
        )}
      </Paper>

      <ChatInterface
        consultationId={consultationId}
        onError={(error) => setError(error)}
      />
    </Container>
  );
};

export default ConsultationPage;