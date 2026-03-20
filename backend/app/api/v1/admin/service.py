import math
import platform
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.models.settings import SystemSetting
from app.utils.security import hash_password
from app.exceptions import NotFoundError, DuplicateError, ValidationError

class AdminService:
    @staticmethod
    async def list_users(db: AsyncSession, page: int, limit: int) -> dict:
        total = await db.scalar(select(func.count(User.id))) or 0
        result = await db.execute(
            select(User).order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
        )
        users = result.scalars().all()
        return {
            "items": [
                {
                    "id": u.id, "email": u.email, "full_name": u.full_name,
                    "role": u.role.value, "is_active": u.is_active,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ],
            "total": total, "page": page, "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def create_user(db: AsyncSession, data) -> dict:
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise DuplicateError("email", data.email)
        try:
            role = UserRole(data.role)
        except ValueError:
            raise ValidationError(f"Invalid role: {data.role}")
        user = User(
            email=data.email, password_hash=hash_password(data.password),
            full_name=data.full_name, role=role,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role.value, "is_active": user.is_active,
        }

    @staticmethod
    async def update_user(db: AsyncSession, user_id: str, data) -> dict:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User", user_id)
        update_data = data.model_dump(exclude_unset=True)
        if "role" in update_data:
            update_data["role"] = UserRole(update_data["role"])
        for key, value in update_data.items():
            setattr(user, key, value)
        await db.commit()
        return {
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role.value, "is_active": user.is_active,
        }

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: str) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User", user_id)
        await db.delete(user)
        await db.commit()

    @staticmethod
    async def list_settings(db: AsyncSession) -> list:
        result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
        return [
            {"key": s.key, "value": s.value, "description": s.description}
            for s in result.scalars().all()
        ]

    @staticmethod
    async def update_setting(db: AsyncSession, key: str, value: str) -> dict:
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = SystemSetting(key=key, value=value)
            db.add(setting)
        await db.commit()
        return {"key": key, "value": value}

    @staticmethod
    async def system_health() -> dict:
        return {
            "status": "healthy",
            "python_version": platform.python_version(),
            "system": platform.system(),
            "uptime": "N/A",
        }

    @staticmethod
    async def get_audit_log(db: AsyncSession, page: int, limit: int) -> dict:
        total = await db.scalar(select(func.count(AuditLog.id))) or 0
        result = await db.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
        )
        logs = result.scalars().all()
        return {
            "items": [
                {
                    "id": log.id, "user_id": log.user_id, "action": log.action,
                    "entity_type": log.entity_type, "entity_id": log.entity_id,
                    "details": log.details, "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
            "total": total, "page": page, "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }
