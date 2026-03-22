import math
import platform
from datetime import datetime
import httpx
import redis as sync_redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from common.config import settings
from common.models.user import User, UserRole
from common.models.invoice import Invoice
from common.models.budget_line import BudgetLine
from common.models.purchase_order import PurchaseOrder
from common.models.accounting_entry import AccountingEntry
from common.models.audit import AuditLog
from common.models.settings import SystemSetting
from common.utils.security import hash_password
from common.exceptions import NotFoundError, DuplicateError, ValidationError

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
    async def system_health(db: AsyncSession) -> dict:
        now = datetime.utcnow()

        # ── Database stats ──
        db_stats = {}
        try:
            db_size = await db.scalar(text("SELECT pg_database_size(current_database())"))
            db_stats["size_mb"] = round((db_size or 0) / 1024 / 1024, 1)
            db_stats["active_connections"] = await db.scalar(text(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )) or 0
            db_stats["total_connections"] = await db.scalar(text(
                "SELECT count(*) FROM pg_stat_activity"
            )) or 0

            # Table row counts
            tables = {}
            for tbl in ["invoices", "users", "partners", "budget_lines", "purchase_orders",
                         "accounting_entries", "cfo_metrics", "audit_logs", "departments", "scenarios"]:
                try:
                    cnt = await db.scalar(text(f"SELECT count(*) FROM {tbl}"))
                    tables[tbl] = cnt or 0
                except Exception:
                    tables[tbl] = -1
            db_stats["tables"] = tables
            db_stats["status"] = "healthy"
        except Exception as e:
            db_stats["status"] = "error"
            db_stats["error"] = str(e)[:200]

        # ── Redis stats ──
        redis_stats = {}
        try:
            r = sync_redis.from_url(settings.REDIS_URL)
            info = r.info()
            redis_stats["status"] = "healthy"
            redis_stats["used_memory_mb"] = round(info.get("used_memory", 0) / 1024 / 1024, 1)
            redis_stats["connected_clients"] = info.get("connected_clients", 0)
            redis_stats["uptime_seconds"] = info.get("uptime_in_seconds", 0)
            redis_stats["total_commands"] = info.get("total_commands_processed", 0)
            redis_stats["pubsub_channels"] = info.get("pubsub_channels", 0)

            # Celery queue lengths
            queues = {}
            for q in ["invoices", "metrics", "celery"]:
                queues[q] = r.llen(q)
            redis_stats["celery_queues"] = queues
            r.close()
        except Exception as e:
            redis_stats["status"] = "error"
            redis_stats["error"] = str(e)[:200]

        # ── Service health checks ──
        services_status = {}
        for name, port in [("ai-service", 8001), ("invoice-pipeline", 8002), ("finance-service", 8003)]:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(f"http://{name}:{port}/")
                    data = resp.json()
                    services_status[name] = {
                        "status": "healthy",
                        "response_ms": int(resp.elapsed.total_seconds() * 1000),
                        "version": data.get("version", "?"),
                    }
            except Exception:
                services_status[name] = {"status": "unreachable"}

        # ── Invoice pipeline stats ──
        pipeline_stats = {}
        try:
            for status_val in ["uploaded", "ocr_processing", "extracting", "pending_review",
                               "in_approval", "awaiting_match", "matched", "posted", "rejected", "error"]:
                cnt = await db.scalar(text(
                    f"SELECT count(*) FROM invoices WHERE status = :s"
                ), {"s": status_val})
                pipeline_stats[status_val] = cnt or 0
        except Exception:
            pass

        return {
            "status": "healthy",
            "timestamp": now.isoformat(),
            "python_version": platform.python_version(),
            "system": platform.system(),
            "database": db_stats,
            "redis": redis_stats,
            "services": services_status,
            "invoice_pipeline": pipeline_stats,
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
