import math
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.nav_config import NavConfig
from app.models.nav_sync_log import NavSyncLog, NavSyncDirection, NavSyncStatus
from app.exceptions import NotFoundError


class SyncService:
    @staticmethod
    async def start_sync(db: AsyncSession, config_id: str, date_from: str, date_to: str) -> dict:
        result = await db.execute(select(NavConfig).where(NavConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise NotFoundError("NavConfig", config_id)

        sync_log = NavSyncLog(
            nav_config_id=config_id,
            direction=NavSyncDirection.inbound,
            date_from=datetime.strptime(date_from, "%Y-%m-%d").date(),
            date_to=datetime.strptime(date_to, "%Y-%m-%d").date(),
            status=NavSyncStatus.running,
        )
        db.add(sync_log)
        await db.commit()
        await db.refresh(sync_log)

        # Dispatch Celery task
        from app.workers.celery_app import celery_app
        celery_app.send_task(
            "nav_sync_inbound",
            args=[sync_log.id, config_id, date_from, date_to],
            queue="nav",
        )

        return {
            "id": sync_log.id,
            "status": sync_log.status.value,
            "message": "Sync started",
        }

    @staticmethod
    async def list_logs(db: AsyncSession, page: int, limit: int) -> dict:
        count_query = select(func.count(NavSyncLog.id))
        total = await db.scalar(count_query) or 0

        result = await db.execute(
            select(NavSyncLog).order_by(NavSyncLog.created_at.desc())
            .offset((page - 1) * limit).limit(limit)
        )
        logs = result.scalars().all()

        return {
            "items": [
                {
                    "id": log.id,
                    "nav_config_id": log.nav_config_id,
                    "direction": log.direction.value,
                    "date_from": log.date_from.isoformat() if log.date_from else None,
                    "date_to": log.date_to.isoformat() if log.date_to else None,
                    "invoices_found": log.invoices_found,
                    "invoices_created": log.invoices_created,
                    "invoices_skipped": log.invoices_skipped,
                    "status": log.status.value,
                    "error_message": log.error_message,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
            "total": total, "page": page, "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def get_log(db: AsyncSession, log_id: str) -> dict:
        result = await db.execute(select(NavSyncLog).where(NavSyncLog.id == log_id))
        log = result.scalar_one_or_none()
        if not log:
            raise NotFoundError("NavSyncLog", log_id)
        return {
            "id": log.id,
            "nav_config_id": log.nav_config_id,
            "direction": log.direction.value,
            "date_from": log.date_from.isoformat() if log.date_from else None,
            "date_to": log.date_to.isoformat() if log.date_to else None,
            "invoices_found": log.invoices_found,
            "invoices_created": log.invoices_created,
            "invoices_skipped": log.invoices_skipped,
            "status": log.status.value,
            "error_message": log.error_message,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "created_at": log.created_at.isoformat(),
        }
