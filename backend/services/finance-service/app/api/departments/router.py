from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user
from common.models.user import User
from app.api.departments.service import DepartmentService
from app.api.departments.schemas import DepartmentCreate, DepartmentUpdate, BudgetMasterSet

router = APIRouter()


@router.get("/")
async def list_departments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DepartmentService.list_all(db)


@router.post("/")
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DepartmentService.create(db, data.model_dump())


@router.get("/{dept_id}")
async def get_department(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DepartmentService.get(db, dept_id)


@router.put("/{dept_id}")
async def update_department(
    dept_id: str,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DepartmentService.update(db, dept_id, data.model_dump(exclude_unset=True))


@router.delete("/{dept_id}")
async def delete_department(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DepartmentService.delete(db, dept_id)


@router.get("/{dept_id}/budget-master")
async def get_budget_master(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DepartmentService.get_budget_master(db, dept_id)


@router.put("/{dept_id}/budget-master")
async def set_budget_master(
    dept_id: str,
    data: BudgetMasterSet,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DepartmentService.set_budget_master(
        db, dept_id, [e.model_dump() for e in data.entries]
    )
