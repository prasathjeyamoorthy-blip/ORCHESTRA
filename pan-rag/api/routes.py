# api/routes.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from api.schemas import QuestionRequest, AnswerResponse
from api.chain_instance import get_chain
import traceback
import json
from fastapi import UploadFile, File, Form
from agent.receptionist import handle_document_upload, merge_form_fields
import shutil
import httpx
from pathlib import Path
from api.voice import voice_router

router = APIRouter()
router.include_router(voice_router)

# URL of the document upload agent (Flask, port 5001)
DOC_AGENT_URL = "http://localhost:5001/api/upload"

# ── Steps where "No" / "N" is a valid answer, never a cancellation ──────────
_YES_NO_ANSWER_STEPS = {
    "aadhaar_photo", "rep_assessee", "confirmation",
}

def _safe_question(question: str, session_id: str) -> str:
    """
    Guard: if the current flow step expects a Yes/No answer, never let a bare
    'no' / 'n' reach the cancellation detector.
    Also handles the email_confirm sub-step inside details_collection.
    """
    q = question.strip()
    if q.lower() not in ("no", "n", "nope", "nah"):
        return question
    try:
        from agent.flow_manager import FlowManager
        fm = FlowManager(session_id)
        if fm.has_active_flow():
            step = fm.get_current_step()
            # Standard yes/no steps
            if step in _YES_NO_ANSWER_STEPS:
                return "No"
            # Email confirm sub-step inside details_collection
            if step == "details_collection" and fm.state.get("_email_confirm_asked") and not fm.state.get("email"):
                return "No"
    except Exception:
        pass
    return question


@router.delete("/session/{session_id}")
def reset_session(session_id: str):
    """Clear flow state and memory for a session (called when session is created or deleted)."""
    from agent.flow_manager import FlowManager, SESSIONS_DIR
    from memory.memory_manager import MemoryManager

    # Delete flow state file
    state_file = SESSIONS_DIR / f"{session_id}.json"
    if state_file.exists():
        state_file.unlink()

    # Clear session memory from Upstash
    try:
        mm = MemoryManager()
        mm._del(f"session:{session_id}:history")
    except Exception:
        pass

    return {"cleared": session_id}


