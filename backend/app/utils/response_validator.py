
# backend/app/utils/response_validator.py
from typing import Dict, Optional, Tuple
import re

class AIResponseValidator:
    def __init__(self):
        self.required_patterns = {
            'symptom_mention': r'symptom|pain|discomfort|feeling|condition',
            'confidence_score': r'\[Confidence:\s*(\d+)%\]',
            'recommendation': r'\[Recommendation:.*?\]',
            'emergency_keywords': r'emergency|immediate|urgent|serious|severe',
        }

    def validate_response(self, response: str) -> Tuple[bool, Optional[str], Dict]:
        """
        Validate AI response for required elements and proper formatting.
        Returns: (is_valid, error_message, processed_response)
        """
        try:
            # Check for minimum length
            if len(response) < 50:
                return False, "Response too short", {}

            # Check for required patterns
            missing_patterns = []
            for pattern_name, pattern in self.required_patterns.items():
                if not re.search(pattern, response, re.IGNORECASE):
                    missing_patterns.append(pattern_name)

            if missing_patterns:
                return False, f"Missing required elements: {', '.join(missing_patterns)}", {}

            # Process and structure the response
            processed = self._process_response(response)
            
            return True, None, processed

        except Exception as e:
            return False, f"Validation error: {str(e)}", {}

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