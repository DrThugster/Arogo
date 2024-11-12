# backend/app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config.database import mongodb_client, redis_client
from app.routes import consultation
from app.services.chat_service import ChatService
from contextlib import asynccontextmanager
from app.config.database import consultations_collection
import uvicorn
import json
import logging
from datetime import datetime
from app.utils.speech_processor import process_text_to_speech
import asyncio


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# class ConnectionManager:
#     def __init__(self):
#         self.active_connections: dict = {}

#     async def connect(self, websocket: WebSocket, consultation_id: str):
#         await websocket.accept()
#         self.active_connections[consultation_id] = websocket
#         logger.info(f"WebSocket connected for consultation: {consultation_id}")

#     def disconnect(self, consultation_id: str):
#         if consultation_id in self.active_connections:
#             del self.active_connections[consultation_id]
#             logger.info(f"WebSocket disconnected for consultation: {consultation_id}")

#     async def send_message(self, consultation_id: str, message: dict):
#         if consultation_id in self.active_connections:
#             try:
#                 await self.active_connections[consultation_id].send_json(message)
#             except Exception as e:
#                 logger.error(f"Error sending message: {str(e)}")
#                 await self.handle_connection_error(consultation_id)

#     async def handle_connection_error(self, consultation_id: str):
#         """Handle WebSocket connection errors."""
#         self.disconnect(consultation_id)
#         # You could implement reconnection logic here if needed

