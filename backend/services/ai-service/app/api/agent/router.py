from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from common.dependencies import get_db, get_current_user
from common.models.user import User
from .schemas import AgentRequest, AgentResponse
from .service import AgentService

router = APIRouter()


def _extract_token(authorization: str = Header(None)) -> str:
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1]
    return ""


@router.post("/ask", response_model=AgentResponse)
async def agent_ask(
    request: AgentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(_extract_token),
):
    return await AgentService.ask(db, request.question, current_user.id, token)
