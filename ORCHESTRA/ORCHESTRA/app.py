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
            "stage": None,
            "chat_history": []
        }

    # Ensure chat_history exists for old sessions that pre-date this feature
    if "chat_history" not in state or state["chat_history"] is None:
        state["chat_history"] = []

    previous_stage = state.get("stage")
    state["question"] = req.message

    # Append user turn to history BEFORE invoking agent
    state["chat_history"].append({"role": "user", "content": req.message})

    if previous_stage == "ASK_CATEGORY":
        state = extract_category(state)
        state = documents_node(state)
    else:
        state = agentic_rag.invoke(state)

    # Append assistant reply to history AFTER getting the answer
    if state.get("answer"):
        state["chat_history"].append({"role": "assistant", "content": state["answer"]})

    # Cap history to last 20 turns (10 exchanges) to avoid unbounded growth
    state["chat_history"] = state["chat_history"][-20:]

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
import asyncio as _asyncio
import threading as _threading
from collections import deque

# Add Playwright folder to Python path
playwright_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Playwright"))
if playwright_dir not in sys.path:
    sys.path.append(playwright_dir)


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []   # all active sockets
        self.latest_response: dict = None
        self._event_queue: deque = deque()         # events queued before any client connects
        self._main_loop = None                     # the uvicorn event loop

    # ── properties ────────────────────────────────────────────────────────────
    @property
    def active_connection(self) -> WebSocket | None:
        return self._connections[0] if self._connections else None

    @property
    def is_connected(self) -> bool:
        return len(self._connections) > 0

    # ── lifecycle ─────────────────────────────────────────────────────────────
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.append(websocket)
        self._main_loop = _asyncio.get_running_loop()
        print(f"[WebSocket] Client connected  — total: {len(self._connections)}")

        # Flush any events that were queued before this client arrived
        while self._event_queue:
            queued = self._event_queue.popleft()
            print(f"[WebSocket] Flushing queued event: {queued.get('type')}")
            await self._send_to(websocket, queued)

    def disconnect(self, websocket: WebSocket):
        if websocket in self._connections:
            self._connections.remove(websocket)
        print(f"[WebSocket] Client disconnected — total: {len(self._connections)}")

    # ── internal send ─────────────────────────────────────────────────────────
    async def _send_to(self, websocket: WebSocket, event_data: dict):
        try:
            await websocket.send_json(event_data)
        except Exception as e:
            print(f"[WebSocket ERROR] send failed: {e}")

    # ── async send (called from the event loop) ───────────────────────────────
    async def send_event(self, event_data: dict):
        if not self._connections:
            print(f"[WebSocket] No client yet — queuing: {event_data.get('type')}")
            self._event_queue.append(event_data)
            return
        self._event_queue.append(event_data)
        await self._flush_queue()

    # ── sync send (called from Playwright thread) ─────────────────────────────
    def send_event_sync(self, event_data: dict, wait_timeout: float = 120.0):
        """
        Send event to frontend. If no client is connected, wait up to
        wait_timeout seconds for one to connect, then send.
        Always queues the event so it's flushed on reconnect too.
        """
        import time as _time

        # Always queue so reconnecting clients get it immediately
        self._event_queue.append(event_data)
        print(f"[WebSocket] Event queued: {event_data.get('type')}")

        # Wait for a client to be connected
        deadline = _time.time() + wait_timeout
        while not self._connections:
            if _time.time() > deadline:
                print(f"[WebSocket ERROR] No client connected after {wait_timeout}s — event stays queued: {event_data.get('type')}")
                return
            print(f"[WebSocket] Waiting for client to connect before sending {event_data.get('type')}...")
            _time.sleep(1)

        loop = self._main_loop
        if loop is None or not loop.is_running():
            print(f"[WebSocket ERROR] No event loop — event stays queued: {event_data.get('type')}")
            return

        # Flush the queue (sends our event + any others pending)
        future = _asyncio.run_coroutine_threadsafe(self._flush_queue(), loop)
        try:
            future.result(timeout=10)
            print(f"[WebSocket] Event sent: {event_data.get('type')}")
        except Exception as e:
            print(f"[WebSocket ERROR] Failed to send {event_data.get('type')}: {e}")

    async def _flush_queue(self):
        """Send all queued events to all connected clients."""
        while self._event_queue:
            event = self._event_queue.popleft()
            for ws in list(self._connections):
                await self._send_to(ws, event)


manager = ConnectionManager()


@app.websocket("/ws/automation")
async def websocket_automation(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "PING":
                continue
            print(f"[WebSocket] Received: {data}")
            manager.latest_response = data
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/automation/captcha")
def get_captcha():
    # Serve the captcha saved by playwright
    captcha_path = os.path.join(playwright_dir, "backend_captcha.png")
    if os.path.exists(captcha_path):
        return FileResponse(
            captcha_path,
            media_type="image/png",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            }
        )
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={"error": "Captcha not found"})

@app.get("/automation/captcha-b64")
def get_captcha_b64():
    """Return captcha as base64 so the frontend can embed it directly — avoids any caching/CORS issues."""
    import base64
    captcha_path = os.path.join(playwright_dir, "backend_captcha.png")
    if os.path.exists(captcha_path):
        with open(captcha_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return {"image": f"data:image/png;base64,{data}"}
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={"error": "Captcha not found"})

@app.get("/download-declaration")
def download_declaration():
    # Serve the self-declaration form for download
    declaration_path = os.path.join(playwright_dir, "Self_Declaration_Form_To_Sign.pdf")
    if os.path.exists(declaration_path):
        return FileResponse(
            declaration_path,
            media_type="application/pdf",
            filename="Self_Declaration_Form.pdf"
        )
    return {"error": "Declaration form not found"}

@app.post("/upload-signed-declaration")
async def upload_signed_declaration(file: UploadFile = File(...)):
    """Save the signed self-declaration form uploaded by user"""
    try:
        # Save to Playwright uploaded_documents directory
        uploaded_docs_dir = os.path.join(playwright_dir, "uploaded_documents")
        os.makedirs(uploaded_docs_dir, exist_ok=True)
        
        save_path = os.path.join(uploaded_docs_dir, f"Signed_Self_Declaration_{file.filename}")
        
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"[INFO] Signed self-declaration saved: {save_path}")
        
        return {
            "status": "success",
            "message": "Signed declaration uploaded successfully",
            "file_path": os.path.abspath(save_path)
        }
    except Exception as e:
        print(f"[ERROR] Failed to save signed declaration: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

import threading as _threading

def run_playwright_agent(payload: dict, loop=None):
    original_cwd = os.getcwd()
    try:
        os.chdir(playwright_dir)
        from rescert import TNeSevaiBackendAgent
        agent = TNeSevaiBackendAgent(payload, ws_manager=manager)
        agent.run()
    except Exception as e:
        print(f"[ERROR] Playwright agent crashed: {e}")
        import traceback
        traceback.print_exc()
        try:
            manager.send_event_sync({
                "type": "AUTOMATION_ERROR",
                "message": f"Automation failed: {str(e)}"
            })
        except Exception:
            pass
    finally:
        os.chdir(original_cwd)

@app.post("/upload-documents")
async def upload_documents(
    aadhaar: UploadFile = File(None),
    ration:  UploadFile = File(None),
    driving: UploadFile = File(None),
    photo:   UploadFile = File(None),
):
    """
    Receives document files from the frontend and saves them to the
    Playwright uploaded_documents directory so the automation agent
    can read them by local path.
    """
    upload_dir = os.path.join(playwright_dir, "uploaded_documents")
    os.makedirs(upload_dir, exist_ok=True)

    saved = {}
    for key, file_obj in [("aadhaar", aadhaar), ("ration", ration), ("driving", driving), ("photo", photo)]:
        if file_obj:
            dest = os.path.join(upload_dir, file_obj.filename)
            with open(dest, "wb") as f:
                shutil.copyfileobj(file_obj.file, f)
            saved[key] = os.path.abspath(dest)
            print(f"[upload-documents] Saved {key} → {saved[key]}")

    return {"status": "success", "saved_paths": saved}



    return {"connected": manager.is_connected}

@app.post("/submit-application")
async def submit_application(payload: dict):
    # Save payload for standalone testing
    try:
        import json as _json
        payload_path = os.path.join(playwright_dir, "last_payload.json")
        with open(payload_path, "w", encoding="utf-8") as f:
            _json.dump(payload, f, indent=2)
        print(f"[INFO] Payload saved to {payload_path}")
    except Exception as e:
        print(f"[WARNING] Could not save payload: {e}")

    # Run in a daemon thread — won't block uvicorn shutdown
    # The thread itself will call wait_for_client() before emitting any WS events
    t = _threading.Thread(target=run_playwright_agent, args=(payload,), daemon=True)
    t.start()
    return {"status": "success", "message": "Playwright task started"}

