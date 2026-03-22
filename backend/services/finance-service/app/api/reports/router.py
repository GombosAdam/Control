from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user
from app.api.reports.service import ReportService
from common.models.user import User

router = APIRouter()

@router.get("/monthly")
async def monthly_report(
    year: int | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ReportService.monthly_report(db, year, month)

@router.get("/vat")
async def vat_report(
    year: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ReportService.vat_report(db, year)

@router.get("/suppliers")
async def supplier_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ReportService.supplier_report(db)
