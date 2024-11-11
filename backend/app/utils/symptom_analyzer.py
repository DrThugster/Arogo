# backend/app/utils/symptom_analyzer.py
from typing import Dict, List
import re
from collections import defaultdict

class SymptomAnalyzer:
    def __init__(self):
        self.symptom_patterns = {
            'consistency': 0.4,
            'detail_level': 0.3,
            'intensity': 0.3
        }

    def analyze_symptoms(self, chat_history: List[Dict]) -> List[Dict]:
        symptoms = defaultdict(lambda: {
            'mentions': 0,
            'details': [],
            'intensity_scores': [],
            'confidence_score': 0
        })
        
        for message in chat_history:
            if message.get('type') == 'user':
                self._process_message(message.get('content', ''), symptoms)
        
        return self._calculate_confidence_scores(symptoms)

    def generate_diagnosis_description(self, analyzed_symptoms: List[Dict]) -> str:
        if not analyzed_symptoms:
            return "No symptoms were identified during the consultation."
        
        description = "Based on your reported symptoms:\n\n"
        
        for symptom in analyzed_symptoms:
            confidence = symptom.get('confidence_score', 0)
            intensity = symptom.get('intensity', 0)
            
            severity = "mild" if intensity <= 3 else "moderate" if intensity <= 7 else "severe"
            confidence_level = "low" if confidence < 50 else "moderate" if confidence < 80 else "high"
            
            description += f"- {symptom['name']}: {severity} intensity ({intensity}/10)"
            description += f" with {confidence_level} confidence ({confidence}%)\n"
        
        return description

    def calculate_severity_score(self, analyzed_symptoms: List[Dict]) -> int:
        if not analyzed_symptoms:
            return 0
            
        total_score = sum(
            symptom.get('intensity', 0) * (symptom.get('confidence_score', 0) / 100)
            for symptom in analyzed_symptoms
        )
        
        return round(min(10, max(1, total_score / len(analyzed_symptoms))))

    def determine_risk_level(self, analyzed_symptoms: List[Dict]) -> str:
        severity_score = self.calculate_severity_score(analyzed_symptoms)
        
        if severity_score <= 3:
            return "Low Risk"
        elif severity_score <= 7:
            return "Medium Risk"
        else:
            return "High Risk"

    def recommend_timeframe(self, analyzed_symptoms: List[Dict]) -> str:
        severity_score = self.calculate_severity_score(analyzed_symptoms)
        
        if severity_score <= 3:
            return "Within 2 weeks"
        elif severity_score <= 5:
            return "Within 1 week"
        elif severity_score <= 7:
            return "Within 48 hours"
        elif severity_score <= 9:
            return "Within 24 hours"
        else:
            return "Immediate medical attention recommended"

    def recommend_specialist(self, analyzed_symptoms: List[Dict]) -> str:
        if not analyzed_symptoms:
            return "General Practitioner"
            
        specialist_mapping = {
            'head': 'Neurologist',
            'headache': 'Neurologist',
            'migraine': 'Neurologist',
            'chest': 'Cardiologist',
            'heart': 'Cardiologist',
            'breath': 'Pulmonologist',
            'stomach': 'Gastroenterologist',
            'skin': 'Dermatologist',
            'joint': 'Orthopedist',
            'anxiety': 'Psychiatrist',
            'depression': 'Psychiatrist'
        }
        
        specialist_counts = defaultdict(int)
        for symptom in analyzed_symptoms:
            for key, specialist in specialist_mapping.items():
                if key in symptom['name'].lower():
                    specialist_counts[specialist] += 1
        
        if not specialist_counts:
            return "General Practitioner"
        
        return max(specialist_counts.items(), key=lambda x: x[1])[0]

    def generate_medication_recommendations(self, analyzed_symptoms: List[Dict]) -> List[str]:
        if not analyzed_symptoms:
            return ["Please consult a healthcare provider for appropriate medication recommendations."]
            
        recommendations = set()
        for symptom in analyzed_symptoms:
            symptom_name = symptom['name'].lower()
            intensity = symptom.get('intensity', 5)
            
            if 'headache' in symptom_name or 'pain' in symptom_name:
                recommendations.add("Over-the-counter pain relievers like acetaminophen or ibuprofen")
            if 'fever' in symptom_name:
                recommendations.add("Fever reducers (acetaminophen)")
            if 'nausea' in symptom_name:
                recommendations.add("Anti-nausea medication")
            
        if not recommendations:
            recommendations.add("Consult with a healthcare provider for specific medication recommendations")
            
        return list(recommendations)

    def generate_home_remedies(self, analyzed_symptoms: List[Dict]) -> List[str]:
        if not analyzed_symptoms:
            return ["Rest and monitor your condition"]
            
        remedies = set()
        for symptom in analyzed_symptoms:
            symptom_name = symptom['name'].lower()
            
            if 'headache' in symptom_name:
                remedies.add("Rest in a quiet, dark room")
                remedies.add("Apply a cold or warm compress")
            if 'nausea' in symptom_name:
                remedies.add("Stay hydrated with clear fluids")
                remedies.add("Try ginger tea or peppermint")
            
        remedies.add("Get adequate rest")
        remedies.add("Stay hydrated")
        
        return list(remedies)

    def generate_precautions(self, analyzed_symptoms: List[Dict]) -> List[str]:
        precautions = [
            "Monitor your symptoms and seek immediate medical attention if they worsen",
            "Keep track of any changes in your symptoms",
            "Stay well-hydrated and get adequate rest"
        ]
        
        severity_score = self.calculate_severity_score(analyzed_symptoms)
        if severity_score > 7:
            precautions.extend([
                "Avoid strenuous activities",
                "Have someone stay with you or check on you regularly",
                "Keep emergency contact numbers handy"
            ])
            
        return precautions

    # Keep existing _process_message and _calculate_confidence_scores methods

    def _process_message(self, message: str, symptoms: Dict) -> None:
        """Process individual messages for symptom information."""
        # Extract symptom mentions with details
        pattern = r'(mild|moderate|severe)?\s*(\w+(?:\s+\w+)?)\s*(pain|ache|discomfort|feeling)?\s*(?:intensity|level)?\s*(\d+)?'
        matches = re.finditer(pattern, message.lower())

        for match in matches:
            severity, symptom_name, type_desc, intensity = match.groups()
            
            if symptom_name in ['the', 'and', 'or', 'my', 'a']:
                continue

            symptom_data = symptoms[symptom_name]
            symptom_data['mentions'] += 1
            
            # Record detail level
            details = []
            if severity:
                details.append('severity_mentioned')
            if type_desc:
                details.append('type_described')
            if intensity:
                details.append('intensity_specified')
                symptom_data['intensity_scores'].append(int(intensity))
            
            symptom_data['details'].extend(details)

    def _calculate_confidence_scores(self, symptoms: Dict) -> List[Dict]:
        """Calculate final confidence scores for symptoms."""
        analyzed_symptoms = []

        for symptom_name, data in symptoms.items():
            # Calculate component scores
            consistency_score = min(data['mentions'] / 3, 1.0)  # Normalize mentions
            detail_score = len(set(data['details'])) / 3  # Normalize unique details
            intensity_score = len(data['intensity_scores']) > 0

            # Calculate weighted confidence score
            confidence_score = (
                consistency_score * self.symptom_patterns['consistency'] +
                detail_score * self.symptom_patterns['detail_level'] +
                intensity_score * self.symptom_patterns['intensity']
            ) * 100

            # Calculate average intensity if available
            intensity = (
                sum(data['intensity_scores']) / len(data['intensity_scores'])
                if data['intensity_scores']
                else 5  # Default middle intensity
            )

            analyzed_symptoms.append({
                'name': symptom_name.title(),
                'intensity': round(intensity, 1),
                'confidence_score': round(confidence_score, 1),
                'mentions': data['mentions'],
                'details': list(set(data['details']))
            })

        return analyzed_symptoms