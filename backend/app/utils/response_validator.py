
# backend/app/utils/response_validator.py
from typing import Dict, List, Optional, Tuple
import re

class AIResponseValidator:
    def __init__(self):
        self.required_patterns = {
            'symptom_mention': r'symptom|pain|discomfort|feeling|condition',
            'confidence_score': r'\[Confidence:\s*(\d+)%\]',
            'recommendation': r'\[Recommendation:.*?\]',
            'emergency_keywords': r'emergency|immediate|urgent|serious|severe',
        }

    def validate_symptoms(self, symptoms: List[Dict]) -> Tuple[bool, List[Dict]]:
        """Validate and clean symptom data"""
        validated_symptoms = []
        
        for symptom in symptoms:
            try:
                # Ensure required fields with proper types
                validated_symptom = {
                    "name": str(symptom.get('name', '')),
                    "severity": float(symptom.get('severity', 0)),
                    "duration": str(symptom.get('duration', 'Not specified')),
                    "pattern": str(symptom.get('pattern', 'Not specified'))
                }
                
                if validated_symptom["name"] and validated_symptom["severity"] > 0:
                    validated_symptoms.append(validated_symptom)
                    
            except (ValueError, TypeError):
                continue
                
        return len(validated_symptoms) > 0, validated_symptoms



    def _process_response(self, response: str) -> Dict:
        """Process and structure the AI response."""
        # Extract confidence scores
        confidence_matches = re.finditer(r'\[Confidence:\s*(\d+)%\]', response)
        confidence_scores = [int(match.group(1)) for match in confidence_matches]

        # Extract recommendations
        recommendations = re.findall(r'\[Recommendation:(.*?)\]', response)

        # Check for emergency keywords
        has_emergency = any(re.search(self.required_patterns['emergency_keywords'], response, re.IGNORECASE))

        # Extract severity/intensity information
        severity_matches = re.findall(r'(\d+)/10', response)
        severity_scores = [int(score) for score in severity_matches] if severity_matches else []

        # Structure the response
        return {
            'main_response': re.sub(r'\[.*?\]', '', response).strip(),
            'confidence_scores': confidence_scores,
            'recommendations': [rec.strip() for rec in recommendations],
            'requires_emergency': has_emergency,
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'severity_scores': severity_scores
        }

    def enhance_response(self, response: Dict) -> str:
        """
        Enhance the response with proper formatting and additional context if needed.
        """
        enhanced = response['main_response']

        # Add confidence context if scores are low
        if response['average_confidence'] < 70:
            enhanced += "\n\nPlease note: This assessment is based on limited information. A medical professional can provide a more accurate evaluation."

        # Add emergency warning if detected
        if response['requires_emergency']:
            enhanced = "⚠️ IMPORTANT: Based on your symptoms, immediate medical attention may be required.\n\n" + enhanced

        # Add recommendations
        if response['recommendations']:
            enhanced += "\n\nRecommendations:\n" + "\n".join(f"• {rec}" for rec in response['recommendations'])

        return enhanced