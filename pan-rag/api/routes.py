# api/routes.py
from fastapi import APIRouter, HTTPException
from api.schemas import QuestionRequest, AnswerResponse
from generation.chain import RAGChain
import traceback
# Add to api/routes.py
from fastapi import UploadFile, File, Form
from agent.receptionist import handle_document_upload
import shutil
from pathlib import Path

router = APIRouter()

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
        print(f"DEBUG result: {result}")       # ← see what chain.run() returns
        return AnswerResponse(**result)
    except Exception as e:
        print(f"ERROR: {e}")                   # ← see the error message
        traceback.print_exc()                  # ← see full traceback in server terminal
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health():
    return {"status": "ok"}

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_document(
    session_id : str      = Form(...),
    doc_type   : str      = Form(...),
    file       : UploadFile = File(...),
):
    # Save file
    dest = UPLOAD_DIR / session_id
    dest.mkdir(parents=True, exist_ok=True)
    file_path = dest / file.filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Tell the agent about the upload
    result = handle_document_upload(
        session_id=session_id,
        filename=file.filename,
        doc_type=doc_type,
    )

    return {
        "filename"  : file.filename,
        "session_id": session_id,
        "message"   : result["answer"],
        "complete"  : result.get("complete", False),
    }