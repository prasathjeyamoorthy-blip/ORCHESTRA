# api/voice_main.py
# Standalone Voice Agent server - runs on port 8002.
# Handles STT, TTS, and the full voice speak pipeline.
#
# Start with:
#   .venv\Scripts\uvicorn api.voice_main:app --host 0.0.0.0 --port 8002 --reload

import os
import sys
from pathlib import Path

# Fix HF cache path
os.environ["HF_HOME"] = os.path.join(os.path.dirname(__file__), "..", "hf_cache")
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.voice import voice_router

app = FastAPI(
    title="PAN Voice Agent",
    description="STT → RAG+LLM → TTS voice pipeline for PAN services",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount voice routes under /api so they match the proxy config
app.include_router(voice_router, prefix="/api")


@app.get("/")
def root():
    return {"service": "voice-agent", "status": "ok"}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "voice-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.voice_main:app", host="0.0.0.0", port=8002, reload=False)
