# api/schemas.py
from pydantic import BaseModel
from typing import Optional

class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "anonymous"

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