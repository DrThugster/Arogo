# backend/app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config.database import mongodb_client, redis_client
from app.routes import consultation
from app.routes.consultation import chat_service
from contextlib import asynccontextmanager
import uvicorn
import json
import logging
from datetime import datetime
from app.utils.speech_processor import process_text_to_speech


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, consultation_id: str):
        await websocket.accept()
        self.active_connections[consultation_id] = websocket
        logger.info(f"WebSocket connected for consultation: {consultation_id}")

    def disconnect(self, consultation_id: str):
        if consultation_id in self.active_connections:
            del self.active_connections[consultation_id]
            logger.info(f"WebSocket disconnected for consultation: {consultation_id}")

    async def send_message(self, consultation_id: str, message: dict):
        if consultation_id in self.active_connections:
            try:
                await self.active_connections[consultation_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {str(e)}")
                await self.handle_connection_error(consultation_id)

    async def handle_connection_error(self, consultation_id: str):
        """Handle WebSocket connection errors."""
        self.disconnect(consultation_id)
        # You could implement reconnection logic here if needed

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

                # Save user message
                await chat_service.update_chat_history(
                    consultation_id,
                    {
                        "type": "user",
                        "content": message_data.get("content", ""),
                        "timestamp": datetime.utcnow()
                    }
                )

                # Get AI response
                response = await chat_service.get_ai_response(consultation_id, message_data.get("content", ""))

                # Generate audio for the response
                try:
                    audio_data = await process_text_to_speech(response)
                    logger.info("Successfully generated audio response")
                except Exception as e:
                    logger.error(f"Error generating audio: {str(e)}")
                    audio_data = None

                # Save bot response
                await chat_service.update_chat_history(
                    consultation_id,
                    {
                        "type": "bot",
                        "content": response,
                        "timestamp": datetime.utcnow()
                    }
                )

                # Send response with audio back to client
                response_data = {
                    "type": "bot",
                    "content": response,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                if audio_data:
                    response_data["audio"] = audio_data

                await websocket.send_json(response_data)
                logger.info("Sent response with audio to client")

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid message format"
                })
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "content": "Error processing your message"
                })

    except WebSocketDisconnect:
        manager.disconnect(consultation_id)
        logger.info(f"WebSocket disconnected for consultation: {consultation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(consultation_id)
        try:
            await websocket.close()
        except:
            pass


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