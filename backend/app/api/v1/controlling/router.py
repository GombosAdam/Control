from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.api.v1.controlling.service import ControllingService

router = APIRouter()


@router.get("/plan-vs-actual")
async def plan_vs_actual(
    department_id: str | None = None,
    period: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ControllingService.plan_vs_actual(db, department_id, period)


@router.get("/budget-status")
async def budget_status(
    department_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ControllingService.budget_status(db, department_id)


@router.get("/commitment")
async def commitment(
    department_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ControllingService.commitment_report(db, department_id)


@router.get("/ebitda")
async def ebitda(
    department_id: str | None = None,
    period: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ControllingService.ebitda_report(db, department_id, period)


@router.get("/pnl")
async def pnl_waterfall(
    department_id: str | None = None,
    period: str | None = None,
    status: str | None = None,
    period_from: str | None = None,
    period_to: str | None = None,
    plan_type: str | None = None,
    scenario_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ControllingService.pnl_waterfall(db, department_id, period, status, period_from, period_to, plan_type, scenario_id)
