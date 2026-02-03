from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict

# Import agent + deterministic nodes
from agent import (
    agentic_rag,
    extract_category,
    documents_node
)

app = FastAPI()

# --------------------------------
# In-memory session store
# --------------------------------
SESSIONS: Dict[str, dict] = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    # -----------------------------
    # Load or initialize state
    # -----------------------------
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

    # Always update the user question
    state["question"] = req.message

    # =================================================
    # 🔒 HARD CATEGORY FLOW (NO LLM GUESSING HERE)
    # =================================================
    if previous_stage == "ASK_CATEGORY":
        # Deterministic extraction
        state = extract_category(state)

        # Immediate document retrieval
        state = documents_node(state)

    else:
        # =================================================
        # NORMAL FLOW
        # Agent graph enforces retrieval internally
        # =================================================
        state = agentic_rag.invoke(state)

    # Persist session state
    SESSIONS[req.session_id] = state

    return {
        "answer": state.get("answer"),
        "stage": state.get("stage"),
        "category": state.get("applicant_category")
    }
