from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from common.dependencies import get_db, get_current_user, require_role, invalidate_permission_cache
from app.api.admin.service import AdminService
from app.api.admin.schemas import UserCreateRequest, UserUpdateRequest, SettingUpdateRequest
from app.api.admin.gpu import router as gpu_router
from common.models.user import User, UserRole
from common.models.permission import Permission, RolePermission

router = APIRouter()
router.include_router(gpu_router)

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await AdminService.system_health(db)

@router.get("/audit")
async def audit_log(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await AdminService.get_audit_log(db, page, limit)


# ── Permission Management ──

@router.get("/permissions/matrix")
async def get_permission_matrix(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Return full permission matrix: all permissions and which roles have them."""
    # All permissions
    result = await db.execute(
        select(Permission).order_by(Permission.resource, Permission.action)
    )
    permissions = result.scalars().all()

    # All role_permissions
    result = await db.execute(select(RolePermission))
    role_perms = result.scalars().all()

    # Build granted map: {role: [permission_id, ...]}
    granted: dict[str, list[str]] = {}
    for rp in role_perms:
        role_val = rp.role.value if hasattr(rp.role, "value") else str(rp.role)
        granted.setdefault(role_val, []).append(rp.permission_id)

    roles = [r.value for r in UserRole]

    return {
        "roles": roles,
        "permissions": [
            {
                "id": p.id,
                "resource": p.resource,
                "action": p.action,
                "description": p.description,
            }
            for p in permissions
        ],
        "granted": granted,
    }


class PermissionToggle(BaseModel):
    role: str
    permission_id: str
    granted: bool


@router.put("/permissions/matrix")
async def update_permission_matrix(
    data: PermissionToggle,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Toggle a single role-permission grant."""
    import uuid

    try:
        role_enum = UserRole(data.role)
    except ValueError:
        from common.exceptions import ValidationError
        raise ValidationError(f"Invalid role: {data.role}")

    if data.granted:
        # Check if already exists
        existing = await db.execute(
            select(RolePermission).where(
                RolePermission.role == role_enum,
                RolePermission.permission_id == data.permission_id,
            )
        )
        if not existing.scalar_one_or_none():
            rp = RolePermission(
                id=str(uuid.uuid4()),
                role=role_enum,
                permission_id=data.permission_id,
            )
            db.add(rp)
    else:
        await db.execute(
            sa_delete(RolePermission).where(
                RolePermission.role == role_enum,
                RolePermission.permission_id == data.permission_id,
            )
        )

    await db.commit()
    invalidate_permission_cache()
    return {"ok": True}
