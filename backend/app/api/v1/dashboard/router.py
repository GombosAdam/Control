from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.api.v1.dashboard.service import DashboardService
from app.models.user import User

router = APIRouter()

@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DashboardService.get_stats(db)

@router.get("/recent")
async def get_recent_invoices(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DashboardService.get_recent_invoices(db, limit)

@router.get("/processing-status")
async def get_processing_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DashboardService.get_processing_status(db)
