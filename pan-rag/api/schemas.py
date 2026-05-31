# api/schemas.py
from pydantic import BaseModel
from typing import Optional, Any

class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "anonymous"
    user_context: Optional[str] = None  # cross-session profile facts
    account_email: Optional[str] = None  # Supabase auth email — always available
    language: Optional[str] = None       # explicit language override from frontend ("en"|"ta"|"hi")

class Source(BaseModel):
    title: str
    url: str

class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: list[Source]
    session_id: str
    intent: Optional[str] = None
    language: Optional[str] = None
    followups: Optional[list[str]] = []
    open_upload: Optional[bool] = False
    close_form: Optional[bool] = False
    form_data: Optional[dict[str, Any]] = None
    options: Optional[dict[str, Any]] = None
    field_buttons: Optional[list[dict[str, str]]] = None  # Add field buttons for modification menu
    elapsed_ms: Optional[int] = None