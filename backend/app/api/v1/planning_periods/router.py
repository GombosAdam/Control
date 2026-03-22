from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user, require_role
from app.models.user import User, UserRole
from app.api.v1.planning_periods.service import PlanningPeriodService
from app.api.v1.planning_periods.schemas import PlanningPeriodCreate

router = APIRouter()


@router.get("")
async def list_planning_periods(
    scenario_id: str | None = None,
    plan_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PlanningPeriodService.list_periods(db, scenario_id, plan_type)


@router.post("")
async def create_planning_period(
    data: PlanningPeriodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo)),
):
    return await PlanningPeriodService.create_period(db, data.model_dump(), current_user.id)


@router.get("/{period_id}")
async def get_planning_period(
    period_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PlanningPeriodService.get_period(db, period_id)


@router.delete("/{period_id}")
async def delete_planning_period(
    period_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo)),
):
    return await PlanningPeriodService.delete_period(db, period_id, current_user.id)
