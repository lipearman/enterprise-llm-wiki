from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    question: str
    company_code: Optional[str] = None
    session_id: Optional[str] = None
    force_rag: bool = False

class ChatSource(BaseModel):
    source_type: str
    title: str | None = None
    url: str | None = None
    score: float | None = None

class ChatResponse(BaseModel):
    answer: str
    mode: str
    sources: list[ChatSource] = []
    cached: bool = False
