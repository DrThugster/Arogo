// src/pages/ConsultationSummary.js
import React, { useState, useEffect, useRef } from 'react';
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
  Divider,
  useTheme,
  ThemeProvider,
  createTheme
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
import { downloadBlob } from '../utils/helpers';
import { styled } from '@mui/material/styles';

// First, let's make sure FeedbackForm is properly imported
// Assuming FeedbackForm is in the components directory
import FeedbackForm from '../components/FeedbackForm';

// Helper function for severity colors
const getSeverityColor = (score) => {
  if (score <= 3) return '#4caf50'; // Green
  if (score <= 7) return '#ff9800'; // Orange
  return '#f44336'; // Red
};

// Styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  marginTop: theme.spacing(4),
  marginBottom: theme.spacing(4),
}));


const ConsultationSummary = () => {
  const { consultationId } = useParams();
  const navigate = useNavigate();
  const theme = useTheme();
  const audioRef = useRef(null);

  // State Management
  const [summary, setSummary] = useState({
    userDetails: {
      firstName: '',
      lastName: '',
      age: '',
      gender: '',
      height: '',
      weight: '',
      email: '',
      mobile: ''
    },
    diagnosis: {
      symptoms: [],
      description: '',
      severityScore: 0,
      riskLevel: '',
      timeframe: '',
      recommendedDoctor: ''
    },
    recommendations: {
      medications: [],
      homeRemedies: [],
      urgency: '',
      safety_concerns: [],
      suggested_improvements: []
    },
    precautions: [],
    created_at: new Date().toISOString()
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showFeedback, setShowFeedback] = useState(false);

  // Format date helper function
  const formatDate = (date) => {
    return new Date(date).toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Fetch summary data
  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await consultationApi.getSummary(consultationId);
        console.log('Summary Data:', data);

        // Transform symptoms data for radar chart if needed
        const transformedSymptoms = data.diagnosis?.symptoms?.map(symptom => ({
          ...symptom,
          intensity: parseInt(symptom.severity || symptom.intensity || 0, 10)
        })) || [];

        setSummary(prevSummary => ({
          ...prevSummary,
          ...data,
          diagnosis: {
            ...data.diagnosis,
            symptoms: transformedSymptoms
          },
          userDetails: data.userDetails || {},
          recommendations: data.recommendations || {}
        }));

        // Handle audio if present
        if (data.audio) {
          audioRef.current = new Audio(`data:audio/mp3;base64,${data.audio}`);
          try {
            await audioRef.current.play();
          } catch (error) {
            console.error('Error playing audio:', error);
          }
        }

      } catch (err) {
        console.error('Error fetching summary:', err);
        setError('Failed to load consultation summary');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();

    // Cleanup function
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, [consultationId]);

  // Handle report download
  const handleDownloadReport = async () => {
    try {
      setLoading(true);
      const blob = await consultationApi.getReport(consultationId);
      downloadBlob(blob, `consultation-report-${consultationId}.pdf`);
    } catch (err) {
      console.error('Error downloading report:', err);
      setError('Failed to download report');
    } finally {
      setLoading(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress size={60} thickness={4} />
      </Box>
    );
  }

  // Error state
  if (error) {
    return (
      <Container maxWidth="md">
        <Alert 
          severity="error" 
          sx={{ mt: 4 }}
          action={
            <Button color="inherit" onClick={() => navigate('/')}>
              Return Home
            </Button>
          }
        >
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        {/* Header Section */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" gutterBottom sx={{ color: 'primary.main', fontWeight: 'bold' }}>
            Medical Consultation Summary
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            Consultation ID: {consultationId}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            Date: {formatDate(summary.created_at)}
          </Typography>
          <Divider sx={{ mt: 2 }} />
        </Box>

        <Grid container spacing={4}>
          {/* Patient Details Section */}
          <Grid item xs={12}>
            <Typography variant="h5" gutterBottom sx={{ color: 'primary.main' }}>
              Patient Details
            </Typography>
            <Box sx={{ pl: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography>
                    <strong>Name:</strong> {summary.userDetails.firstName} {summary.userDetails.lastName}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography>
                    <strong>Age:</strong> {summary.userDetails.age}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography>
                    <strong>Gender:</strong> {summary.userDetails.gender}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography>
                    <strong>Height:</strong> {summary.userDetails.height} cm
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography>
                    <strong>Weight:</strong> {summary.userDetails.weight} kg
                  </Typography>
                </Grid>
              </Grid>
            </Box>
          </Grid>

          {/* Diagnosis Section */}
          <Grid item xs={12}>
            <Typography variant="h5" gutterBottom sx={{ color: 'primary.main' }}>
              Diagnosis Summary
            </Typography>
            <Box sx={{ pl: 2 }}>
              {summary.diagnosis.symptoms.length > 0 && (
                <>
                  <Typography variant="subtitle1" gutterBottom>
                    Reported Symptoms:
                  </Typography>
                  {summary.diagnosis.symptoms.map((symptom, index) => (
                    <Typography key={index} sx={{ mb: 1 }}>
                      • {symptom.name}: {symptom.intensity || symptom.severity}/10
                      {symptom.confidence && ` (Confidence: ${symptom.confidence}%)`}
                    </Typography>
                  ))}
                </>
              )}
              
              <Box sx={{ mt: 2 }}>
                <Typography>
                  <strong>Severity Score:</strong>{' '}
                  <span style={{ color: getSeverityColor(summary.diagnosis.severityScore) }}>
                    {summary.diagnosis.severityScore}/10
                  </span>
                </Typography>
                <Typography>
                  <strong>Risk Level:</strong> {summary.diagnosis.riskLevel}
                </Typography>
                <Typography>
                  <strong>Recommended Timeframe:</strong> {summary.diagnosis.timeframe}
                </Typography>
                <Typography>
                  <strong>Recommended Specialist:</strong> {summary.diagnosis.recommendedDoctor}
                </Typography>
              </Box>
            </Box>
          </Grid>

          {/* Symptoms Chart */}
          {summary.diagnosis.symptoms.length > 0 && (
            <Grid item xs={12}>
              <Typography variant="h5" gutterBottom sx={{ color: 'primary.main' }}>
                Symptoms Analysis
              </Typography>
              <Box sx={{ height: 300, width: '100%' }}>
                <ResponsiveContainer>
                  <RadarChart data={summary.diagnosis.symptoms}>
                    <PolarGrid gridType="circle" />
                    <PolarAngleAxis dataKey="name" />
                    <PolarRadiusAxis domain={[0, 10]}  tickCount={6}/>
                    <Radar
                      name="Intensity"
                      dataKey="intensity"
                      fill={theme.palette.primary.main}
                      fillOpacity={0.6}
                      stroke={theme.palette.primary.main}
                      strokeWidth={2}

                    />
                  </RadarChart>
                </ResponsiveContainer>
              </Box>
            </Grid>
          )}

          {/* Recommendations Section */}
          <Grid item xs={12}>
            <Typography variant="h5" gutterBottom sx={{ color: 'primary.main' }}>
              Treatment Recommendations
            </Typography>
            <Box sx={{ pl: 2 }}>
              <Typography variant="h6" gutterBottom>
                Medications:
              </Typography>
              <ul>
                {summary.recommendations.medications?.map((med, index) => (
                  <li key={index}>
                    <Typography>{med}</Typography>
                  </li>
                ))}
              </ul>

              <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                Home Remedies:
              </Typography>
              <ul>
                {summary.recommendations.homeRemedies?.map((remedy, index) => (
                  <li key={index}>
                    <Typography>{remedy}</Typography>
                  </li>
                ))}
              </ul>

              <Typography variant="subtitle1" sx={{ mt: 2 }}>
                <strong>Urgency Level:</strong> {summary.recommendations.urgency}
              </Typography>
            </Box>
          </Grid>

          {/* Safety Concerns Section */}
          {summary.recommendations.safety_concerns?.length > 0 && (
            <Grid item xs={12}>
              <Typography variant="h5" gutterBottom sx={{ color: 'primary.main' }}>
                Safety Concerns
              </Typography>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Please pay attention to the following safety concerns:
              </Alert>
              <Box sx={{ pl: 2 }}>
                <ul>
                  {summary.recommendations.safety_concerns.map((concern, index) => (
                    <li key={index}>
                      <Typography>{concern}</Typography>
                    </li>
                  ))}
                </ul>
              </Box>
            </Grid>
          )}

          {/* Precautions Section */}
          <Grid item xs={12}>
            <Typography variant="h5" gutterBottom sx={{ color: 'primary.main' }}>
              Precautions & Follow-up
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              Recommended timeframe to see a doctor: {summary.diagnosis.timeframe}
            </Alert>
            <Box sx={{ pl: 2 }}>
              <ul>
                {summary.precautions?.length > 0 ? (
                  summary.precautions.map((precaution, index) => (
                    <li key={index}>
                      <Typography>{precaution}</Typography>
                    </li>
                  ))
                ) : (
                  <Typography>No specific precautions provided</Typography>
                )}
              </ul>
            </Box>
          </Grid>

          {/* Actions Section */}
          <Grid item xs={12}>
            <Box sx={{ 
              display: 'flex', 
              gap: 2, 
              justifyContent: 'center',
              mt: 4,
              mb: 2 
            }}>
              <Button
                variant="contained"
                onClick={handleDownloadReport}
                color="primary"
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} /> : 'Download Report'}
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
        </Grid>

        {/* Disclaimer */}
        <Box sx={{ mt: 4, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary" align="center">
            This is an AI-generated pre-diagnosis report and should not be considered as a replacement for professional medical advice. 
            Please consult with a healthcare provider for proper medical diagnosis and treatment. 
            In case of emergency, seek immediate medical attention.
          </Typography>
        </Box>

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