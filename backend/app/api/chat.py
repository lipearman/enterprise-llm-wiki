from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    return await chat_service.answer(req.question, req.company_code, req.force_rag, req.session_id)
