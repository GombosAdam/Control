from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, require_role
from app.api.config.schemas import NavConfigCreateRequest, NavConfigUpdateRequest
from app.api.config.service import NavConfigService
from app.models.user import User

router = APIRouter()


@router.get("")
async def list_configs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await NavConfigService.list_configs(db, page, limit)


@router.post("")
async def create_config(
    data: NavConfigCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await NavConfigService.create_config(db, data)


@router.put("/{config_id}")
async def update_config(
    config_id: str,
    data: NavConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await NavConfigService.update_config(db, config_id, data)


@router.delete("/{config_id}")
async def delete_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    await NavConfigService.delete_config(db, config_id)
    return {"message": "NAV config deleted"}


@router.post("/{config_id}/test")
async def test_connection(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return await NavConfigService.test_connection(db, config_id)
