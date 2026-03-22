from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user
from common.models.user import User
from app.api.departments.service import DepartmentService
from app.api.departments.schemas import DepartmentCreate, DepartmentUpdate

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
