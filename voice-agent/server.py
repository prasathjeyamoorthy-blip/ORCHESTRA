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
def health():
    return {"status": "ok", "service": "voice-agent"}
