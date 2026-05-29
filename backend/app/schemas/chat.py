from pydantic import BaseModel, field_validator
from typing import Optional


class ChatRequest(BaseModel):
    question: str
    company_code: Optional[str] = None
    session_id: Optional[str] = None
    force_rag: bool = False

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        if len(v) > 2000:
            raise ValueError(f"Question too long ({len(v)} chars). Maximum: 2000 characters")
        return v


class ChatSource(BaseModel):
    source_type: str
    title: str | None = None
    url: str | None = None
    score: float | None = None


class SourceRef(BaseModel):
    """Deduplicated source reference for frontend display."""
    label: str          # human-readable label, e.g. "About Us - Company Profile"
    url: str | None = None


class ChatResponse(BaseModel):
    answer: str
    mode: str
    sources: list[ChatSource] = []
    source_refs: list[SourceRef] = []   # clean display refs (max 5, deduped)
    cached: bool = False
