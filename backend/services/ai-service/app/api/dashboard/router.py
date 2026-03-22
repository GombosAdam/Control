from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user
from common.models.user import User

router = APIRouter()


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
    """Trigger CFO metrics calculation."""
    from app.workers.celery_app import celery_app
    if period is None:
        period = date.today().strftime("%Y-%m")
    result = celery_app.send_task("calculate_cfo_metrics", args=[period])
    return {"status": "calculating", "period": period, "task_id": result.id}
