# backend/app/routes/speech.py
from fastapi import APIRouter, UploadFile, File, HTTPException
import speech_recognition as sr
import io
import tempfile
import os

router = APIRouter()

@router.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    try:
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            # Write the audio content to the temporary file
            content = await audio.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name

        # Initialize recognizer
        recognizer = sr.Recognizer()
        
        # Process the audio file
        with sr.AudioFile(temp_audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            
        # Clean up the temporary file
        os.remove(temp_audio_path)
        
        return {"text": text, "status": "success"}
    
    except sr.UnknownValueError:
        raise HTTPException(status_code=400, detail="Could not understand audio")
    except sr.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error with the speech recognition service: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure temp file is removed even if an error occurs
        if 'temp_audio_path' in locals():
            try:
                os.remove(temp_audio_path)
            except:
                pass