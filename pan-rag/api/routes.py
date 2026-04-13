# api/routes.py
from fastapi import APIRouter, HTTPException
from api.schemas import QuestionRequest, AnswerResponse
from generation.chain import RAGChain
import traceback
from fastapi import UploadFile, File, Form
from agent.receptionist import handle_document_upload
import shutil
import httpx
from pathlib import Path

router = APIRouter()

# URL of the document upload agent (Flask, port 5001)
DOC_AGENT_URL = "http://localhost:5001/api/upload"

_chain: RAGChain | None = None

def get_chain() -> RAGChain:
    global _chain
    if _chain is None:
        _chain = RAGChain()
    return _chain


@router.post("/ask", response_model=AnswerResponse)
def ask(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        result = get_chain().run(
            question=request.question,
            session_id=request.session_id,
            user_id=request.user_id
        )
        print(f"DEBUG result: {result}")
        return AnswerResponse(**result)
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
):
    # Save file locally for flow tracking
    dest = UPLOAD_DIR / session_id
    dest.mkdir(parents=True, exist_ok=True)
    file_path = dest / file.filename

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

    # ── Update conversation flow ──
    flow_result = handle_document_upload(
        session_id=session_id,
        filename=file.filename,
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