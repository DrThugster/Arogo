# backend/app/routes/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from app.utils.chatbot import MedicalChatbot
from app.utils.response_validator import AIResponseValidator
from app.utils.symptom_analyzer import SymptomAnalyzer
from app.config.database import redis_client, consultations_collection
import json
from datetime import datetime
from typing import Dict
import json
import logging

logger = logging.getLogger(__name__)

class EnhancedConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
        self.chatbots: dict = {}
        self.response_validator = AIResponseValidator()
        self.symptom_analyzer = SymptomAnalyzer()

    async def process_message(self, message: str, consultation_id: str) -> dict:
        """Process message and validate response"""
        try:
            # Get AI response
            response = await self.chatbots[consultation_id].process_message(message)
            
            # Validate response
            is_valid, error_msg, processed_response = self.response_validator.validate_response(response)
            
            if not is_valid:
                # Handle invalid response
                return {
                    "status": "error",
                    "message": "I apologize, but I need to rephrase my response. Could you please repeat your last message?",
                    "error": error_msg
                }

            # Enhance response if valid
            enhanced_response = self.response_validator.enhance_response(processed_response)
            
            return {
                "status": "success",
                "message": enhanced_response,
                "confidence_scores": processed_response['confidence_scores'],
                "requires_emergency": processed_response['requires_emergency']
            }

        except Exception as e:
            return {
                "status": "error",
                "message": "I apologize, but I'm having trouble processing your request. Please try again.",
                "error": str(e)
            }

    async def update_consultation_analysis(self, consultation_id: str, message: str, response: dict):
        """Update consultation with analyzed data"""
        try:
            # Get current chat history
            consultation = await consultations_collection.find_one({"consultation_id": consultation_id})
            chat_history = consultation.get('chat_history', [])
            
            # Analyze symptoms
            analyzed_symptoms = self.symptom_analyzer.analyze_symptoms(chat_history)
            
            # Update consultation with analysis
            await consultations_collection.update_one(
                {"consultation_id": consultation_id},
                {
                    "$set": {
                        "analyzed_symptoms": analyzed_symptoms,
                        "last_analysis": datetime.utcnow(),
                        "requires_emergency": response.get('requires_emergency', False)
                    }
                }
            )

        except Exception as e:
            print(f"Error updating consultation analysis: {str(e)}")

async def websocket_endpoint(websocket: WebSocket, consultation_id: str):
    manager = EnhancedConnectionManager()
    try:
        await manager.connect(websocket, consultation_id)
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process and validate response
            response = await manager.process_message(message_data['content'], consultation_id)
            
            # Update consultation analysis
            await manager.update_consultation_analysis(consultation_id, message_data['content'], response)
            
            # Send response to client
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        manager.disconnect(consultation_id)
    except Exception as e:
        await websocket.send_json({
            "status": "error",
            "message": "An error occurred in the conversation.",
            "error": str(e)
        })
        manager.disconnect(consultation_id)



class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, consultation_id: str):
        await websocket.accept()
        self.active_connections[consultation_id] = websocket
        logger.info(f"WebSocket connection established for consultation {consultation_id}")

    def disconnect(self, consultation_id: str):
        if consultation_id in self.active_connections:
            del self.active_connections[consultation_id]
            logger.info(f"WebSocket connection closed for consultation {consultation_id}")

    async def send_message(self, consultation_id: str, message: str):
        if consultation_id in self.active_connections:
            await self.active_connections[consultation_id].send_json({
                "type": "message",
                "content": message
            })

    async def handle_message(self, websocket: WebSocket, consultation_id: str, data: str):
        try:
            message_data = json.loads(data)
            # Here you can add your message processing logic
            response = f"Received your message: {message_data.get('content', '')}"
            await self.send_message(consultation_id, response)
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "content": "Error processing message"
            })

    

def websocket_manager():
    return WebSocketManager()