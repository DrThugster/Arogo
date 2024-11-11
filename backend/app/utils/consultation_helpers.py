# backend/app/utils/consultation_helpers.py
from typing import List, Dict
from app.utils.symptom_analyzer import SymptomAnalyzer

# Create an instance of SymptomAnalyzer to use its methods
analyzer = SymptomAnalyzer()

def generate_medication_recommendations(symptoms: List[Dict]) -> List[str]:
    """
    Generate medication recommendations based on symptoms.
    """
    recommendations = []
    symptom_meds = {
        'headache': ['Acetaminophen', 'Ibuprofen'],
        'fever': ['Acetaminophen', 'Ibuprofen'],
        'cough': ['Dextromethorphan', 'Expectorant'],
        'allergies': ['Antihistamine', 'Nasal Decongestant'],
        'pain': ['Pain Reliever', 'Anti-inflammatory medication'],
        'nausea': ['Anti-nausea medication'],
        'indigestion': ['Antacid'],
        'anxiety': ['Consult doctor for appropriate medication'],
        'insomnia': ['Consult doctor for sleep medication']
    }

    for symptom in symptoms:
        for key, meds in symptom_meds.items():
            if key in symptom['name'].lower():
                recommendations.extend(meds)

    # Remove duplicates while preserving order
    return list(dict.fromkeys(recommendations))

def generate_home_remedies(symptoms: List[Dict]) -> List[str]:
    """
    Generate home remedy recommendations based on symptoms.
    """
    remedies = []
    symptom_remedies = {
        'headache': [
            'Rest in a quiet, dark room',
            'Apply cold or warm compress',
            'Stay hydrated'
        ],
        'fever': [
            'Rest and get plenty of sleep',
            'Stay hydrated',
            'Use a light blanket if chills occur'
        ],
        'cough': [
            'Drink warm honey and lemon tea',
            'Use a humidifier',
            'Stay hydrated'
        ],
        'sore throat': [
            'Gargle with warm salt water',
            'Drink warm liquids',
            'Use throat lozenges'
        ],
        'nausea': [
            'Eat small, frequent meals',
            'Avoid strong odors',
            'Try ginger tea'
        ],
        'stress': [
            'Practice deep breathing exercises',
            'Try meditation or yoga',
            'Get regular exercise'
        ]
    }

    for symptom in symptoms:
        for key, remedies_list in symptom_remedies.items():
            if key in symptom['name'].lower():
                remedies.extend(remedies_list)

    return list(dict.fromkeys(remedies))

def generate_precautions(symptoms: List[Dict]) -> List[str]:
    """
    Generate precautions based on symptoms and severity.
    """
    # Use SymptomAnalyzer instance to calculate severity
    severity_score = analyzer.calculate_severity_score(symptoms)
    
    precautions = [
        "Monitor your symptoms regularly",
        "Keep track of any changes in symptom intensity",
        "Maintain good hygiene practices"
    ]

    if severity_score > 7:
        precautions.extend([
            "Seek immediate medical attention if symptoms worsen",
            "Avoid strenuous activities",
            "Have someone stay with you or check on you regularly"
        ])
    elif severity_score > 4:
        precautions.extend([
            "Limit daily activities as needed",
            "Get adequate rest",
            "Contact healthcare provider if symptoms persist"
        ])

    symptom_precautions = {
        'fever': [
            "Monitor temperature regularly",
            "Stay hydrated",
            "Avoid exposure to extreme temperatures"
        ],
        'breathing': [
            "Avoid smoke and other irritants",
            "Keep head elevated while resting",
            "Use prescribed inhaler if available"
        ],
        'pain': [
            "Avoid movements that aggravate the pain",
            "Apply ice/heat as recommended",
            "Take prescribed medication as directed"
        ]
    }

    for symptom in symptoms:
        for key, specific_precautions in symptom_precautions.items():
            if key in symptom['name'].lower():
                precautions.extend(specific_precautions)

    return list(dict.fromkeys(precautions))

def generate_diagnosis_description(chat_history: List[Dict]) -> str:
    """
    Generate a comprehensive diagnosis description based on chat history.
    """
    # Use SymptomAnalyzer instance to analyze symptoms
    symptoms = analyzer.analyze_symptoms(chat_history)
    severity_score = analyzer.calculate_severity_score(symptoms)
    risk_level = analyzer.determine_risk_level(symptoms)

    # Create a structured diagnosis description
    description = "Based on the reported symptoms:\n\n"

    # Add symptoms overview
    description += "Primary Symptoms:\n"
    for symptom in symptoms:
        intensity_description = "mild" if symptom['intensity'] <= 3 else \
                              "moderate" if symptom['intensity'] <= 7 else "severe"
        description += f"- {symptom['name']}: {intensity_description} "
        description += f"(intensity: {symptom['intensity']}/10)\n"

    # Add overall assessment
    description += f"\nOverall Assessment:\n"
    description += f"The symptoms indicate a {risk_level.lower()} condition. "
    
    if severity_score <= 3:
        description += "The condition appears to be mild and can likely be managed with "
        description += "home care and over-the-counter medications. "
    elif severity_score <= 7:
        description += "The condition requires attention and monitoring. "
        description += "Medical consultation is recommended for proper evaluation. "
    else:
        description += "The condition requires prompt medical attention. "
        description += "Please seek professional medical care soon. "

    return description