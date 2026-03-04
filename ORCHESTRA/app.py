from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import Dict
import requests
import shutil
import os

from fastapi.middleware.cors import CORSMiddleware

# --------------------------------
# Import agent + deterministic nodes
# --------------------------------
from agent import (
    agentic_rag, 
    extract_category,
    documents_node
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------
# In-memory session store
# --------------------------------
SESSIONS: Dict[str, dict] = {}

UPLOAD_AGENT_URL = "http://localhost:8002/extract"
TEMP_UPLOAD_DIR = "temp_uploads"
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)


# ================================
# CHAT ENDPOINT (UNCHANGED)
# ================================
class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    state = SESSIONS.get(req.session_id)

    if not state:
        state = {
            "question": "",
            "intent": None,
            "context": None,
            "answer": None,
            "applicant_category": None,
            "stage": None
        }

    previous_stage = state.get("stage")

    state["question"] = req.message

    if previous_stage == "ASK_CATEGORY":
        state = extract_category(state)
        state = documents_node(state)
    else:
        state = agentic_rag.invoke(state)

    SESSIONS[req.session_id] = state

    return {
        "answer": state.get("answer"),
        "stage": state.get("stage"),
        "category": state.get("applicant_category")
    }


# ================================
# DOCUMENT UPLOAD ENDPOINT (NEW)
# ================================
@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    temp_path = os.path.join(TEMP_UPLOAD_DIR, file.filename)

    # Save temporarily
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print(f"\n📥 [RAG AGENT] File received: {file.filename}")

    # Forward to Document Upload Agent
    with open(temp_path, "rb") as f:
        files = {
            "file": (file.filename, f, file.content_type)
        }
        response = requests.post(UPLOAD_AGENT_URL, files=files)
        response.raise_for_status()

    extracted_json = response.json()

    print("\n📦 --- EXTRACTED JSON RECEIVED IN RAG AGENT ---\n")
    print(extracted_json)

    # 🔜 OPTIONAL (future):
    # - store in session
    # - embed & push to vector DB
    # - connect to documents_node

    return {
        "status": "success",
        "extracted_data": extracted_json
    }
