from fastapi import APIRouter, Request
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_service
from app.services.audit_service import audit_log

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    result = await chat_service.answer(
        req.question, req.company_code, req.force_rag, req.session_id
    )
    no_data = result.answer.startswith("ขณะนี้ยังไม่มีข้อมูล")
    audit_log(
        "chat.question",
        request=request,
        company_code=req.company_code,
        detail={
            "question":     req.question[:80],
            "force_rag":    req.force_rag,
            "source_count": len(result.source_refs or []),
            "answered":     not no_data,
        },
    )
    return result
