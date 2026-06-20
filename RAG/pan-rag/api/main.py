# api/main.py

import os
# Fix HF cache path for Linux
os.environ["HF_HOME"] = os.path.join(os.path.dirname(__file__), "..", "hf_cache")

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from api.chain_instance import get_chain

app = FastAPI(
    title="PAN RAG Chatbot",
    description="AI assistant for Protean PAN Services",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Pre-load RAG chain at startup."""
    print("Pre-loading RAG chain...")
    get_chain()
    print(f"✅ RAG chain ready — model: {os.getenv('LLM_MODEL', 'meta/llama-3.1-70b-instruct')} via NVIDIA NIM")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)