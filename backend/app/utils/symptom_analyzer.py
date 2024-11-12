# backend/app/utils/symptom_analyzer.py
from typing import Dict, List
import logging
from app.utils.ai_config import GeminiConfig
import json

logger = logging.getLogger(__name__)

class SymptomAnalyzer:
    def __init__(self):
        self.ai_config = GeminiConfig()

    async def analyze_conversation(self, chat_history: List[Dict]) -> Dict:
        """Analyze entire conversation for symptoms using AI."""
        try:
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze this medical consultation conversation and extract detailed symptom information.
            
            Conversation:
            {self._format_chat_history(chat_history)}

            Provide a structured analysis including:
            1. Identified symptoms with:
               - Severity (1-10)
               - Duration
               - Pattern (constant, intermittent, progressive)
               - Related factors
               - Impact on daily activities
            2. Symptom progression over time
            3. Risk assessment
            4. Urgency level
            
            Format response as JSON with these exact keys:
            {{
                "symptoms": [
                    {{
                        "name": "symptom name",
                        "severity": 1-10,
                        "duration": "duration description",
                        "pattern": "pattern description",
                        "related_factors": ["factor1", "factor2"],
                        "impact": "impact description"
                    }}
                ],
                "progression": "progression description",
                "risk_level": "low|medium|high",
                "urgency": "routine|prompt|immediate",
                "confidence_score": 1-100
            }}
            """

            # Get AI analysis
            response = self.ai_config.model.generate_content(analysis_prompt)
            analysis = self._parse_ai_response(response.text)
            
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing conversation: {str(e)}")
            raise

    async def validate_medical_response(self, response: str, context: List[Dict]) -> Dict:
        """Validate medical response using AI."""
        try:
            validation_prompt = f"""
            Validate this medical response for quality and safety:

            Response to validate:
            {response}

            Context:
            {self._format_chat_history(context)}

            Check for:
            1. Medical accuracy
            2. Appropriate caution/disclaimers
            3. Emergency recognition
            4. Completeness of response
            5. Professional tone
            
            Format response as JSON with these exact keys:
            {{
                "is_valid": true|false,
                "safety_concerns": ["concern1", "concern2"],
                "missing_elements": ["element1", "element2"],
                "emergency_level": "none|low|high",
                "improvement_needed": true|false,
                "suggested_improvements": ["improvement1", "improvement2"]
            }}
            """

            validation_response = self.ai_config.model.generate_content(validation_prompt)
            return self._parse_ai_response(validation_response.text)

        except Exception as e:
            logger.error(f"Error validating response: {str(e)}")
            raise

    def _format_chat_history(self, chat_history: List[Dict]) -> str:
        """Format chat history for AI prompt."""
        formatted = []
        for msg in chat_history:
            role = "Patient" if msg["type"] == "user" else "Doctor"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    def _parse_ai_response(self, response: str) -> Dict:
        """Parse AI response ensuring it's valid JSON."""
        try:
            # Clean and format the response text
            cleaned_response = response.strip()
            # Look for JSON content between curly braces if present
            start_idx = cleaned_response.find('{')
            end_idx = cleaned_response.rfind('}')
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = cleaned_response[start_idx:end_idx + 1]
                return json.loads(json_str)
            
            # If no JSON found, create a structured response
            return {
                "symptoms": [],
                "progression": "Unable to determine",
                "risk_level": "unknown",
                "urgency": "unknown",
                "confidence_score": 0
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed, creating structured response: {str(e)}")
            return {
                "symptoms": [],
                "progression": "Unable to determine",
                "risk_level": "unknown",
                "urgency": "unknown",
                "confidence_score": 0
            }


    async def get_severity_assessment(self, symptoms: List[Dict]) -> Dict:
        """Get AI-powered severity assessment."""
        severity_prompt = f"""
        Assess the severity of these symptoms:
        {json.dumps(symptoms, indent=2)}

        Consider:
        1. Individual symptom severity
        2. Symptom combinations
        3. Impact on daily life
        4. Risk factors
        5. Emergency indicators

        Provide assessment as JSON with:
        {{
            "overall_severity": 1-10,
            "risk_level": "low|medium|high",
            "requires_emergency": true|false,
            "recommended_timeframe": "when to seek care",
            "reasoning": ["reason1", "reason2"]
        }}
        """

        response = self.ai_config.model.generate_content(severity_prompt)
        return self._parse_ai_response(response.text)
    
    # def analyze_symptoms(self, chat_history: List[Dict]) -> List[Dict]:
    #     """Analyze symptoms from chat history."""
    #     try:
    #         symptoms = []
    #         for message in chat_history:
    #             if message.get('symptom_analysis'):
    #                 symptoms.extend(message['symptom_analysis'].get('symptoms', []))
            
    #         # Consolidate duplicate symptoms and average their intensities
    #         consolidated_symptoms = {}
    #         for symptom in symptoms:
    #             name = symptom['name'].lower()
    #             if name in consolidated_symptoms:
    #                 consolidated_symptoms[name]['intensity'] = (
    #                     consolidated_symptoms[name]['intensity'] + float(symptom['severity'])
    #                 ) / 2
    #             else:
    #                 consolidated_symptoms[name] = {
    #                     'name': symptom['name'],
    #                     'intensity': float(symptom['severity']),
    #                     'duration': symptom.get('duration', 'Not specified'),
    #                     'pattern': symptom.get('pattern', 'Not specified')
    #                 }
            
    #         return list(consolidated_symptoms.values())
    #     except Exception as e:
    #         logger.error(f"Error analyzing symptoms: {str(e)}")
    #         return []
        
    # def calculate_severity_score(self, symptoms: List[Dict]) -> float:
    #     """Calculate overall severity score from symptoms."""
    #     try:
    #         if not symptoms:
    #             return 0.0
                
    #         total_severity = 0.0
    #         for symptom in symptoms:
    #             severity = symptom.get('severity') or symptom.get('intensity', 0)
    #             if severity:
    #                 total_severity += float(severity)
            
    #         # Normalize to 1-10 scale
    #         return min(10.0, (total_severity / len(symptoms)))
            
    #     except Exception as e:
    #         logger.error(f"Error calculating severity score: {str(e)}")
    #         return 0.0

    def analyze_symptoms(self, chat_history: List[Dict]) -> List[Dict]:
        try:
            symptoms = []
            for message in chat_history:
                if message.get('symptom_analysis'):
                    for symptom in message['symptom_analysis'].get('symptoms', []):
                        if isinstance(symptom, dict):
                            symptoms.append({
                                'name': symptom.get('name', 'Unknown'),
                                'severity': float(symptom.get('severity', 0) or 0),
                                'duration': symptom.get('duration', 'Not specified'),
                                'pattern': symptom.get('pattern', 'Not specified')
                            })
            
            return symptoms
        except Exception as e:
            logger.error(f"Error analyzing symptoms: {str(e)}")
            return []

    def calculate_severity_score(self, symptoms: List[Dict]) -> float:
        try:
            if not symptoms:
                return 0.0
                
            severities = []
            for symptom in symptoms:
                severity = symptom.get('severity', 0)
                if severity is not None:
                    severities.append(float(severity))
            
            return sum(severities) / len(severities) if severities else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating severity score: {str(e)}")
            return 0.0

    def determine_risk_level(self, symptoms: List[Dict]) -> str:
        """Determine risk level based on symptoms."""
        severity_score = self.calculate_severity_score(symptoms)
        
        if severity_score >= 8.0:
            return "high"
        elif severity_score >= 5.0:
            return "medium"
        else:
            return "low"

    def recommend_timeframe(self, symptoms: List[Dict]) -> str:
        """Recommend consultation timeframe based on symptoms."""
        risk_level = self.determine_risk_level(symptoms)
        
        if risk_level == "high":
            return "immediate"
        elif risk_level == "medium":
            return "within 24 hours"
        else:
            return "within a week"

    def recommend_specialist(self, symptoms: List[Dict]) -> str:
        """Recommend appropriate medical specialist based on symptoms."""
        # Default to general practitioner
        return "General Practitioner"
    
    def needs_conclusion(self, symptoms: List[Dict]) -> bool:
        """Determine if enough symptom data is gathered for conclusion"""
        if len(symptoms) >= 3:  # At least 3 symptoms documented
            severity_score = self.calculate_severity_score(symptoms)
            return severity_score > 0  # We have meaningful severity data
        return False


