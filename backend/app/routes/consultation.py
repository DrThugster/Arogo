# backend/app/routes/consultation.py
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from app.models.consultation import ConsultationCreate
from app.config.database import consultations_collection
from app.utils.report_generator import create_pdf_report
from app.utils.symptom_analyzer import SymptomAnalyzer
from app.utils.speech_processor import process_speech_to_text
from datetime import datetime
import google.generativeai as genai
from app.config.database import redis_client
import json
import uuid
import io
import json
import os
import logging
from app.utils.consultation_helpers import (
    generate_medication_recommendations,
    generate_home_remedies,
    generate_precautions,
    generate_diagnosis_description
)


logger = logging.getLogger(__name__)
router = APIRouter()

class ChatService:
    def __init__(self):
        # Initialize Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-pro')
        self.collection = consultations_collection
        
    def get_conversation_context(self, consultation_id: str) -> str:
        """Get conversation history from Redis."""
        try:
            context = redis_client.get(f"chat_context_{consultation_id}")
            return json.loads(context) if context else []
        except:
            return []

    def store_conversation_context(self, consultation_id: str, context: list):
        """Store conversation history in Redis."""
        try:
             # Create a serializable copy of the context
            serializable_context = []
            for message in context:
             message_copy = {
                "type": message["type"],
                "content": message["content"],
                "timestamp": message["timestamp"].isoformat() if isinstance(message["timestamp"], datetime) else message["timestamp"]
            }
            serializable_context.append(message_copy)


            redis_client.set(
                f"chat_context_{consultation_id}",
                json.dumps(serializable_context),
                ex=3600  # expire after 1 hour
            )
        except Exception as e:
            logger.error(f"Error storing context: {str(e)}")

    def create_prompt(self, message: str, context: list) -> str:
        """Create a context-aware prompt for Gemini."""
        base_prompt = """
        You are a medical pre-diagnosis assistant. Your role is to:
        1. Ask relevant follow-up questions about symptoms
        2. Show empathy while gathering information
        3. Provide preliminary guidance
        4. Recommend when to seek professional medical help
        5. Keep responses clear and focused

        Rules:
        - Ask one main question at a time
        - Don't make definitive diagnoses
        - If symptoms are severe, recommend immediate medical attention
        - Be professional and empathetic
        - Provide medical information based on symptoms
        """

        # Add conversation history
        history = "\n".join([
            f"{'Patient' if msg['type'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in context[-5:]  # Last 5 messages for context
        ])

        return f"{base_prompt}\n\nConversation History:\n{history}\n\nCurrent Patient Message: {message}\n\nResponse:"

    async def update_chat_history(self, consultation_id: str, message: dict):
        """Update chat history in MongoDB and context in Redis."""
        try:
            # Update MongoDB
            result = consultations_collection.update_one(
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

            # Update Redis context
            context = self.get_conversation_context(consultation_id)
            context.append(message)
            self.store_conversation_context(consultation_id, context)
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating chat history: {str(e)}")
            return False

    async def get_ai_response(self, consultation_id: str, message: str) -> str:
        """Generate AI response using Gemini."""
        try:
            # Get conversation context
            context = self.get_conversation_context(consultation_id)
            
            # Create prompt with context
            prompt = self.create_prompt(message, context)
            
            # Generate response from Gemini
            response = self.model.generate_content(prompt)
            
            # Process and clean response
            ai_response = response.text.strip()
            
            # Add some safety checks
            if not ai_response:
                return "I apologize, but I need more information about your symptoms. Could you please provide more details?"
            
            if len(ai_response) > 1000:  # Limit response length
                ai_response = ai_response[:1000] + "..."
            
            return ai_response

        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request. Could you please rephrase your message?"

# Create an instance of ChatService
chat_service = ChatService()

@router.post("/start")
async def start_consultation(user_data: ConsultationCreate):
    """Start a new consultation session."""
    try:
        logger.info(f"Received consultation request with data: {json.dumps(user_data.dict())}")
        
        consultation_id = str(uuid.uuid4())
        logger.info(f"Generated consultation ID: {consultation_id}")
        
        consultation_data = {
            "consultation_id": consultation_id,
            "user_details": user_data.dict(),
            "status": "started",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "chat_history": [],
            "diagnosis": None
        }
        
        try:
            result = consultations_collection.insert_one(consultation_data)
            logger.info(f"Consultation created with ID: {consultation_id}")
            
            if not result.inserted_id:
                logger.error("Failed to get inserted_id from MongoDB")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create consultation record"
                )
            
            response_data = {
                "status": "success",
                "consultationId": consultation_id,
                "userDetails": user_data.dict(),
                "message": "Consultation started successfully"
            }
            logger.info(f"Sending success response: {json.dumps(response_data)}")
            return response_data
            
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(db_error)}"
            )
    
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/status/{consultation_id}")
async def get_consultation_status(consultation_id: str):
    """Get the current status of a consultation."""
    try:
        consultation = consultations_collection.find_one(
            {"consultation_id": consultation_id}
        )
        
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        return {
            "status": "active",
            "consultationId": consultation_id,
            "userDetails": consultation["user_details"],
            "created_at": consultation["created_at"]
        }
    
    except Exception as e:
        logger.error(f"Error getting consultation status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message/{consultation_id}")
