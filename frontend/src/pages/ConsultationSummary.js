// src/pages/ConsultationSummary.js
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Box,
  Typography,
  Button,
  Grid,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts';
import { consultationApi } from '../utils/api';
import { getSeverityColor, downloadBlob } from '../utils/helpers';
import FeedbackForm from '../components/FeedbackForm';

const ConsultationSummary = () => {
  const { consultationId } = useParams();
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showFeedback, setShowFeedback] = useState(false);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await consultationApi.getSummary(consultationId);
        setSummary(data);
      } catch (err) {
        setError('Failed to load consultation summary');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [consultationId]);

  const handleDownloadReport = async () => {
    try {
      const blob = await consultationApi.getReport(consultationId);
      downloadBlob(blob, `consultation-report-${consultationId}.pdf`);
    } catch (err) {
      setError('Failed to download report');
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
      <Container maxWidth="md">
        <Alert severity="error" sx={{ mt: 4 }}>{error}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          Consultation Summary
        </Typography>
        
        <Grid container spacing={3}>
          {/* Patient Details */}
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>Patient Details</Typography>
            <Box sx={{ pl: 2 }}>
              <Typography>
                Name: {summary.userDetails.firstName} {summary.userDetails.lastName}
              </Typography>
              <Typography>
                Age: {summary.userDetails.age}
              </Typography>
              <Typography>
                Gender: {summary.userDetails.gender}
              </Typography>
            </Box>
          </Grid>

          {/* Diagnosis */}
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>Diagnosis</Typography>
            <Typography paragraph>{summary.diagnosis.description}</Typography>
            
            <Box sx={{ mb: 2 }}>
              <Chip
                label={`Severity: ${summary.diagnosis.severityScore}/10`}
                sx={{
                  bgcolor: getSeverityColor(summary.diagnosis.severityScore),
                  color: 'white',
                  mr: 1
                }}
              />
              <Chip
                label={`Risk Level: ${summary.diagnosis.riskLevel}`}
                color="primary"
              />
            </Box>
          </Grid>

          {/* Symptoms Chart */}
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>Symptoms Analysis</Typography>
            <Box sx={{ height: 300 }}>
              <ResponsiveContainer>
                <RadarChart data={summary.diagnosis.symptoms}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="name" />
                  <PolarRadiusAxis domain={[0, 10]} />
                  <Radar
                    name="Intensity"
                    dataKey="intensity"
                    fill="#1976d2"
                    fillOpacity={0.6}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </Box>
          </Grid>

          {/* Recommendations */}
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>Recommendations</Typography>
            <Box sx={{ pl: 2 }}>
              <Typography variant="subtitle1">Medications:</Typography>
              <ul>
                {summary.recommendations.medications.map((med, index) => (
                  <li key={index}>{med}</li>
                ))}
              </ul>
              
              <Typography variant="subtitle1">Home Remedies:</Typography>
              <ul>
                {summary.recommendations.homeRemedies.map((remedy, index) => (
                  <li key={index}>{remedy}</li>
                ))}
              </ul>
            </Box>
          </Grid>

          {/* Actions */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Button
                variant="contained"
                onClick={handleDownloadReport}
                color="primary"
              >
                Download Report
              </Button>
              <Button
                variant="outlined"
                onClick={() => setShowFeedback(true)}
                color="secondary"
              >
                Provide Feedback
              </Button>
              <Button
                variant="outlined"
                onClick={() => navigate('/')}
              >
                Start New Consultation
              </Button>
            </Box>
          </Grid>

          {/* Precautions */}
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>Precautions</Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              Recommended timeframe to see a doctor: {summary.diagnosis.timeframe}
            </Alert>
            <Box sx={{ pl: 2 }}>
              <ul>
                {summary.precautions.map((precaution, index) => (
                  <li key={index}>{precaution}</li>
                ))}
              </ul>
            </Box>
          </Grid>
        </Grid>

        {/* Feedback Dialog */}
        {showFeedback && (
          <FeedbackForm
            consultationId={consultationId}
            onSubmit={() => setShowFeedback(false)}
            onClose={() => setShowFeedback(false)}
          />
        )}
      </Paper>
    </Container>
  );
};

export default ConsultationSummary;