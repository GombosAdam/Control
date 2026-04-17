from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user, require_role
from common.models.user import UserRole
from app.api.auth.schemas import LoginRequest, RegisterRequest, UserResponse, TokenResponse
from app.api.auth.service import AuthService
from common.models.user import User

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService.login(db, data)

@router.post("/register", response_model=UserResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService.register(db, data)

@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse.from_user(current_user)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await AuthService.refresh_token(current_user)

@router.post("/switch-user/{user_id}", response_model=TokenResponse)
async def switch_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Admin can switch to any user without knowing their password."""
    return await AuthService.switch_user(db, user_id)

@router.get("/me/permissions")
async def my_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current user's effective permissions as a flat list."""
    from common.dependencies import get_user_permissions
    from common.models.user import UserRole as UR

    # Admin gets all permissions
    if current_user.role == UR.admin:
        from common.models.permission import Permission
        from sqlalchemy import select as sa_select
        result = await db.execute(sa_select(Permission.resource, Permission.action))
        perms = [f"{r}:{a}" for r, a in result.all()]
    else:
        perms = sorted(await get_user_permissions(db, current_user.role))

    return {"permissions": perms}
