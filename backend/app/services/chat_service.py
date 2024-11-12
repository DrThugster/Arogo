# backend/app/services/chat_service.py
from app.utils.ai_config import GeminiConfig
from app.utils.symptom_analyzer import SymptomAnalyzer
from app.config.database import redis_client, consultations_collection
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.ai_config = GeminiConfig()
        self.symptom_analyzer = SymptomAnalyzer()
        self.conversation_expiry = 3600  # 1 hour

    async def get_conversation_context(self, consultation_id: str) -> list:
        """Retrieve conversation context from Redis."""
        try:
            context = redis_client.get(f"chat_context_{consultation_id}")
            return json.loads(context) if context else []
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []

    async def store_conversation_context(self, consultation_id: str, context: list):
        """Store conversation context in Redis."""
        try:
            redis_client.setex(
                f"chat_context_{consultation_id}",
                self.conversation_expiry,
                json.dumps(context)
            )
        except Exception as e:
            logger.error(f"Error storing context: {e}")

    async def process_message(self, consultation_id: str, message: str) -> dict:
        """Process message with AI and symptom analysis."""
        try:
            # Get current context
            context = await self.get_conversation_context(consultation_id)
            
            # Add user message to context
            user_message = {
                "type": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            context.append(user_message)

            # Get consultation details
            consultation = consultations_collection.find_one({"consultation_id": consultation_id})
            user_details = consultation.get("user_details", {})

            # Generate AI response with context
            response = await self._generate_ai_response(message, context, user_details)

            # Analyze symptoms from conversation
            symptom_analysis = await self.symptom_analyzer.analyze_conversation(context)
            
            # Validate response
            validation_result = await self.symptom_analyzer.validate_medical_response(
                response,
                context
            )

            # Process final response
            processed_response = await self._process_response(
                response,
                symptom_analysis,
                validation_result
            )

            # Add bot message to context
            bot_message = {
                "type": "bot",
                "content": processed_response["response"],
                "timestamp": datetime.utcnow().isoformat(),
                "symptom_analysis": symptom_analysis,
                "validation": validation_result
            }
            context.append(bot_message)

            # Store updated context
            await self.store_conversation_context(consultation_id, context)
            
            # Update MongoDB
            await self.update_chat_history(consultation_id, [user_message, bot_message])

            return processed_response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise


    async def _generate_ai_response(self, message: str, context: list, user_details: dict) -> str:
        """Generate AI response using Gemini."""
        question_count = sum(1 for msg in context if msg['type'] == 'bot' and '?' in msg['content'])

        prompt = f"""
        As a medical AI assistant, respond to this patient considering their full context.

        Patient Details:
        Age: {user_details.get('age')}
        Gender: {user_details.get('gender')}

        Conversation History:
        {self._format_context(context)}

        Current Message: {message}
        Questions Asked: {question_count}/5

        IMPORTANT RULES:
        1. If {question_count} >= 4, provide a conclusion with likely condition and next steps 
        2. Ask only ONE specific question about the symptom
        3. Focus on the most important aspect first
        4. Each response should be focused and under 50 words
        5. Do not provide treatment advice until symptoms are fully understood
        6. Wait for patient's response before asking follow-up questions
        7. Maximum 5 questions total

        Respond with a single, focused question or statement.
        {f"Provide final assessment and recommendations" if question_count >= 4 else "Ask next most relevant question"}
        """

        response = self.ai_config.model.generate_content(prompt)
        return response.text


    async def _process_response(self, response: str, symptom_analysis: dict, validation: dict) -> dict:
        """Process and enhance the AI response."""
        processed = {
            "response": response,
            "symptoms": symptom_analysis.get("symptoms", []),
            "risk_level": symptom_analysis.get("risk_level", "unknown"),
            "urgency": symptom_analysis.get("urgency", "unknown"),
            "requires_emergency": validation.get("emergency_level") == "high",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add emergency warning if needed
        if processed["requires_emergency"]:
            processed["response"] = "⚠️ URGENT: This requires immediate medical attention!\n\n" + processed["response"]

        return processed

    def _format_context(self, context: list) -> str:
        """Format conversation context for AI prompt."""
        return "\n".join([
            f"{'Patient' if msg['type'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in context[-5:]  # Last 5 messages for context
        ])

    async def update_chat_history(self, consultation_id: str, messages: list):
        """Update chat history in MongoDB."""
        try:
            for message in messages:
                consultations_collection.update_one(
                    {"consultation_id": consultation_id},
                    {
                        "$push": {
                            "chat_history": message
                        },
                        "$set": {
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Error updating chat history: {e}")
            raise