# manager = ConnectionManager()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
        self.chat_service = ChatService()
        self.reconnect_attempts = {}
        self.max_reconnect_attempts = 3

    async def connect(self, websocket: WebSocket, consultation_id: str):
        """Connect and initialize consultation session."""
        try:
            await websocket.accept()
            self.active_connections[consultation_id] = websocket
            logger.info(f"WebSocket connected for consultation: {consultation_id}")

            # Load existing context if any
            context = await self.chat_service.get_conversation_context(consultation_id)
            if context:
                logger.info(f"Loaded existing context for consultation: {consultation_id}")

            # Send welcome message with context
            welcome_message = await self._generate_welcome_message(consultation_id, context)
            self.send_message(consultation_id, welcome_message)

        except Exception as e:
            logger.error(f"Error establishing connection for consultation {consultation_id}: {str(e)}")
            raise

    def disconnect(self, consultation_id: str):
        """Handle disconnection and cleanup."""
        try:
            if consultation_id in self.active_connections:
                del self.active_connections[consultation_id]
                if consultation_id in self.reconnect_attempts:
                    del self.reconnect_attempts[consultation_id]
                logger.info(f"WebSocket disconnected for consultation: {consultation_id}")
        except Exception as e:
            logger.error(f"Error during disconnect for consultation {consultation_id}: {str(e)}")

    async def send_message(self, consultation_id: str, message: dict):
        """Send message with retry logic."""
        if consultation_id in self.active_connections:
            try:
                websocket = self.active_connections[consultation_id]
                
                # Add audio if text response is present
                if 'response' in message and isinstance(message['response'], str):
                    try:
                        audio_data = await process_text_to_speech(message['response'])
                        message['audio'] = audio_data
                    except Exception as audio_error:
                        logger.error(f"Error generating audio: {str(audio_error)}")

                await websocket.send_json(message)
                
                # Reset reconnect attempts on successful send
                self.reconnect_attempts[consultation_id] = 0

            except Exception as e:
                logger.error(f"Error sending message: {str(e)}")
                await self.handle_connection_error(consultation_id)

    async def handle_connection_error(self, consultation_id: str):
        """Handle connection errors with retry logic."""
        try:
            if consultation_id in self.reconnect_attempts:
                self.reconnect_attempts[consultation_id] += 1
                
                if self.reconnect_attempts[consultation_id] <= self.max_reconnect_attempts:
                    logger.info(f"Attempting reconnection {self.reconnect_attempts[consultation_id]} "
                              f"for consultation {consultation_id}")
                    
                    # Store current context before disconnection
                    context = await self.chat_service.get_conversation_context(consultation_id)
                    
                    # Disconnect current connection
                    self.disconnect(consultation_id)
                    
                    # Wait for potential reconnection
                    await asyncio.sleep(2 ** self.reconnect_attempts[consultation_id])  # Exponential backoff
                    
                    # If client reconnects, context will be restored in connect method
                else:
                    logger.warning(f"Max reconnection attempts reached for consultation {consultation_id}")
                    self.disconnect(consultation_id)
                    
                    # Save conversation state for potential later recovery
                    await self._save_conversation_state(consultation_id)

        except Exception as e:
            logger.error(f"Error handling connection error: {str(e)}")
            self.disconnect(consultation_id)

    async def _generate_welcome_message(self, consultation_id: str, context: list) -> dict:
        """Generate contextual welcome message."""
        try:
            consultation = consultations_collection.find_one({"consultation_id": consultation_id})
            user_details = consultation.get("user_details", {})
            
            if context:
                # Generate context-aware welcome back message
                welcome_prompt = f"""
                Generate a brief welcome back message for a patient with these details:
                Name: {user_details.get('firstName')}
                Last conversation messages: {context[-2:]}
                
                Keep it professional, friendly, and reference their previous conversation.
                """
            else:
                # Generate initial welcome message
                welcome_prompt = f"""
                Generate a brief welcome message for a new patient:
                Name: {user_details.get('firstName')}
                Age: {user_details.get('age')}
                Gender: {user_details.get('gender')}

                Keep it professional and friendly, and ask them about their symptoms.
                """

            # Get AI response
            response = self.chat_service.ai_config.model.generate_content(welcome_prompt)
            
            return {
                "type": "bot",
                "content": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating welcome message: {str(e)}")
            return {
                "type": "bot",
                "content": "Welcome to your medical consultation. How can I help you today?",
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _save_conversation_state(self, consultation_id: str):
        """Save conversation state for recovery."""
        try:
            context = await self.chat_service.get_conversation_context(consultation_id)
            if context:
                await consultations_collection.update_one(
                    {"consultation_id": consultation_id},
                    {
                        "$set": {
                            "last_context": context,
                            "disconnected_at": datetime.utcnow(),
                            "connection_state": "disconnected"
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Error saving conversation state: {str(e)}")

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        logger.info("Starting up the application...")
        
        # Test database connections
        mongodb_client.admin.command('ping')
        redis_client.ping()
        logger.info("Successfully connected to databases")
        
    except Exception as e:
        logger.error(f"Startup Error: {str(e)}")
        raise e
    
    yield
    
    # Shutdown
    try:
        logger.info("Shutting down the application...")
        mongodb_client.close()
        logger.info("Database connections closed")
        
        # Clean up any remaining WebSocket connections
        for consultation_id in list(manager.active_connections.keys()):
            manager.disconnect(consultation_id)
            
    except Exception as e:
        logger.error(f"Shutdown Error: {str(e)}")

app = FastAPI(
    title="Arogo Telemedicine API",
    description="AI-powered telemedicine consultation platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    consultation.router,
    prefix="/api/consultation",
    tags=["consultation"]
)

# @app.websocket("/ws/{consultation_id}")
# async def websocket_endpoint(websocket: WebSocket, consultation_id: str):
#     """WebSocket endpoint for real-time chat."""
#     await manager.connect(websocket, consultation_id)
#     try:
#         while True:
#             # Receive and parse message
#             data = await websocket.receive_text()
#             try:
#                 message_data = json.loads(data)
#                 logger.info(f"Received message: {message_data}")

#                 # Save user message
#                 await chat_service.update_chat_history(
#                     consultation_id,
#                     {
#                         "type": "user",
#                         "content": message_data.get("content", ""),
#                         "timestamp": datetime.utcnow()
#                     }
#                 )

#                 # Get AI response
#                 response = await chat_service.get_ai_response(consultation_id, message_data.get("content", ""))

#                 # Generate audio for the response
#                 try:
#                     audio_data = await process_text_to_speech(response)
#                     logger.info("Successfully generated audio response")
#                 except Exception as e:
#                     logger.error(f"Error generating audio: {str(e)}")
#                     audio_data = None

#                 # Save bot response
#                 await chat_service.update_chat_history(
#                     consultation_id,
#                     {
#                         "type": "bot",
#                         "content": response,
#                         "timestamp": datetime.utcnow()
#                     }
#                 )

#                 # Send response with audio back to client
#                 response_data = {
#                     "type": "bot",
#                     "content": response,
#                     "timestamp": datetime.utcnow().isoformat(),
#                 }

#                 if audio_data:
#                     response_data["audio"] = audio_data

#                 await websocket.send_json(response_data)
#                 logger.info("Sent response with audio to client")

#             except json.JSONDecodeError as e:
#                 logger.error(f"Invalid JSON received: {str(e)}")
#                 await websocket.send_json({
#                     "type": "error",
#                     "content": "Invalid message format"
#                 })
#             except Exception as e:
#                 logger.error(f"Error processing message: {str(e)}")
#                 await websocket.send_json({
#                     "type": "error",
#                     "content": "Error processing your message"
#                 })

#     except WebSocketDisconnect:
#         manager.disconnect(consultation_id)
#         logger.info(f"WebSocket disconnected for consultation: {consultation_id}")
#     except Exception as e:
#         logger.error(f"WebSocket error: {str(e)}")
#         manager.disconnect(consultation_id)
#         try:
#             await websocket.close()
#         except:
#             pass

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
        self.chat_service = ChatService()  # Initialize ChatService

    async def connect(self, websocket: WebSocket, consultation_id: str):
        await websocket.accept()
        self.active_connections[consultation_id] = websocket
        logger.info(f"WebSocket connected for consultation: {consultation_id}")

    def disconnect(self, consultation_id: str):
        if consultation_id in self.active_connections:
            del self.active_connections[consultation_id]
            logger.info(f"WebSocket disconnected for consultation: {consultation_id}")

manager = ConnectionManager()

@app.websocket("/ws/{consultation_id}")
async def websocket_endpoint(websocket: WebSocket, consultation_id: str):
    """WebSocket endpoint for real-time chat."""
    await manager.connect(websocket, consultation_id)
    try:
        while True:
            # Receive and parse message
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                logger.info(f"Received message: {message_data}")

                # Process message using ChatService
                # This handles context management, AI response, and symptom analysis
                processed_response = await manager.chat_service.process_message(
                    consultation_id,
                    message_data.get("content", "")
                )

                # Generate audio for the response
                try:
                    audio_data = await process_text_to_speech(processed_response["response"])
                    logger.info("Successfully generated audio response")
                except Exception as e:
                    logger.error(f"Error generating audio: {str(e)}")
                    audio_data = None

                # Prepare response data with all analyzed information
                response_data = {
                    "type": "bot",
                    "content": processed_response["response"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "symptoms": processed_response.get("symptoms", []),
                    "risk_level": processed_response.get("risk_level", "unknown"),
                    "urgency": processed_response.get("urgency", "unknown"),
                    "requires_emergency": processed_response.get("requires_emergency", False)
                }

                if audio_data:
                    response_data["audio"] = audio_data

                await websocket.send_json(response_data)
                logger.info(f"Sent response with analysis for consultation: {consultation_id}")

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid message format"
                })
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                error_response = {
                    "type": "error",
                    "content": "Error processing your message. Please try again.",
                    "timestamp": datetime.utcnow().isoformat()
                }
                try:
                    await websocket.send_json(error_response)
                except:
                    logger.error("Failed to send error response")

    except WebSocketDisconnect:
        manager.disconnect(consultation_id)
        logger.info(f"WebSocket disconnected for consultation: {consultation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(consultation_id)
        try:
            await websocket.close()
        except:
            logger.error("Failed to close WebSocket connection")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Check the health status of the application."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "mongodb": "disconnected",
                "redis": "disconnected"
            }
        }

        # Check MongoDB
        try:
            mongodb_client.admin.command('ping')
            health_status["services"]["mongodb"] = "connected"
        except Exception as e:
            logger.error(f"MongoDB health check failed: {str(e)}")
            health_status["services"]["mongodb"] = f"error: {str(e)}"

        # Check Redis
        try:
            redis_client.ping()
            health_status["services"]["redis"] = "connected"
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            health_status["services"]["redis"] = f"error: {str(e)}"

        # Overall status
        if all(status == "connected" for status in health_status["services"].values()):
            return health_status
        else:
            return JSONResponse(
                status_code=503,
                content=health_status
            )

    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for all unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "status": "error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )