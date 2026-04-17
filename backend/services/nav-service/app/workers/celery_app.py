from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "nav_service",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks.sync_inbound",
        "app.workers.tasks.submit_outbound",
        "app.workers.tasks.check_status",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Budapest",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=360,
    task_default_queue="nav",
)

celery_app.conf.beat_schedule = {
    "nav_check_pending_statuses": {
        "task": "nav_check_pending_statuses",
        "schedule": 300.0,  # 5 minutes
    },
    "nav_sync_inbound_auto": {
        "task": "nav_sync_inbound_auto",
        "schedule": crontab(minute=0, hour="*/4"),  # every 4 hours
    },
}
