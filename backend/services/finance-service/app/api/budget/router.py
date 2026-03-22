from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user, require_role
from common.models.user import User, UserRole
from app.api.budget.service import BudgetService
from app.api.budget.schemas import BudgetLineCreate, BudgetLineUpdate, BulkLineIds, BulkAdjust, CopyPeriod, CreateYearPlan, CopyToForecast, AddComment

router = APIRouter()


@router.get("/lines")
async def list_budget_lines(
    department_id: str | None = None,
    period: str | None = None,
    status: str | None = None,
    plan_type: str | None = None,
    scenario_id: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BudgetService.list_lines(db, department_id, period, status, plan_type, scenario_id, page, limit)


@router.post("/lines")
async def create_budget_line(
    data: BudgetLineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo, UserRole.accountant)),
):
    return await BudgetService.create_line(db, data.model_dump(), current_user.id)


@router.put("/lines/{line_id}")
async def update_budget_line(
    line_id: str,
    data: BudgetLineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo, UserRole.accountant)),
):
    return await BudgetService.update_line(db, line_id, data.model_dump(exclude_unset=True), current_user.id)


@router.post("/lines/{line_id}/approve")
async def approve_budget_line(
    line_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo, UserRole.department_head)),
):
    return await BudgetService.approve(db, line_id, current_user.id)


@router.post("/lines/{line_id}/lock")
async def lock_budget_line(
    line_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo)),
):
    return await BudgetService.lock(db, line_id, current_user.id)


@router.get("/lines/{line_id}/audit")
async def get_line_audit(
    line_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BudgetService.get_line_audit(db, line_id, page, limit)


@router.get("/lines/{line_id}/comments")
async def list_line_comments(
    line_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BudgetService.list_comments(db, line_id, page, limit)


@router.post("/lines/{line_id}/comments")
async def add_line_comment(
    line_id: str,
    data: AddComment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BudgetService.add_comment(db, line_id, data.text, current_user.id)


@router.post("/lines/bulk-approve")
async def bulk_approve(
    data: BulkLineIds,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo, UserRole.department_head)),
):
    return await BudgetService.bulk_approve(db, data.line_ids, current_user.id)


@router.post("/lines/bulk-lock")
async def bulk_lock(
    data: BulkLineIds,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo)),
):
    return await BudgetService.bulk_lock(db, data.line_ids, current_user.id)


@router.post("/lines/copy-period")
async def copy_period(
    data: CopyPeriod,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BudgetService.copy_period(db, data.source_period, data.target_period, data.department_id, current_user.id)


@router.post("/lines/bulk-adjust")
async def bulk_adjust(
    data: BulkAdjust,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BudgetService.bulk_adjust(db, data.line_ids, data.percentage, current_user.id)


@router.post("/lines/validate-approve")
async def validate_approve(
    data: BulkLineIds,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BudgetService.validate_approve(db, data.line_ids)


@router.post("/lines/create-forecast")
async def create_forecast(
    data: CopyToForecast,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo, UserRole.accountant)),
):
    return await BudgetService.create_forecast_from_budget(
        db, data.source_period, data.department_id, data.adjustment_pct, data.scenario_id, current_user.id
    )


@router.post("/create-year-plan")
async def create_year_plan(
    data: CreateYearPlan,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo)),
):
    return await BudgetService.create_year_plan(
        db, data.year, data.source_year, data.adjustment_pct, data.department_id, data.plan_type, data.scenario_id, current_user.id
    )


@router.get("/periods")
async def get_periods(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BudgetService.get_periods(db)


@router.get("/availability/{dept_id}")
async def get_budget_availability(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BudgetService.get_availability(db, dept_id)
