"""Celery tasks for workflow engine: timeout checks, pending message recovery, dispatcher."""

import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.tasks.workflow_tasks.check_timeouts")
def check_timeouts():
    """Check for timed-out workflow tasks and escalate them."""
    _run_async(_check_timeouts_async())


async def _check_timeouts_async():
    from datetime import datetime
    from sqlalchemy import select
    from common.database import async_session_factory
    from common.models.workflow_task import WorkflowTask, TaskStatus
    from common.workflow.engine import WorkflowEngine

    async with async_session_factory() as db:
        result = await db.execute(
            select(WorkflowTask).where(
                WorkflowTask.status == TaskStatus.pending,
                WorkflowTask.due_at != None,
                WorkflowTask.due_at < datetime.utcnow(),
            )
        )
        timed_out_tasks = result.scalars().all()

        if not timed_out_tasks:
            return

        logger.info("Found %d timed-out workflow tasks", len(timed_out_tasks))
        engine = WorkflowEngine(db)

        for task in timed_out_tasks:
            try:
                await engine.escalate_task(task.id)
                logger.info("Escalated task %s", task.id)
            except Exception:
                logger.exception("Failed to escalate task %s", task.id)

        await db.commit()


@celery_app.task(name="app.workers.tasks.workflow_tasks.check_pending_messages")
def check_pending_messages():
    """Claim stale messages from the workflow event stream."""
    _run_async(_check_pending_messages_async())


async def _check_pending_messages_async():
    from common.events import event_bus
    from common.workflow.dispatcher import WorkflowDispatcher

    claimed = await event_bus.claim_stale(
        WorkflowDispatcher.GROUP,
        "recovery-worker",
        min_idle_ms=600000,  # 10 minutes
        count=20,
    )
    if claimed:
        logger.info("Claimed %d stale messages", len(claimed))
        # Ack them after claiming — the dispatcher will pick them up
        msg_ids = [msg_id for msg_id, _ in claimed]
        await event_bus.ack(WorkflowDispatcher.GROUP, *msg_ids)


@celery_app.task(name="app.workers.tasks.workflow_tasks.run_dispatcher")
def run_dispatcher():
    """Run the workflow dispatcher loop (long-running task)."""
    _run_async(_run_dispatcher_async())


async def _run_dispatcher_async():
    from common.workflow.dispatcher import WorkflowDispatcher
    dispatcher = WorkflowDispatcher()
    await dispatcher.start()
