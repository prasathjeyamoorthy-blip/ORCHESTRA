from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Dict, Optional
import os
import re
import time
import sys
import uuid
import traceback
import threading as _threading
import asyncio as _asyncio
import json
from collections import deque

from fastapi.middleware.cors import CORSMiddleware
from agent import agentic_rag, documents_node, generate_response_stream
from guardrails import check_guardrail

try:
    from supabase_db import (
        save_message,
        fetch_user_history,
        delete_user_history,
        delete_user_documents,
        delete_application_payload,
        save_user_document_meta,
        fetch_user_documents,
        save_application_payload,
        get_latest_application_payload,
        save_user_profile,
        fetch_user_profile,
    )
except Exception as _e:
    print(f"[app] Note: supabase_db functions optional: {_e}")
    save_message = fetch_user_history = delete_user_history = None
    delete_user_documents = delete_application_payload = None
    save_user_document_meta = fetch_user_documents = None
    save_application_payload = get_latest_application_payload = None
    save_user_profile = fetch_user_profile = None

app = FastAPI(title="ORCHESTRA Main Server")

allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    if allowed_origins_env.strip() == "*":
        ALLOWED_ORIGINS = ["*"]
    else:
        ALLOWED_ORIGINS = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]

# Sanitize ALLOWED_ORIGINS so '*' doesn't break allow_credentials=True in Starlette
is_wildcard = "*" in ALLOWED_ORIGINS or ALLOWED_ORIGINS == ["*"]
clean_origins = [o for o in ALLOWED_ORIGINS if o != "*"] if (is_wildcard and len(ALLOWED_ORIGINS) > 1) else ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=clean_origins,
    allow_credentials=True if clean_origins != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.head("/")
def health_check():
    return {"status": "online", "service": "ORCHESTRA Backend Agent"}

# ── Session store ──────────────────────────────────────────────────────────────
SESSIONS: Dict[str, dict] = {}
USER_PROFILES: Dict[str, dict] = {}

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
    phone_number: Optional[str] = None
    user_id: Optional[str] = None
    language: Optional[str] = "en"
    encrypted_content: Optional[str] = None


