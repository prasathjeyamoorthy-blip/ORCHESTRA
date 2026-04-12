# api/main.py

import os
os.environ["HF_HOME"] = "D:\\hf_cache"

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router, get_chain

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
    """Load the RAG chain when server starts — not on first request."""
    print("Pre-loading RAG chain...")
    get_chain()
    print("✅ Server ready to accept requests")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)