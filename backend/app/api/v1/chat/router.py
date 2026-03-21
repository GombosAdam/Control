from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.api.v1.chat.schemas import ChatRequest, ChatResponse
from app.api.v1.chat.service import ChatService
from app.models.user import User

router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ChatService.chat(db, request.question, current_user.id)
