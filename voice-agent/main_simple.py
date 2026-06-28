"""
Simplified Voice Agent - FastAPI server
Handles audio upload, STT, TTS, and RAG integration
Runs on port 8002
"""

import os
import io
import asyncio
import wave
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

# Load environment
load_dotenv()

app = FastAPI(title="Voice Agent", version="1.0.0")

# ─────────────────────────────────────────────────────────────────────
# MOCK STT - In production, use Sarvam AI or NVIDIA NIM
# ─────────────────────────────────────────────────────────────────────

def mock_stt(audio_bytes: bytes, language: str = "en") -> str:
    """
    Mock STT - In production, this would call Sarvam AI or NVIDIA NIM
    
    For testing, returns a default response based on language
    """
    # In production, you would:
    # 1. Save audio to file
    # 2. Call Sarvam AI API: https://api.sarvam.ai/speech-to-text
    # 3. Get transcript
    
    # Mock responses for testing
    mock_responses = {
        "en": "I want to apply for a PAN card",
        "ta": "நான் பான் கார்டுக்கு விண்ணப்பிக்க விரும்புகிறேன்",
        "hi": "मुझे पैन कार्ड के लिए आवेदन करना है",
    }
    
    return mock_responses.get(language, mock_responses["en"])


# ─────────────────────────────────────────────────────────────────────
# MOCK TTS - In production, use Sarvam AI or NVIDIA NIM
# ─────────────────────────────────────────────────────────────────────

def mock_tts(text: str, language: str = "en") -> bytes:
    """
    Mock TTS - In production, this would call Sarvam AI or NVIDIA NIM
    
    Returns a simple WAV file with silence
    For production: call Sarvam AI TTS API
    """
    # Create a simple WAV file (1 second of silence at 16kHz)
    sample_rate = 16000
    duration = 1  # 1 second
    num_samples = sample_rate * duration
    
    # Create silent audio using bytearray instead of numpy
    audio_data = bytearray(num_samples * 2)  # 16-bit PCM = 2 bytes per sample
    
    # Write to WAV
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data)
    
    wav_buffer.seek(0)
    return wav_buffer.getvalue()


# ─────────────────────────────────────────────────────────────────────
# RAG INTEGRATION - Get response from pan-rag service
# ─────────────────────────────────────────────────────────────────────

async def get_rag_response(query: str, language: str = "en") -> str:
    """
    Call pan-rag service to get RAG-based response
    """
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "http://localhost:8000/api/ask",
                json={
                    "question": query,
                    "language": language,
                    "session_id": "voice-session"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("answer", "I'm here to help with your PAN questions.")
            else:
                print(f"RAG service error: {response.status_code}")
                return "Let me help you with that PAN question."
                
    except Exception as e:
        print(f"Error calling RAG service: {e}")
        return "I'm having trouble connecting to the knowledge base right now."


# ─────────────────────────────────────────────────────────────────────
# VOICE ENDPOINT
# ─────────────────────────────────────────────────────────────────────

@app.post("/api/voice/speak")
async def voice_speak(
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
    session_id: str = Form(default="")
):
    """
    Main voice endpoint
    
    Input: Audio file + language
    Process: STT → RAG → TTS
    Output: Audio stream + headers (transcript, reply)
    """
    try:
        print(f"[Voice] Received audio request: language={language}, session={session_id}")
        
        # Read audio file
        audio_bytes = await audio.read()
        if not audio_bytes:
            return JSONResponse(
                {"error": "No audio data"},
                status_code=400
            )
        
        print(f"[Voice] Audio size: {len(audio_bytes)} bytes")
        
        # 1. STT - Convert audio to text
        try:
            transcript = mock_stt(audio_bytes, language)
            print(f"[Voice] STT Result: {transcript}")
        except Exception as e:
            print(f"[Voice] STT Error: {e}")
            transcript = "I couldn't understand the audio"
        
        # 2. RAG - Get response
        try:
            reply = await get_rag_response(transcript, language)
            print(f"[Voice] RAG Response: {reply}")
        except Exception as e:
            print(f"[Voice] RAG Error: {e}")
            reply = "Let me help you with that question."
        
        # 3. TTS - Convert response to audio
        try:
            audio_response = mock_tts(reply, language)
            print(f"[Voice] TTS generated {len(audio_response)} bytes")
        except Exception as e:
            print(f"[Voice] TTS Error: {e}")
            # Still return response even if TTS fails
            audio_response = b''
        
        # 4. Return response with headers
        print(f"[Voice] Returning response")
        
        async def audio_stream():
            yield audio_response
        
        return StreamingResponse(
            audio_stream(),
            media_type="audio/wav",
            headers={
                "X-Transcript": transcript,
                "X-Reply": reply,
                "X-Language": language,
                "X-Success": "true"
            }
        )
        
    except Exception as e:
        print(f"[Voice] Endpoint error: {e}")
        return JSONResponse(
            {
                "error": "Voice processing failed",
                "details": str(e),
                "transcript": "",
                "reply": "Sorry, something went wrong",
                "audio_available": False
            },
            status_code=500
        )


# ─────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "voice-agent",
        "version": "1.0.0",
        "stt_available": True,
        "tts_available": True,
        "rag_available": "checking"
    }


# ─────────────────────────────────────────────────────────────────────
# ROOT
# ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Welcome endpoint"""
    return {
        "message": "Voice Agent API",
        "endpoints": [
            "POST /api/voice/speak",
            "GET /api/health"
        ],
        "port": 8002
    }


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("  🎤 Voice Agent Server Starting")
    print("  Port: 8002")
    print("  Endpoints:")
    print("    - POST /api/voice/speak (main voice endpoint)")
    print("    - GET /api/health (health check)")
    print("="*60 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
