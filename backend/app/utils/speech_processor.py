# backend/app/utils/speech_processor.py
import speech_recognition as sr
import io
import tempfile
import os
from gtts import gTTS
import base64
import logging
from pydub import AudioSegment
import uuid


logger = logging.getLogger(__name__)

async def convert_to_wav(audio_data: bytes) -> bytes:
    """Convert audio data to WAV format."""
    try:
        # Save incoming audio to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_webm:
            temp_webm.write(audio_data)
            temp_webm_path = temp_webm.name

        # Convert to WAV
        audio = AudioSegment.from_file(temp_webm_path, format="webm")
        
        # Export as WAV to another temporary file
        wav_path = temp_webm_path + ".wav"
        audio.export(wav_path, format="wav")

        # Read the WAV file
        with open(wav_path, 'rb') as wav_file:
            wav_data = wav_file.read()

        # Cleanup temporary files
        os.remove(temp_webm_path)
        os.remove(wav_path)

        return wav_data

    except Exception as e:
        logger.error(f"Error converting audio format: {str(e)}")
        raise

async def process_speech_to_text(audio_data: bytes) -> str:
    """Convert speech audio to text."""
    try:
        # Convert audio to WAV format first
        wav_data = await convert_to_wav(audio_data)
        
        # Create temporary file for the WAV data
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            temp_audio.write(wav_data)
            temp_audio_path = temp_audio.name

        try:
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            # Adjust for ambient noise and recognize
            with sr.AudioFile(temp_audio_path) as source:
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source)
                # Record the audio
                audio = recognizer.record(source)
                # Recognize speech
                text = recognizer.recognize_google(audio)
                logger.info(f"Successfully transcribed audio to: {text}")
                return text

        finally:
            # Always cleanup temp file
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)

    except sr.UnknownValueError:
        logger.error("Google Speech Recognition could not understand audio")
        raise ValueError("Could not understand audio")
    except sr.RequestError as e:
        logger.error(f"Could not request results from Speech Recognition service; {e}")
        raise RuntimeError(f"Speech Recognition service error: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing speech: {str(e)}")
        raise Exception(f"Error processing speech: {str(e)}")

# async def process_text_to_speech(text: str) -> str:
#     """Convert text to speech and return as base64 encoded string."""
#     try:
#         # Create temporary file for audio
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
#             # Generate speech
#             tts = gTTS(text=text, lang='en')
#             tts.save(temp_audio.name)
            
#             # Read the file and convert to base64
#             with open(temp_audio.name, 'rb') as audio_file:
#                 audio_data = base64.b64encode(audio_file.read()).decode()

#             # Cleanup
#             os.unlink(temp_audio.name)
#             return audio_data

#     except Exception as e:
#         logger.error(f"Error generating speech: {str(e)}")
#         raise Exception(f"Error generating speech: {str(e)}")

async def process_text_to_speech(text: str) -> str:
    """Convert text to speech with improved file handling."""
    temp_path = None
    try:
        # Generate unique filename
        temp_path = os.path.join(tempfile.gettempdir(), f'speech_{uuid.uuid4()}.mp3')
        
        # Generate speech
        tts = gTTS(text=text, lang='en')
        tts.save(temp_path)
        
        # Read file content
        with open(temp_path, 'rb') as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode()
            
        return audio_data

    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        raise Exception(f"Error generating speech: {str(e)}")
        
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
