from celery import Celery
from celery.schedules import crontab
from common.config import settings

celery_app = Celery(
    "ai_service",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks.calculate_metrics",
        "app.workers.tasks.intelligence",
        "app.workers.tasks.store_chat_example",
        "app.workers.tasks.daily_digest",
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
    task_default_queue="metrics",
    beat_schedule={
        "daily-digest": {
            "task": "send_daily_digest",
            "schedule": crontab(hour=settings.DAILY_DIGEST_HOUR, minute=0),
        },
    },
)
