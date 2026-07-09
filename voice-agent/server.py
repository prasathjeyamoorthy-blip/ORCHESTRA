"""
server.py — FastAPI HTTP server for the voice agent

Routes all STT, TTS, and Speak requests to the cloud-based voice router from pan-rag,
enabling native Tamil and English speech processing using NVIDIA NIM cloud APIs.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load pan-rag/.env first to get Supabase and Upstash configurations
pan_rag_env = Path(__file__).parent.parent / "pan-rag" / ".env"
load_dotenv(dotenv_path=pan_rag_env)

# Load voice-agent/.env to overwrite local keys if needed
load_dotenv()

# Add pan-rag to system path so it can import the routes and database clients
sys.path.insert(0, str(Path(__file__).parent.parent / "pan-rag"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.voice import voice_router

app = FastAPI(title="Voice Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_router, prefix="/api")


@app.get("/")
def root():
    return {"service": "voice-agent", "status": "ok"}


@app.get("/api/health")
async def health():
    """Enhanced health check for voice agent service"""
    import httpx
    from datetime import datetime
    
    health_status = {
        "status": "ok",
        "service": "voice-agent", 
        "timestamp": datetime.utcnow().isoformat(),
        "port": 8002,
        "services": {}
    }
    try:
        sarvam_key = os.getenv("SARVAM_API_KEY")
        if sarvam_key:
            health_status["services"]["sarvam_ai"] = {
                "status": "configured",
                "api_key_present": True,
                "models": {
                    "stt": os.getenv("SARVAM_STT_MODEL", "saaras:v3"),
                    "tts": os.getenv("SARVAM_TTS_MODEL", "bulbul:v3"),
                }
            }
        else:
            health_status["services"]["sarvam_ai"] = {
                "status": "misconfigured",
                "api_key_present": False,
            }
    except Exception as e:
        health_status["services"]["sarvam_ai"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check pan-rag connectivity
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get("http://localhost:8000/api/health")
            if response.status_code == 200:
                health_status["services"]["pan_rag"] = {
                    "status": "online",
                    "accessible": True
                }
            else:
                health_status["services"]["pan_rag"] = {
                    "status": "degraded", 
                    "accessible": False,
                    "http_status": response.status_code
                }
    except Exception as e:
        health_status["services"]["pan_rag"] = {
            "status": "offline",
            "accessible": False,
            "error": str(e)
        }
    
    # Determine overall status
    service_issues = [
        service for service in health_status["services"].values()
        if service.get("status") not in ["online", "configured"]
    ]
    
    if service_issues:
        health_status["status"] = "degraded" if len(service_issues) < len(health_status["services"]) else "unhealthy"
    
    return health_status
