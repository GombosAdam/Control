from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.api.v1.positions.service import PositionService
from app.api.v1.positions.schemas import PositionCreate, PositionUpdate

router = APIRouter()


@router.get("/")
async def list_positions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PositionService.list_all(db)


@router.post("/")
async def create_position(
    data: PositionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PositionService.create(db, data.model_dump())


@router.get("/{position_id}")
async def get_position(
    position_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PositionService.get(db, position_id)


@router.put("/{position_id}")
async def update_position(
    position_id: str,
    data: PositionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PositionService.update(db, position_id, data.model_dump(exclude_unset=True))


@router.delete("/{position_id}")
async def delete_position(
    position_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PositionService.delete(db, position_id)
