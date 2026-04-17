from celery import Celery
from common.config import settings

celery_app = Celery(
    "finance_workflow",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks.workflow_tasks"],
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
    task_default_queue="workflow",
    beat_schedule={
        "check-workflow-timeouts": {
            "task": "app.workers.tasks.workflow_tasks.check_timeouts",
            "schedule": 300.0,  # 5 minutes
        },
        "check-pending-messages": {
            "task": "app.workers.tasks.workflow_tasks.check_pending_messages",
            "schedule": 600.0,  # 10 minutes
        },
    },
)
