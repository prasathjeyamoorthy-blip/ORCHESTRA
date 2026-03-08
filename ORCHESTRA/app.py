from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
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
# PLAYWRIGHT INTEGRATION
# ================================
import sys
from fastapi import BackgroundTasks

# Add Playwright folder to Python path
playwright_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Playwright"))
if playwright_dir not in sys.path:
    sys.path.append(playwright_dir)

# Global WebSocket Manager for Automation Events
class ConnectionManager:
    def __init__(self):
        self.active_connection: WebSocket = None
        self.latest_response: dict = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connection = websocket
        print("[WebSocket] Automation Frontend Connected")

    def disconnect(self):
        self.active_connection = None
        print("[WebSocket] Automation Frontend Disconnected")

    async def send_event(self, event_data: dict):
        if self.active_connection:
            try:
                await self.active_connection.send_json(event_data)
            except Exception as e:
                print(f"[WebSocket WARNING] Error sending event: {e}")
        else:
            print("[WebSocket WARNING] Tried to emit event but frontend is disconnected:", event_data)

manager = ConnectionManager()

@app.websocket("/ws/automation")
async def websocket_automation(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            print(f"[WebSocket] Received from frontend: {data}")
            # Store the latest valid answer emitted by React
            manager.latest_response = data
    except WebSocketDisconnect:
        manager.disconnect()

@app.get("/automation/captcha")
def get_captcha():
    # Serve the captcha saved by playwright
    captcha_path = os.path.join(playwright_dir, "backend_captcha.png")
    if os.path.exists(captcha_path):
        return FileResponse(captcha_path)
    return {"error": "Captcha not found"}

def run_playwright_agent(payload: dict, loop=None):
    original_cwd = os.getcwd()
    try:
        os.chdir(playwright_dir)
        from rescert import TNeSevaiBackendAgent
        # Pass the global manager reference to the agent
        agent = TNeSevaiBackendAgent(payload, ws_manager=manager, loop=loop)
        agent.run()
    finally:
        os.chdir(original_cwd)

@app.post("/submit-application")
async def submit_application(payload: dict, background_tasks: BackgroundTasks):
    import asyncio
    loop = asyncio.get_running_loop()
    background_tasks.add_task(run_playwright_agent, payload, loop)
    return {"status": "success", "message": "Playwright task started"}