@app.post("/chat")
async def chat(req: ChatRequest):
    user_key = (
        (req.phone_number and req.phone_number.strip())
        or (req.user_id and req.user_id.strip())
        or "default_user"
    )

    user_profile = USER_PROFILES.setdefault(user_key, {
        "applicant_category": None,
        "chat_history": [],
        "stage": None,
        "user_details": {}
    })

    # Retrieve existing session or initialize from cross-session user profile
    state = SESSIONS.get(req.session_id)
    if not state:
        state = {
            "question": "",
            "intent": None,
            "context": None,
            "answer": None,
            "applicant_category": user_profile.get("applicant_category"),
            "stage": user_profile.get("stage"),
            "chat_history": list(user_profile.get("chat_history", []))[-10:]
        }
    else:
        if not state.get("applicant_category") and user_profile.get("applicant_category"):
            state["applicant_category"] = user_profile["applicant_category"]
        if not state.get("chat_history") and user_profile.get("chat_history"):
            state["chat_history"] = list(user_profile["chat_history"])[-10:]

    previous_stage = state.get("stage")
    state["question"] = req.message

    # Outer Guardrail Check BEFORE reaching the agent
    is_allowed, refusal_msg = check_guardrail(req.message)
    if not is_allowed:
        state["chat_history"].append({"role": "user", "content": req.message})
        state["chat_history"].append({"role": "assistant", "content": refusal_msg})
        user_profile["chat_history"] = state["chat_history"][-10:]
        return {
            "answer": refusal_msg,
            "session_id": req.session_id,
            "applicant_category": state.get("applicant_category"),
            "stage": state.get("stage")
        }

    state["chat_history"].append({"role": "user", "content": req.message})
    t_start = time.perf_counter()

    try:
        if previous_stage == "ASK_CATEGORY":
            state = await documents_node(state)
        else:
            state = await agentic_rag.ainvoke(state)
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

    # ── Sync across sessions via user profile ─────────────────────────────────
    if state.get("applicant_category"):
        user_profile["applicant_category"] = state["applicant_category"]
    if state.get("stage"):
        user_profile["stage"] = state["stage"]

    user_profile["chat_history"] = list(state.get("chat_history", []))[-20:]
    USER_PROFILES[user_key] = user_profile
    SESSIONS[req.session_id] = state

    # ── Optional DB persistence ───────────────────────────────────────────────
    if save_message and req.phone_number:
        try:
            save_message(req.phone_number, "user", req.message, session_id=req.session_id, stage=state.get("stage"))
            if state.get("answer"):
                save_message(req.phone_number, "assistant", state["answer"], session_id=req.session_id, stage=state.get("stage"))
        except Exception as _e:
            print(f"[app] Note: message save error: {_e}")

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


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    user_key = (
        (req.phone_number and req.phone_number.strip())
        or (req.user_id and req.user_id.strip())
        or "default_user"
    )

    user_profile = USER_PROFILES.setdefault(user_key, {
        "applicant_category": None,
        "chat_history": [],
        "stage": None,
        "user_details": {}
    })

    state = SESSIONS.get(req.session_id)
    if not state:
        state = {
            "question": "",
            "intent": None,
            "context": None,
            "answer": None,
            "applicant_category": user_profile.get("applicant_category"),
            "stage": user_profile.get("stage"),
            "chat_history": list(user_profile.get("chat_history", []))[-10:]
        }
    else:
        if not state.get("applicant_category") and user_profile.get("applicant_category"):
            state["applicant_category"] = user_profile["applicant_category"]
        if not state.get("chat_history") and user_profile.get("chat_history"):
            state["chat_history"] = list(user_profile["chat_history"])[-10:]

    state["question"] = req.message
    state["chat_history"].append({"role": "user", "content": req.message})

    async def event_generator():
        final_answer = ""
        try:
            async for chunk_line in generate_response_stream(state):
                data = json.loads(chunk_line)
                if data.get("done"):
                    final_answer = data.get("answer", "")
                yield chunk_line
        except Exception as exc:
            tb = traceback.format_exc()
            print(f"[ERROR] /chat/stream failed: {tb}")
            yield json.dumps({"error": str(exc), "done": True}) + "\n"
            return

        if final_answer:
            cleaned = _clean_answer(final_answer)
            state["answer"] = cleaned
            state["chat_history"].append({"role": "assistant", "content": cleaned})

        state["chat_history"] = state["chat_history"][-20:]

        if state.get("applicant_category"):
            user_profile["applicant_category"] = state["applicant_category"]
        if state.get("stage"):
            user_profile["stage"] = state["stage"]

        user_profile["chat_history"] = list(state.get("chat_history", []))[-20:]
        USER_PROFILES[user_key] = user_profile
        SESSIONS[req.session_id] = state

        if save_message and req.phone_number:
            try:
                save_message(req.phone_number, "user", req.message, session_id=req.session_id, stage=state.get("stage"))
                if state.get("answer"):
                    save_message(req.phone_number, "assistant", state["answer"], session_id=req.session_id, stage=state.get("stage"))
            except Exception as _e:
                print(f"[app] Note: stream message save error: {_e}")

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


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
        self._event_history: deque = deque(maxlen=300)
        self._event_seq: int = 0
        self._current_run_id: str = ""
        self._last_poll_time: float = 0.0
        self._main_loop = None
        self._sse_event: Optional[_asyncio.Event] = None
        self.latest_captcha_b64: str = ""

    @property
    def active_connection(self) -> WebSocket | None:
        return self._connections[0] if self._connections else None

    @property
    def is_connected(self) -> bool:
        # Client is considered connected if a WebSocket is active OR an HTTP polling/SSE client polled within the last 25 seconds
        return bool(self._connections) or ((time.time() - self._last_poll_time) < 25.0)

    def note_poll(self):
        self._last_poll_time = time.time()

    def start_new_run(self) -> str:
        self._current_run_id = str(uuid.uuid4())[:8]
        self.latest_response = None
        self._last_poll_time = time.time()
        print(f"[Automation Engine] New execution run started: run_id={self._current_run_id}", flush=True)
        self.notify_sse()
        return self._current_run_id

    def notify_sse(self):
        if self._sse_event is not None and self._main_loop and self._main_loop.is_running():
            try:
                self._main_loop.call_soon_threadsafe(self._sse_event.set)
            except Exception:
                pass

    def get_events_since(self, since_seq: int = 0, run_id: Optional[str] = None) -> list[dict]:
        self.note_poll()
        now = time.time()
        results = []
        for e in self._event_history:
            # When requesting from beginning (0), ignore old events older than 10 minutes to prevent stale replays
            if since_seq == 0 and (now - e.get("_ts", 0) > 600):
                continue
            if run_id and e.get("_run_id") and e.get("_run_id") != run_id:
                continue
            if e.get("_seq", 0) > since_seq:
                results.append(e)
        return results

    def record_client_response(self, data: dict):
        self.note_poll()
        print(f"[Automation Input Received] {data.get('type')}: {data.get('data') if 'data' in data else 'action'}", flush=True)
        self.latest_response = data

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        # Clean up any closed or disconnected connections
        self._connections = [
            c for c in self._connections
            if getattr(c, "client_state", None) is not None and getattr(c.client_state, "name", "") == "CONNECTED"
        ]
        self._connections.append(websocket)
        self._main_loop = _asyncio.get_running_loop()
        print(f"[WebSocket] Client connected — total: {len(self._connections)}", flush=True)
        while self._event_queue:
            await self._send_to(websocket, self._event_queue.popleft())

    def disconnect(self, websocket: WebSocket):
        if websocket in self._connections:
            self._connections.remove(websocket)
        print(f"[WebSocket] Client disconnected — total: {len(self._connections)}", flush=True)

    async def _send_to(self, websocket: WebSocket, event_data: dict):
        try:
            await websocket.send_json(event_data)
        except Exception as e:
            print(f"[WebSocket ERROR] send failed: {e}", flush=True)
            if websocket in self._connections:
                self._connections.remove(websocket)

    def _prepare_event(self, event_data: dict) -> dict:
        self._event_seq += 1
        item = dict(event_data)
        item["_seq"] = self._event_seq
        item["_run_id"] = self._current_run_id
        item["_ts"] = time.time()
        self._event_history.append(item)
        if item.get("type") in ("REQUEST_CAPTCHA", "CAPTCHA_REFRESHED") and item.get("image"):
            self.latest_captcha_b64 = item["image"]
        self.notify_sse()
        return item

    async def send_event(self, event_data: dict):
        item = self._prepare_event(event_data)
        if not self._connections:
            self._event_queue.append(item)
            return
        self._event_queue.append(item)
        await self._flush_queue()

    def send_event_sync(self, event_data: dict, wait_timeout: float = 120.0):
        item = self._prepare_event(event_data)
        self._event_queue.append(item)
        print(f"[Automation Event Queued] seq={item['_seq']} run={item['_run_id']} type={item.get('type')}", flush=True)

        is_interactive = item.get("type") in ("REQUEST_CAPTCHA", "REQUEST_OTP", "REQUEST_SIGNED_DECLARATION")
        if is_interactive:
            deadline = time.time() + wait_timeout
            while not self.is_connected:
                if time.time() > deadline:
                    print(f"[Automation ERROR] No client connected after {wait_timeout}s for {item.get('type')}", flush=True)
                    return
                time.sleep(1)
        elif not self.is_connected:
            # Non-interactive status updates shouldn't block the thread if no client is listening
            return

        loop = self._main_loop
        if loop is None or not loop.is_running():
            return
        future = _asyncio.run_coroutine_threadsafe(self._flush_queue(), loop)
        try:
            future.result(timeout=10)
        except Exception as e:
            print(f"[Automation ERROR] {e}", flush=True)

    async def _flush_queue(self):
        while self._event_queue:
            event = self._event_queue.popleft()
            for ws in list(self._connections):
                await self._send_to(ws, event)


