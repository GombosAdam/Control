from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user
from app.api.dashboard.service import DashboardService
from common.models.user import User

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

@router.get("/cfo-kpis")
async def get_cfo_kpis(
    scenario_id: str | None = None,
    plan_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DashboardService.get_cfo_kpis(db, scenario_id, plan_type)

@router.get("/cfo-trends")
async def get_cfo_trends(
    scenario_id: str | None = None,
    plan_type: str | None = None,
    periods: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DashboardService.get_trend_data(db, scenario_id, plan_type, periods)

@router.get("/cfo-departments")
async def get_cfo_departments(
    period: str | None = None,
    scenario_id: str | None = None,
    plan_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DashboardService.get_department_comparison(db, period, scenario_id, plan_type)

@router.get("/cfo-alerts")
async def get_cfo_alerts(
    threshold_pct: float = 10,
    scenario_id: str | None = None,
    plan_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DashboardService.get_budget_alerts(db, threshold_pct, scenario_id, plan_type)
