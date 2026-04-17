from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, require_role
from app.api.sync.schemas import SyncStartRequest
from app.api.sync.service import SyncService
from app.models.user import User

router = APIRouter()


@router.post("/start")
async def start_sync(
    data: SyncStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "accountant")),
):
    return await SyncService.start_sync(db, data.config_id, data.date_from, data.date_to)


@router.get("/logs")
async def list_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "accountant")),
):
    return await SyncService.list_logs(db, page, limit)


@router.get("/logs/{log_id}")
async def get_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "accountant")),
):
    return await SyncService.get_log(db, log_id)
