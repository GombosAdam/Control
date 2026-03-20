from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.api.v1.extraction.service import ExtractionService
from app.models.user import User

router = APIRouter()

@router.get("/queue")
async def get_queue(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ExtractionService.get_queue(db, page, limit)

@router.post("/{invoice_id}/approve")
async def approve(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ExtractionService.approve(db, invoice_id, current_user.id)

@router.post("/{invoice_id}/reject")
async def reject(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ExtractionService.reject(db, invoice_id, current_user.id)

@router.get("/duplicates")
async def get_duplicates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ExtractionService.get_duplicates(db)
