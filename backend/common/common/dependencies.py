import logging
import time
from typing import AsyncGenerator
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from common.database import async_session_factory
from common.models.user import User, UserRole
from common.utils.security import decode_access_token
from common.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise AuthenticationError("Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    return user

def require_role(*roles):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise AuthorizationError(f"Role {current_user.role} not authorized")
        return current_user
    return role_checker


# ── Dynamic permission system ──

# In-memory cache: {role_value: set of "resource:action" strings}
_permission_cache: dict[str, set[str]] = {}
_cache_ts: float = 0
_CACHE_TTL = 60  # seconds


async def _load_permission_cache(db: AsyncSession) -> None:
    """Load all role permissions into memory cache."""
    global _permission_cache, _cache_ts
    from common.models.permission import Permission, RolePermission

    result = await db.execute(
        select(RolePermission.role, Permission.resource, Permission.action)
        .join(Permission, RolePermission.permission_id == Permission.id)
    )
    cache: dict[str, set[str]] = {}
    for role, resource, action in result.all():
        role_val = role.value if hasattr(role, "value") else str(role)
        cache.setdefault(role_val, set()).add(f"{resource}:{action}")
    _permission_cache = cache
    _cache_ts = time.time()
    logger.debug("Permission cache loaded: %d roles", len(cache))


def invalidate_permission_cache() -> None:
    """Force cache refresh on next check."""
    global _cache_ts
    _cache_ts = 0


async def get_user_permissions(db: AsyncSession, role: str) -> set[str]:
    """Get permission strings for a role, using cache."""
    global _permission_cache, _cache_ts
    if time.time() - _cache_ts > _CACHE_TTL:
        await _load_permission_cache(db)
    role_val = role.value if hasattr(role, "value") else str(role)
    return _permission_cache.get(role_val, set())


def require_permission(resource: str, action: str):
    """FastAPI dependency: check if current user's role has a specific permission."""
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        # Admin always passes
        if current_user.role == UserRole.admin:
            return current_user

        perms = await get_user_permissions(db, current_user.role)
        if f"{resource}:{action}" not in perms:
            raise AuthorizationError(
                f"Nincs jogosultság: {resource}:{action}"
            )
        return current_user
    return permission_checker
