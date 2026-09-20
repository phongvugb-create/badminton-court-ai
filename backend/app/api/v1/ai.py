# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from app.schemas.all_schemas import AIChatRequest, AIChatResponse
from app.ai.gemini_bot import ask_gemini_badminton

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

@router.post("/chat", response_model=AIChatResponse)
async def chat_with_ai(req: AIChatRequest):
    reply = await ask_gemini_badminton(req.message, req.context)
    return AIChatResponse(reply=reply)
