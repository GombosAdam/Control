from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user, require_role
from app.api.v1.admin.service import AdminService
from app.api.v1.admin.schemas import UserCreateRequest, UserUpdateRequest, SettingUpdateRequest
from app.api.v1.admin.gpu import router as gpu_router
from app.models.user import User, UserRole

router = APIRouter()
router.include_router(gpu_router)

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await AdminService.list_users(db, page, limit)

@router.post("/users")
async def create_user(
    data: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await AdminService.create_user(db, data)

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await AdminService.update_user(db, user_id, data)

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    await AdminService.delete_user(db, user_id)
    return {"message": "User deleted"}

@router.get("/settings")
async def list_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await AdminService.list_settings(db)

@router.put("/settings/{key}")
async def update_setting(
    key: str,
    data: SettingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await AdminService.update_setting(db, key, data.value)

@router.get("/system")
async def system_health(
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await AdminService.system_health()

@router.get("/audit")
async def audit_log(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await AdminService.get_audit_log(db, page, limit)