async def handle_message(consultation_id: str, message: dict):
    """Handle incoming chat messages."""
    try:
        # Save user message
        await chat_service.update_chat_history(consultation_id, {
            "type": "user",
            "content": message.get("content", ""),
            "timestamp": datetime.utcnow()
        })

        # Get AI response
        response = await chat_service.get_ai_response(message.get("content", ""))

        # Save AI response
        await chat_service.update_chat_history(consultation_id, {
            "type": "bot",
            "content": response,
            "timestamp": datetime.utcnow()
        })

        return {
            "status": "success",
            "response": response
        }

    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech audio to text."""
    try:
        logger.info("Receiving audio file for speech-to-text conversion")
        contents = await audio.read()
        
        if not contents:
            raise ValueError("Empty audio file received")
            
        logger.info(f"Received audio file of size: {len(contents)} bytes")
        logger.info(f"Audio content type: {audio.content_type}")
        
        text = await process_speech_to_text(contents)
        
        if not text:
            raise ValueError("No text was transcribed from the audio")
            
        logger.info(f"Successfully transcribed text: {text}")
        
        return JSONResponse(
            content={
                "status": "success",
                "text": text
            }
        )
    except ValueError as ve:
        logger.error(f"Validation error in speech-to-text: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        logger.error(f"Runtime error in speech-to-text: {str(re)}")
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        logger.error(f"Unexpected error in speech-to-text: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary/{consultation_id}")
async def get_consultation_summary(consultation_id: str):
    """Get consultation summary and generate diagnosis."""
    try:
        consultation = consultations_collection.find_one(
            {"consultation_id": consultation_id}
        )
        
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        try:
            # Get chat history for diagnosis
            chat_history = consultation.get('chat_history', [])
            
            # Generate diagnosis description using consultation helper
            diagnosis_description = generate_diagnosis_description(chat_history)
            
            # Analyze symptoms using SymptomAnalyzer for detailed analysis
            symptom_analyzer = SymptomAnalyzer()
            analyzed_symptoms = symptom_analyzer.analyze_symptoms(chat_history)
            
            # Generate recommendations using consultation helpers
            medications = generate_medication_recommendations(analyzed_symptoms)
            home_remedies = generate_home_remedies(analyzed_symptoms)
            precautions = generate_precautions(analyzed_symptoms)
            
            # Generate summary
            summary = {
                "consultation_id": consultation_id,
                "userDetails": consultation["user_details"],
                "diagnosis": {
                    "symptoms": analyzed_symptoms,
                    "description": diagnosis_description,
                    "severityScore": symptom_analyzer.calculate_severity_score(analyzed_symptoms),
                    "riskLevel": symptom_analyzer.determine_risk_level(analyzed_symptoms),
                    "timeframe": symptom_analyzer.recommend_timeframe(analyzed_symptoms),
                    "recommendedDoctor": symptom_analyzer.recommend_specialist(analyzed_symptoms)
                },
                "recommendations": {
                    "medications": medications,
                    "homeRemedies": home_remedies
                },
                "precautions": precautions,
                "chatHistory": chat_history,
                "created_at": consultation["created_at"],
                "completed_at": datetime.utcnow()
            }
            
            # Update consultation with summary
            result = consultations_collection.update_one(
                {"consultation_id": consultation_id},
                {
                    "$set": {
                        "status": "completed",
                        "diagnosis_summary": summary,
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count == 0:
                logger.warning(f"No consultation was updated for ID: {consultation_id}")
            
            return summary
            
        except Exception as analysis_error:
            logger.error(f"Error analyzing consultation data: {str(analysis_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error analyzing consultation data: {str(analysis_error)}"
            )
            
    except Exception as e:
        logger.error(f"Error generating consultation summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/report/{consultation_id}")
async def get_consultation_report(consultation_id: str):
    """Generate and download PDF report."""
    try:
        consultation = consultations_collection.find_one(
            {"consultation_id": consultation_id}
        )
        
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        try:
            # Get or generate summary
            if "diagnosis_summary" not in consultation:
                summary = await get_consultation_summary(consultation_id)
            else:
                summary = consultation["diagnosis_summary"]
            
            # Ensure symptoms data is available
            if "symptoms" not in summary and "diagnosis" in summary:
                summary["symptoms"] = summary["diagnosis"].get("symptoms", [])
            
            # Generate PDF
            pdf_buffer = create_pdf_report(summary)
            
            return StreamingResponse(
                io.BytesIO(pdf_buffer.getvalue()),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=consultation-report-{consultation_id}.pdf"
                }
            )
            
        except Exception as report_error:
            logger.error(f"Error generating PDF report content: {str(report_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error generating report content: {str(report_error)}"
            )
            
    except Exception as e:
        logger.error(f"Error generating PDF report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))