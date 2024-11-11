# backend/app/utils/report_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
import datetime
import io
import base64
import logging
from app.utils.consultation_helpers import (
    generate_medication_recommendations,
    generate_home_remedies,
    generate_precautions,
    generate_diagnosis_description
)
from app.utils.symptom_analyzer import SymptomAnalyzer

logger = logging.getLogger(__name__)

def create_radar_chart(symptoms):
    """Create radar chart for symptoms."""
    try:
        if not symptoms:
            return None

        plt.close('all')  # Close any existing plots
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(projection='polar'))

        # Extract data
        names = [s['name'] for s in symptoms]
        values = [float(s['intensity']) for s in symptoms]
        
        # Generate angles for the plot
        angles = np.linspace(0, 2*np.pi, len(names), endpoint=False)
        
        # Close the plot by appending first value to end
        values = np.concatenate((values, [values[0]]))
        angles = np.concatenate((angles, [angles[0]]))
        
        # Create plot
        ax.plot(angles, values)
        ax.fill(angles, values, alpha=0.25)
        ax.set_xticks(angles[:-1])  # Don't show the duplicated last angle
        ax.set_xticklabels(names)
        ax.set_title("Symptoms Intensity")

        # Save to buffer
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close('all')
        
        return img_buffer
    except Exception as e:
        logger.error(f"Error creating radar chart: {str(e)}")
        return None

def create_pdf_report(consultation_data):
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph("Medical Consultation Report", title_style))
        story.append(Spacer(1, 12))

        # Header Information
        story.append(Paragraph(f"Consultation ID: {consultation_data.get('consultation_id', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))

        # Patient Information
        story.append(Paragraph("Patient Information", styles['Heading2']))
        user_details = consultation_data.get('userDetails', {})
        patient_data = [
            ["Name", f"{user_details.get('firstName', '')} {user_details.get('lastName', '')}"],
            ["Age", str(user_details.get('age', 'N/A'))],
            ["Gender", user_details.get('gender', 'N/A')],
            ["Height", f"{user_details.get('height', 'N/A')} cm"],
            ["Weight", f"{user_details.get('weight', 'N/A')} kg"]
        ]
        patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(patient_table)
        story.append(Spacer(1, 20))

        # Get analyzed symptoms
        chat_history = consultation_data.get('chatHistory', [])
        symptom_analyzer = SymptomAnalyzer()
        analyzed_symptoms = symptom_analyzer.analyze_symptoms(chat_history)
        severity_score = symptom_analyzer.calculate_severity_score(analyzed_symptoms)
        risk_level = symptom_analyzer.determine_risk_level(analyzed_symptoms)

        # Diagnosis Section
        # Diagnosis Section
        story.append(Paragraph("Diagnosis Summary", styles['Heading2']))
        
        # Get chat history and generate diagnosis description
        chat_history = consultation_data.get('chatHistory', [])
        diagnosis_description = generate_diagnosis_description(chat_history)
        story.append(Paragraph(diagnosis_description, styles['Normal']))
        story.append(Spacer(1, 12))

        # Get analyzed symptoms for further processing
        symptom_analyzer = SymptomAnalyzer()
        analyzed_symptoms = symptom_analyzer.analyze_symptoms(chat_history)
        
        # Severity and Recommendations
        severity_data = [
            ["Severity Score", f"{symptom_analyzer.calculate_severity_score(analyzed_symptoms)}/10"],
            ["Risk Level", symptom_analyzer.determine_risk_level(analyzed_symptoms)],
            ["Recommended Timeframe", symptom_analyzer.recommend_timeframe(analyzed_symptoms)],
            ["Recommended Specialist", symptom_analyzer.recommend_specialist(analyzed_symptoms)]
        ]

    
        severity_table = Table(severity_data, colWidths=[2.5*inch, 3.5*inch])
        severity_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(severity_table)
        story.append(Spacer(1, 20))

        # Symptoms Visualization
        story.append(Paragraph("Symptoms Analysis", styles['Heading2']))
        if analyzed_symptoms:
            chart_buffer = create_radar_chart(analyzed_symptoms)
            if chart_buffer:
                img = Image(chart_buffer, width=4*inch, height=4*inch)
                story.append(img)
            else:
                story.append(Paragraph("Unable to generate symptoms visualization", styles['Normal']))
        else:
            story.append(Paragraph("No symptoms data available for visualization", styles['Normal']))
        story.append(Spacer(1, 20))

        # Recommendations
        story.append(Paragraph("Treatment Recommendations", styles['Heading2']))
        
        # Medications
        story.append(Paragraph("Recommended Medications:", styles['Heading3']))
        medications = generate_medication_recommendations(analyzed_symptoms)
        for med in medications:
            story.append(Paragraph(f"• {med}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Home Remedies
        story.append(Paragraph("Home Remedies:", styles['Heading3']))
        remedies = generate_home_remedies(analyzed_symptoms)
        for remedy in remedies:
            story.append(Paragraph(f"• {remedy}", styles['Normal']))
        story.append(Spacer(1, 12))

        # Precautions
        story.append(Paragraph("Important Precautions", styles['Heading2']))
        precautions = generate_precautions(analyzed_symptoms)
        for precaution in precautions:
            story.append(Paragraph(f"• {precaution}", styles['Normal']))
        story.append(Spacer(1, 12))

        # Chat History
        story.append(Paragraph("Consultation History", styles['Heading2']))
        if chat_history:
            for message in chat_history:
                msg_type = message.get('type', 'unknown')
                content = message.get('content', '')
                timestamp = message.get('timestamp', datetime.datetime.now())
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        pass
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if isinstance(timestamp, datetime.datetime) else str(timestamp)
                role = "Patient" if msg_type == "user" else "Doctor"
                story.append(Paragraph(f"{role} ({timestamp_str}):", styles['Heading4']))
                story.append(Paragraph(content, styles['Normal']))
                story.append(Spacer(1, 6))
        
        # Disclaimer
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey
        )
        story.append(Paragraph(
            "Disclaimer: This is an AI-generated pre-diagnosis report and should not be considered as a replacement for "
            "professional medical advice. Please consult with a healthcare provider for proper medical diagnosis and treatment. "
            "In case of emergency, seek immediate medical attention.",
            disclaimer_style
        ))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    except Exception as e:
        logger.error(f"Error generating PDF report: {str(e)}")
        raise Exception(f"Failed to generate PDF report: {str(e)}")