@router.post("/ask", response_model=AnswerResponse)
def ask(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    import time
    _t = time.time()
    safe_q = _safe_question(request.question, request.session_id or "")

    try:
        result = get_chain().run(
            question=safe_q,
            session_id=request.session_id,
            user_id=request.user_id,
            user_context=request.user_context,
            account_email=request.account_email or "",
            language_override=request.language or None,
        )
        elapsed_ms = int((time.time() - _t) * 1000)
        print(f"[ask] intent={result.get('intent','?')} | {elapsed_ms}ms | q={request.question[:60]!r}")
        result["elapsed_ms"] = elapsed_ms
        return AnswerResponse(**result)
    except Exception as e:
        elapsed_ms = int((time.time() - _t) * 1000)
        print(f"[ask] ERROR after {elapsed_ms}ms: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-stream")
def ask_stream(request: QuestionRequest):
    """
    SSE streaming endpoint.
    Runs all pre-LLM logic (intent, retrieval, flow) synchronously,
    then streams the final LLM answer token-by-token.

    Event format:
      data: {"type": "meta",  ...session_id, intent, sources, followups, open_upload, form_data}
      data: {"type": "token", "text": "..."}
      data: {"type": "done"}
      data: {"type": "error", "message": "..."}
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    safe_q = _safe_question(request.question, request.session_id or "")
    chain = get_chain()

    def event_stream():
        try:
            # Run the full chain in streaming mode
            yield from chain.run_stream(
                question=safe_q,
                session_id=request.session_id,
                user_id=request.user_id,
                user_context=request.user_context,
                account_email=request.account_email or "",
                language_override=request.language or None,
            )
        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
def health():
    return {"status": "ok"}

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_document(
    session_id: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    message: str = Form(default=""),
):
    # Save file locally using {username}_{doctype} naming
    dest = UPLOAD_DIR / session_id
    dest.mkdir(parents=True, exist_ok=True)

    # Build stored filename: {username}_{doctype}.{ext}
    from agent.flow_manager import FlowManager as _FM
    _fm = _FM(session_id)
    _username = (_fm.state.get("full_name") or "user").split()[0].lower()
    import re as _re
    _username = _re.sub(r'[^a-z0-9]', '', _username) or "user"
    _ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    stored_filename = f"{_username}_{doc_type.lower().replace(' ', '_')}{_ext}"
    file_path = dest / stored_filename

    file_bytes = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # ── Forward to document upload agent for extraction + verification ──
    extraction_result = {}
    agent_error = None
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                DOC_AGENT_URL,
                data={"session_id": session_id, "doc_type": doc_type},
                files={"file": (file.filename, file_bytes, file.content_type or "application/octet-stream")},
            )
        if response.status_code == 200:
            extraction_result = response.json()
        else:
            agent_error = response.json().get("error", "Document agent returned an error")
    except httpx.ConnectError:
        agent_error = "Document extraction service is offline. File saved — extraction skipped."
    except Exception as e:
        agent_error = f"Document extraction failed: {str(e)}"

    # ── Extract form fields from the accompanying message text ──
    if message.strip():
        from agent.flow_manager import FlowManager
        fm = FlowManager(session_id)
        if fm.has_active_flow():
            merge_form_fields(fm, message)

    # ── Update conversation flow ──
    flow_result = handle_document_upload(
        session_id=session_id,
        filename=stored_filename,
        doc_type=doc_type,
    )

    # ── Build response ──
    # Merge extraction data into the chat message if available
    extraction_summary = ""
    if extraction_result.get("status") in ("success", "partial") and extraction_result.get("summary"):
        s = extraction_result["summary"]
        if doc_type == "aadhaar":
            extraction_summary = (
                f"\n\n**Extracted from Aadhaar:**\n"
                f"- Name: {s.get('name', 'N/A')}\n"
                f"- Aadhaar No: {s.get('aadhaar_number', 'N/A')}\n"
                f"- DOB: {s.get('dob', 'N/A')}\n"
                f"- Gender: {s.get('gender', 'N/A')}\n"
                f"- State: {s.get('state', 'N/A')}\n"
                f"- Confidence: {s.get('confidence', 'N/A')}"
            )
            if extraction_result.get("validation_errors"):
                errs = "\n".join(f"  ⚠️ {e}" for e in extraction_result["validation_errors"])
                extraction_summary += f"\n\n**Validation issues:**\n{errs}"
        elif doc_type == "photograph":
            extraction_summary = (
                f"\n\n**Photo check:**\n"
                f"- Face detected: {'✅' if s.get('has_face') else '❌'}\n"
                f"- Face centered: {'✅' if s.get('face_centered') else '❌'}\n"
                f"- Plain background: {'✅' if s.get('plain_background') else '❌'}\n"
                f"- Confidence: {s.get('confidence', 'N/A')}"
            )
            if extraction_result.get("validation_errors"):
                errs = "\n".join(f"  ⚠️ {e}" for e in extraction_result["validation_errors"])
                extraction_summary += f"\n\n**Issues:**\n{errs}"
        elif doc_type == "driving_license":
            extraction_summary = (
                f"\n\n**Extracted from Driving License:**\n"
                f"- Name: {s.get('name', 'N/A')}\n"
                f"- DL No: {s.get('dl_number', 'N/A')}\n"
                f"- DOB: {s.get('dob', 'N/A')}\n"
                f"- State: {s.get('state', 'N/A')}"
            )

    chat_message = flow_result["answer"] + extraction_summary
    if agent_error:
        chat_message += f"\n\n> ⚠️ {agent_error}"

    return {
        "filename": file.filename,
        "session_id": session_id,
        "message": chat_message,
        "complete": flow_result.get("complete", False),
        # Full extraction payload for frontend use
        "extraction": extraction_result if extraction_result else None,
        "verified": extraction_result.get("verified", False),
        "validation_errors": extraction_result.get("validation_errors", []),
    }