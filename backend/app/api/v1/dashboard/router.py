from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
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


@router.get("/cfo-metrics")
async def get_cfo_metrics(
    period: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all pre-calculated CFO metrics for a period."""
    if period is None:
        period = date.today().strftime("%Y-%m")
    result = await db.execute(
        text("SELECT metric_key, value, calculated_at FROM cfo_metrics WHERE period = :p ORDER BY metric_key"),
        {"p": period},
    )
    rows = result.fetchall()
    return {
        "period": period,
        "metrics": {row[0]: row[1] for row in rows},
        "calculated_at": rows[0][2].isoformat() if rows else None,
        "count": len(rows),
    }


@router.post("/cfo-metrics/calculate")
async def calculate_cfo_metrics(
    period: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger CFO metrics calculation (sync, for admin use)."""
    from app.workers.tasks.calculate_metrics import calculate_cfo_metrics as calc_task
    if period is None:
        period = date.today().strftime("%Y-%m")
    result = calc_task.delay(period)
    return {"status": "calculating", "period": period, "task_id": result.id}