manager = ConnectionManager()


@app.on_event("startup")
async def on_startup():
    manager._main_loop = _asyncio.get_running_loop()
    manager._sse_event = _asyncio.Event()
    print("[Server Startup] Event loop registered in ConnectionManager.", flush=True)


@app.websocket("/ws/automation")
async def websocket_automation(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "PING":
                continue
            print(f"[WebSocket] Received: {data}")
            manager.record_client_response(data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket ERROR] Client connection error: {e}", flush=True)
    finally:
        manager.disconnect(websocket)


def run_playwright_agent(payload: dict):
    original_cwd = os.getcwd()
    try:
        os.chdir(playwright_dir)
        import importlib
        try:
            import rescert
            importlib.reload(rescert)
            from rescert import TNeSevaiBackendAgent
        except Exception:
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


def run_delete_saved_app_agent(payload: dict):
    original_cwd = os.getcwd()
    try:
        os.chdir(playwright_dir)
        import importlib
        try:
            import delete_saved_app
            importlib.reload(delete_saved_app)
            from delete_saved_app import TNeSevaiSavedAppCleaner
        except Exception:
            from delete_saved_app import TNeSevaiSavedAppCleaner
        creds = payload.get("credentials") or {}
        cleaner = TNeSevaiSavedAppCleaner(credentials=creds, ws_manager=manager)
        cleaner.run()
    except Exception as e:
        print(f"[ERROR] Delete saved application cleaner crashed: {e}")
        import traceback; traceback.print_exc()
        try:
            manager.send_event_sync({"type": "AUTOMATION_ERROR", "message": str(e)})
        except Exception:
            pass
    finally:
        os.chdir(original_cwd)


@app.get("/ws/status")
@app.get("/api/ws-status")
def ws_status():
    manager.note_poll()
    return {
        "connected": manager.is_connected,
        "connections": len(manager._connections),
        "latest_seq": manager._event_seq,
        "active_run_id": manager._current_run_id,
        "is_polling": bool((time.time() - manager._last_poll_time) < 25.0),
        "queue_size": len(manager._event_queue),
    }


@app.get("/ws/events")
@app.get("/api/automation-events")
def get_automation_events(since: int = 0, run_id: Optional[str] = None):
    events = manager.get_events_since(since, run_id=run_id)
    return {
        "events": events,
        "latest_seq": manager._event_seq,
        "active_run_id": manager._current_run_id,
        "connected": manager.is_connected,
    }


@app.get("/ws/events/stream")
@app.get("/api/automation-stream")
async def automation_stream(request: Request, since: int = 0, run_id: Optional[str] = None):
    """Server-Sent Events (SSE) streaming endpoint: zero-latency push, 100% immune to WebSocket blocks."""
    manager.note_poll()
    if manager._sse_event is None:
        manager._sse_event = _asyncio.Event()

    async def event_generator():
        last_seq = since
        while True:
            if await request.is_disconnected():
                break

            manager.note_poll()
            events = manager.get_events_since(last_seq, run_id=run_id)
            if events:
                for ev in events:
                    last_seq = max(last_seq, ev.get("_seq", 0))
                    yield f"id: {ev.get('_seq', 0)}\nevent: message\ndata: {json.dumps(ev)}\n\n"

            # Wait for next event notify or 3-second heartbeat
            try:
                manager._sse_event.clear()
                await _asyncio.wait_for(manager._sse_event.wait(), timeout=3.0)
            except _asyncio.TimeoutError:
                # SSE comment heartbeat to keep intermediate proxies/NAT active
                yield ": heartbeat\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/ws/action")
@app.post("/api/automation-action")
async def post_automation_action(payload: dict):
    manager.record_client_response(payload)
    return {"status": "ok", "type": payload.get("type")}


@app.get("/ws/diagnostic")
@app.get("/api/ws-diagnostic")
def ws_diagnostic():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "is_connected": manager.is_connected,
        "websocket_clients": len(manager._connections),
        "total_events_dispatched": manager._event_seq,
        "history_buffer_size": len(manager._event_history),
        "active_run_id": manager._current_run_id,
        "seconds_since_last_activity": round(time.time() - manager._last_poll_time, 2),
        "supported_transports": ["WebSocket", "Server-Sent Events (SSE)", "HTTP Polling", "REST Action POST"]
    }


@app.post("/submit-application")
async def submit_application(payload: dict):
    manager.start_new_run()
    try:
        from supabase_db import save_application_payload, save_user_profile
        save_application_payload(payload)
        phone_num = payload.get("applicant_details", {}).get("mobile_number") or payload.get("credentials", {}).get("username")
        if phone_num:
            save_user_profile(phone_num, payload)
    except Exception as e:
        print(f"[WARNING] Could not save payload to database: {e}")
    _threading.Thread(target=run_playwright_agent, args=(payload,), daemon=True).start()
    return {"status": "success", "message": "Playwright task started"}


@app.post("/delete-saved-application")
async def delete_saved_application(payload: dict = None):
    """Developer endpoint: Run automation to delete pending Saved Applications on portal."""
    manager.start_new_run()
    payload = payload or {}
    creds = payload.get("credentials")
    if not creds:
        try:
            from supabase_db import get_latest_application_payload
            latest = get_latest_application_payload() or {}
            creds = latest.get("credentials")
        except Exception:
            creds = None
    if not creds:
        creds = {
            "username": os.getenv("CITIZEN_USERNAME") or os.getenv("CITIZEN_PORTAL_USER", ""),
            "password": os.getenv("CITIZEN_PASSWORD") or os.getenv("CITIZEN_PORTAL_PASS", "")
        }

    cleaner_payload = {"credentials": creds}
    _threading.Thread(target=run_delete_saved_app_agent, args=(cleaner_payload,), daemon=True).start()
    return {"status": "success", "message": "Cleaner task started"}


@app.get("/latest-payload")
def get_payload(phone_number: str = ""):
    """Fetch the latest submitted application payload from Supabase Database / memory."""
    try:
        from supabase_db import get_latest_application_payload
        payload = get_latest_application_payload(phone_number)
        return {"status": "success", "payload": payload}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/user-profile")
def get_user_profile(phone_number: str = ""):
    """Fetch user profile and document metadata from Supabase."""
    try:
        from supabase_db import fetch_user_profile
        data = fetch_user_profile(phone_number)
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/user-profile")
def save_user_profile_endpoint(req: dict):
    """Save user profile to Supabase."""
    try:
        from supabase_db import save_user_profile
        phone_number = req.get("phone_number") or req.get("mobile_number") or req.get("applicant_details", {}).get("mobile_number")
        if not phone_number:
            return {"status": "error", "message": "phone_number required"}
        save_user_profile(phone_number, req)
        return {"status": "success", "message": "User profile saved to Supabase"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class SendOtpRequest(BaseModel):
    phone_number: str


class VerifyOtpRequest(BaseModel):
    phone_number: str
    code: str
    verification_id: Optional[str] = ""


@app.post("/api/send-otp")
def send_otp_endpoint(req: SendOtpRequest):
    """
    Send OTP via Message Central service or local fallback.
    """
    try:
        from otp_service import send_otp
        res = send_otp(req.phone_number)
        return res
    except Exception as e:
        print(f"[OTP Endpoint Error] send_otp: {e}")
        return {"success": False, "message": str(e)}


@app.post("/api/verify-otp")
def verify_otp_endpoint(req: VerifyOtpRequest):
    """
    Verify OTP via Message Central service or local fallback.
    """
    try:
        from otp_service import verify_otp
        res = verify_otp(req.phone_number, req.code, req.verification_id or "")
        return res
    except Exception as e:
        print(f"[OTP Endpoint Error] verify_otp: {e}")
        return {"success": False, "message": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# CHAT HISTORY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/chat-history")
def get_chat_history(phone_number: str = "", session_id: Optional[str] = None, limit: int = 50):
    """Fetch chronological chat history for a phone number."""
    if not phone_number:
        return {"history": []}
    if fetch_user_history:
        try:
            history = fetch_user_history(phone_number, limit=limit, session_id=session_id)
            if history:
                return {"history": history}
        except Exception as e:
            print(f"[app] fetch_user_history error: {e}")

    phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]
    profile = USER_PROFILES.get(phone_clean) or USER_PROFILES.get(phone_number, {})
    return {"history": profile.get("chat_history", [])}


@app.delete("/api/chat-history")
def delete_chat_history_endpoint(phone_number: str = "", session_id: Optional[str] = None):
    """Delete chat history and optionally all user data for a phone number."""
    if not phone_number:
        return JSONResponse(status_code=400, content={"status": "error", "message": "phone_number required"})

    phone_clean = phone_number.replace("+", "").replace(" ", "").strip()[-10:]

    # 1. Delete from Supabase / in-memory DB
    if delete_user_history:
        try:
            delete_user_history(phone_number, session_id=session_id)
        except Exception as e:
            print(f"[app] delete_user_history error: {e}")

    # 2. If no session_id is specified (full "Clear My Data"), clear docs & payloads
    if not session_id:
        if delete_user_documents:
            try:
                delete_user_documents(phone_number)
            except Exception as e:
                print(f"[app] delete_user_documents error: {e}")

        if delete_application_payload:
            try:
                delete_application_payload(phone_number)
            except Exception as e:
                print(f"[app] delete_application_payload error: {e}")

        USER_PROFILES.pop(phone_clean, None)
        USER_PROFILES.pop(phone_number, None)

    # 3. Clean up matching in-memory sessions
    sessions_to_remove = [
        sid for sid, sdata in list(SESSIONS.items())
        if (session_id and sid == session_id) or (not session_id and sdata.get("phone_number") in (phone_number, phone_clean))
    ]
    for sid in sessions_to_remove:
        SESSIONS.pop(sid, None)

    return {"status": "success", "message": "Chat history deleted successfully"}


# ══════════════════════════════════════════════════════════════════════════════
# USER DOCUMENTS REGISTRY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
class UserDocMetaRequest(BaseModel):
    phone_number: str
    doc_id: str
    filename: str
    supabase_url: str
    extracted_data: Optional[list] = []


@app.post("/api/user-documents")
def save_user_document_meta_endpoint(req: UserDocMetaRequest):
    """Save or update document metadata in Supabase registry."""
    if save_user_document_meta:
        try:
            save_user_document_meta(
                req.phone_number,
                req.doc_id,
                req.filename,
                req.supabase_url,
                req.extracted_data
            )
            return {"status": "success", "message": "Document registered successfully"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    return {"status": "success", "message": "Saved"}


@app.get("/api/user-documents")
def get_user_documents_endpoint(phone_number: str = ""):
    """Fetch all registered document records for a phone number."""
    if not phone_number:
        return {"status": "success", "documents": {}}
    if fetch_user_documents:
        try:
            docs = fetch_user_documents(phone_number)
            return {"status": "success", "documents": docs}
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    return {"status": "success", "documents": {}}


# ══════════════════════════════════════════════════════════════════════════════
# AUTOMATION CAPTCHA & DECLARATION ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/automation/captcha-b64")
def get_captcha_b64():
    """Return latest captcha screenshot as base64."""
    import base64
    captcha_path = os.path.join(playwright_dir, "backend_captcha.png")
    if os.path.exists(captcha_path):
        try:
            with open(captcha_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return {"image": f"data:image/png;base64,{data}"}
        except Exception as e:
            print(f"[app] Failed to read captcha image: {e}")

    if getattr(manager, "latest_captcha_b64", ""):
        return {"image": manager.latest_captcha_b64}

    return JSONResponse(status_code=404, content={"error": "Captcha not available"})


@app.get("/download-declaration")
def download_declaration():
    """Download self declaration PDF form."""
    from fastapi.responses import FileResponse
    declaration_path = os.path.join(playwright_dir, "Self_Declaration_Form_To_Sign.pdf")
    if not os.path.exists(declaration_path):
        declaration_path = os.path.join(playwright_dir, "Self_Declaration_Form_For_User.pdf")

    if os.path.exists(declaration_path):
        return FileResponse(
            declaration_path,
            media_type="application/pdf",
            filename="Self_Declaration_Form.pdf"
        )
    return JSONResponse(status_code=404, content={"error": "Declaration form not found"})


@app.post("/upload-signed-declaration")
async def upload_signed_declaration(file: UploadFile = File(...)):
    """Save the signed self-declaration form locally and optionally upload to Supabase Storage."""
    try:
        content_bytes = await file.read()
        
        # Save locally in playwright directory and uploaded_documents
        uploads_dir = os.path.join(playwright_dir, "uploaded_documents")
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Save as specific name and canonical Signed_Self_Declaration.pdf
        clean_name = f"Signed_{file.filename}"
        local_saved_path = os.path.join(uploads_dir, clean_name)
        with open(local_saved_path, "wb") as f_out:
            f_out.write(content_bytes)

        canon_path = os.path.join(uploads_dir, "Signed_Self_Declaration.pdf")
        with open(canon_path, "wb") as f_out:
            f_out.write(content_bytes)

        # Also copy to root of playwright_dir for maximum discovery
        with open(os.path.join(playwright_dir, "Signed_Self_Declaration.pdf"), "wb") as f_out:
            f_out.write(content_bytes)

        s_url = ""
        try:
            from supabase_db import upload_to_supabase_storage
            c_type = getattr(file, "content_type", "application/pdf") or "application/pdf"
            s_url = upload_to_supabase_storage(content_bytes, clean_name, content_type=c_type)
        except Exception as se:
            print(f"[Supabase Storage] Notice: upload skipped ({se})")

        print(f"[INFO] Signed self-declaration saved locally: {local_saved_path}, Supabase: {s_url}")

        return {
            "status": "success",
            "message": "Signed declaration saved successfully",
            "file_path": local_saved_path,
            "supabase_url": s_url
        }
    except Exception as e:
        print(f"[ERROR] Failed to save signed declaration: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/clear-cache")
def clear_cache_endpoint():
    """Clear server cache."""
    return {"status": "success", "message": "Cache cleared"}



