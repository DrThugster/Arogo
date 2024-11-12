from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def create_pdf_report(consultation_data):
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
    # Add custom styles
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#1976d2')
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor('#1976d2')
    ))
    
    story = []
    
    # Header
    story.append(Paragraph("Medical Consultation Report", styles['CustomTitle']))
    story.append(Paragraph(f"Consultation ID: {consultation_data['consultation_id']}", styles['Normal']))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Patient Information
    story.append(Paragraph("Patient Information", styles['SectionTitle']))
    patient_data = [
        ['Name', f"{consultation_data['userDetails']['firstName']} {consultation_data['userDetails']['lastName']}"],
        ['Age', str(consultation_data['userDetails']['age'])],
        ['Gender', consultation_data['userDetails']['gender']],
        ['Height', f"{consultation_data['userDetails']['height']} cm"],
        ['Weight', f"{consultation_data['userDetails']['weight']} kg"]
    ]
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 20))
    

    
    # Diagnosis Summary
    story.append(Paragraph("Diagnosis Summary", styles['SectionTitle']))
    symptoms_text = "Based on your reported symptoms:\n"
    for symptom in consultation_data['diagnosis']['symptoms']:
        symptoms_text += f"- {symptom['name']}: {symptom['severity']}/10 intensity with {symptom.get('confidence', 'N/A')}% confidence\n"
    story.append(Paragraph(symptoms_text, styles['Normal']))
    story.append(Spacer(1, 10))
    
    diagnosis_data = [
        ['Severity Score', f"{consultation_data['diagnosis']['severityScore']}/10"],
        ['Risk Level', consultation_data['diagnosis']['riskLevel']],
        ['Recommended Timeframe', consultation_data['diagnosis']['timeframe']],
        ['Recommended Specialist', consultation_data['diagnosis']['recommendedDoctor']]
    ]
    diagnosis_table = Table(diagnosis_data, colWidths=[2*inch, 4*inch])
    diagnosis_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(diagnosis_table)
    story.append(Spacer(1, 20))

    # Add Safety Concerns section
    if consultation_data['recommendations'].get('safety_concerns'):
        story.append(Paragraph("Safety Concerns", styles['SectionTitle']))
        for concern in consultation_data['recommendations']['safety_concerns']:
            story.append(Paragraph(f"• {concern}", styles['Normal']))
        story.append(Spacer(1, 20))

     # Add Urgency Level
    story.append(Paragraph("Urgency Level", styles['SectionTitle']))
    story.append(Paragraph(f"Level: {consultation_data['recommendations']['urgency']}", styles['Normal']))
    story.append(Spacer(1, 20))

    # Add Symptoms Analysis with confidence levels
    story.append(Paragraph("Detailed Symptoms Analysis", styles['SectionTitle']))
    for symptom in consultation_data['diagnosis']['symptoms']:
        confidence_text = f" (Confidence: {symptom.get('confidence', 'N/A')}%)" if 'confidence' in symptom else ""
        story.append(Paragraph(
            f"• {symptom['name']}: {symptom.get('severity', symptom.get('intensity', 0))}/10{confidence_text}",
            styles['Normal']
        ))
    story.append(Spacer(1, 20))

     # Create radar chart
    def create_symptoms_chart(symptoms):
        # Get symptom names and intensities
        names = [symptom['name'] for symptom in symptoms]
        values = [symptom.get('severity', symptom.get('intensity', 0)) for symptom in symptoms]
        
        # Number of variables
        num_vars = len(names)
        
        # Compute angle for each axis
        angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
        angles += angles[:1]
        values += values[:1]
        
        # Initialize the spider plot
        fig, ax = plt.subplots(figsize=(4, 5), subplot_kw=dict(projection='polar'))
        
        # Plot data
        ax.plot(angles, values)
        ax.fill(angles, values, alpha=0.25)
        
        # Set the labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(names)
        
        # Save to buffer
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        plt.close()
        
        return img_buffer
    # Add chart to PDF after symptoms section
    if consultation_data['diagnosis']['symptoms']:
        chart_buffer = create_symptoms_chart(consultation_data['diagnosis']['symptoms'])
        story.append(Paragraph("Symptoms Analysis Chart", styles['SectionTitle']))
        story.append(Image(chart_buffer, width=250, height=200))
        story.append(Spacer(1, 20))
    

    # Add Follow-up Information
    story.append(Paragraph("Follow-up Information", styles['SectionTitle']))
    story.append(Paragraph(f"Recommended Timeframe: {consultation_data['diagnosis']['timeframe']}", styles['Normal']))
    story.append(Spacer(1, 20))

    
    # Treatment Recommendations
    story.append(Paragraph("Treatment Recommendations", styles['SectionTitle']))
    story.append(Paragraph("Recommended Medications:", styles['Heading4']))
    for med in consultation_data['recommendations']['medications']:
        story.append(Paragraph(f"• {med}", styles['Normal']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Home Remedies:", styles['Heading4']))
    for remedy in consultation_data['recommendations']['homeRemedies']:
        story.append(Paragraph(f"• {remedy}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Important Precautions
    story.append(Paragraph("Important Precautions", styles['SectionTitle']))
    for precaution in consultation_data['precautions']:
        story.append(Paragraph(f"• {precaution}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Disclaimer
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    disclaimer_text = """This is an AI-generated pre-diagnosis report and should not be considered as a replacement for professional medical advice. 
    Please consult with a healthcare provider for proper medical diagnosis and treatment. 
    In case of emergency, seek immediate medical attention."""
    story.append(Paragraph(disclaimer_text, disclaimer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer