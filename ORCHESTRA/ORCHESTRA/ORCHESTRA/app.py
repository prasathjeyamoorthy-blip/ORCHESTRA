from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict
import os
import re
import time
import sys
import traceback
import threading as _threading
import asyncio as _asyncio
from collections import deque

from fastapi.middleware.cors import CORSMiddleware
from agent import agentic_rag, documents_node

app = FastAPI(title="ORCHESTRA Main Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://[REPLACE_WITH_ELASTIC_IP]",
        "http://[REPLACE_WITH_ELASTIC_IP]:80"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Session store ──────────────────────────────────────────────────────────────
SESSIONS: Dict[str, dict] = {}

# ── Response time warning threshold (ms) ──────────────────────────────────────
_MAX_MS = 3000   # warn if slower than this

# ── Timing log ─────────────────────────────────────────────────────────────────
_TIMING_LOG: list = []

# ── Answer post-processing ─────────────────────────────────────────────────────
_STRIP_PATTERNS = [
    r"(?i)additionally[^.]*?(?:applicant|you|user)\s+needs?\s+to\s+provide\s+personal\s+details[^:]*:[\s\S]*?(?=\n\n|\Z)",
    r"(?i)(?:[-•*]\s*applicant\s+(?:father\s+name|mobile\s+number|email\s+id|date\s+of\s+birth)[^\n]*\n?)+",
    r"(?i)(?:you\s+will\s+need\s+to|the\s+applicant\s+needs?\s+to)\s+provide\s+personal\s+details[^:]*:[\s\S]*?(?=\n\n|\Z)",
]

def _fix_markdown(text: str) -> str:
    """Fix malformed markdown produced by the LLM."""
    # Strip filler openers
    text = re.sub(
        r"^(I will handle this for you\.?\s*|According to the context,?\s*|"
        r"I will take care of this\.?\s*|I am submitting on your behalf\.?\s*)",
        "", text, flags=re.IGNORECASE
    ).lstrip()

    lines = text.split("\n")
    fixed = []
    for line in lines:
        # Fix numbered list items that contain stray asterisks used as sub-bullets
        # e.g. "4. *5. *6. *7.* **Current Address Proof**"
        # → split into proper list items
        m = re.match(r'^(\d+)\.\s+(\*\d+\.\s+)+\*?\s*(.+)$', line)
        if m:
            # Extract the actual content after all the stray *N. markers
            content = re.sub(r'\*\d+\.\s*', '', line)
            content = re.sub(r'^\d+\.\s+', '', content).strip()
            line = f"- {content}"

        # Fix lines that are just stray asterisk-number patterns like "*5." or "* 6."
        line = re.sub(r'^\s*\*(\d+)\.\s*', r'\1. ', line)

        # Fix bold markers with spaces: "** text **" → "**text**"
        line = re.sub(r'\*\*\s+(.+?)\s+\*\*', r'**\1**', line)

        fixed.append(line)
    return "\n".join(fixed)

def _clean_answer(text: str) -> str:
    for pattern in _STRIP_PATTERNS:
        text = re.sub(pattern, "", text)
    text = _fix_markdown(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ══════════════════════════════════════════════════════════════════════════════
# CHAT ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════
class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    state = SESSIONS.get(req.session_id) or {
        "question": "", "intent": None, "context": None,
        "answer": None, "applicant_category": None,
        "stage": None, "chat_history": []
    }
    if not state.get("chat_history"):
        state["chat_history"] = []

    previous_stage = state.get("stage")
    state["question"] = req.message
    state["chat_history"].append({"role": "user", "content": req.message})

    t_start = time.perf_counter()

    try:
        if previous_stage == "ASK_CATEGORY":
            state = documents_node(state)
        else:
            state = agentic_rag.invoke(state)
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[ERROR] /chat failed:\n{tb}")
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "traceback": tb}
        )

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    total_ms = round(elapsed_ms)

    if total_ms > _MAX_MS:
        print(f"[TIMING] WARNING: response took {total_ms}ms (>{_MAX_MS}ms target)")

    # ── Clean answer ──────────────────────────────────────────────────────────
    if state.get("answer"):
        state["answer"] = _clean_answer(state["answer"])
        state["chat_history"].append({"role": "assistant", "content": state["answer"]})

    state["chat_history"] = state["chat_history"][-20:]
    SESSIONS[req.session_id] = state

    # ── Log ───────────────────────────────────────────────────────────────────
    intent = (state.get("intent") or {}).get("primary", "unknown")
    entry = {
        "session_id": req.session_id[:8],
        "message": req.message[:60],
        "intent": intent,
        "elapsed_ms": total_ms,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
    }
    _TIMING_LOG.append(entry)
    print(f"[TIMING] {entry['timestamp']} | intent={intent} | {total_ms}ms | \"{req.message[:40]}\"")

    return {
        "answer": state.get("answer"),
        "stage": state.get("stage"),
        "category": state.get("applicant_category"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# TIMINGS ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/chat/timings")
def get_timings(last: int = 50):
    entries = _TIMING_LOG[-last:]
    if not entries:
        return {"count": 0, "timings": []}
    avg = round(sum(e["elapsed_ms"] for e in entries) / len(entries))
    return {
        "count": len(entries),
        "avg_ms": avg,
        "fastest_ms": min(e["elapsed_ms"] for e in entries),
        "slowest_ms": max(e["elapsed_ms"] for e in entries),
        "timings": list(reversed(entries)),
    }


# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET / PLAYWRIGHT
# ══════════════════════════════════════════════════════════════════════════════
playwright_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "Playwright"))
if playwright_dir not in sys.path:
    sys.path.append(playwright_dir)


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self.latest_response: dict = None
        self._event_queue: deque = deque()
        self._main_loop = None

    @property
    def active_connection(self) -> WebSocket | None:
        return self._connections[0] if self._connections else None

    @property
    def is_connected(self) -> bool:
        return bool(self._connections)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.append(websocket)
        self._main_loop = _asyncio.get_running_loop()
        print(f"[WebSocket] Client connected — total: {len(self._connections)}")
        while self._event_queue:
            await self._send_to(websocket, self._event_queue.popleft())

    def disconnect(self, websocket: WebSocket):
        if websocket in self._connections:
            self._connections.remove(websocket)
        print(f"[WebSocket] Client disconnected — total: {len(self._connections)}")

    async def _send_to(self, websocket: WebSocket, event_data: dict):
        try:
            await websocket.send_json(event_data)
        except Exception as e:
            print(f"[WebSocket ERROR] send failed: {e}")

    async def send_event(self, event_data: dict):
        if not self._connections:
            self._event_queue.append(event_data)
            return
        self._event_queue.append(event_data)
        await self._flush_queue()

    def send_event_sync(self, event_data: dict, wait_timeout: float = 120.0):
        self._event_queue.append(event_data)
        print(f"[WebSocket] Event queued: {event_data.get('type')}")
        deadline = time.time() + wait_timeout
        while not self._connections:
            if time.time() > deadline:
                print(f"[WebSocket ERROR] No client after {wait_timeout}s")
                return
            time.sleep(1)
        loop = self._main_loop
        if loop is None or not loop.is_running():
            return
        future = _asyncio.run_coroutine_threadsafe(self._flush_queue(), loop)
        try:
            future.result(timeout=10)
        except Exception as e:
            print(f"[WebSocket ERROR] {e}")

    async def _flush_queue(self):
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


def run_playwright_agent(payload: dict):
    original_cwd = os.getcwd()
    try:
        os.chdir(playwright_dir)
        from rescert import TNeSevaiBackendAgent
        TNeSevaiBackendAgent(payload, ws_manager=manager).run()
    except Exception as e:
        print(f"[ERROR] Playwright agent crashed: {e}")
        import traceback; traceback.print_exc()
        try:
            manager.send_event_sync({"type": "AUTOMATION_ERROR", "message": str(e)})
        except Exception:
            pass
    finally:
        os.chdir(original_cwd)


@app.get("/ws/status")
def ws_status():
    return {"connected": manager.is_connected}


@app.post("/submit-application")
async def submit_application(payload: dict):
    try:
        import json as _json
        with open(os.path.join(playwright_dir, "last_payload.json"), "w") as f:
            _json.dump(payload, f, indent=2)
    except Exception as e:
        print(f"[WARNING] Could not save payload: {e}")
    _threading.Thread(target=run_playwright_agent, args=(payload,), daemon=True).start()
    return {"status": "success", "message": "Playwright task started"}
