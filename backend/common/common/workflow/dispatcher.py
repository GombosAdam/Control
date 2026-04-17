"""Workflow dispatcher: reads Redis Stream and routes events to the engine."""

import asyncio
import logging

from sqlalchemy import select

from common.events import event_bus
from common.database import async_session_factory
from common.models.workflow_definition import WorkflowDefinition
from common.workflow.engine import WorkflowEngine

logger = logging.getLogger(__name__)


class WorkflowDispatcher:
    """Consumes events from Redis Streams and triggers workflow actions."""

    GROUP = "workflow-engine"
    CONSUMER = "dispatcher-1"

    def __init__(self):
        self._running = False

    async def start(self) -> None:
        """Start the dispatcher loop."""
        await event_bus.create_consumer_group(self.GROUP)
        self._running = True
        logger.info("WorkflowDispatcher started (group=%s, consumer=%s)", self.GROUP, self.CONSUMER)

        while self._running:
            try:
                messages = await event_bus.read_stream(
                    self.GROUP, self.CONSUMER, count=10, block=5000
                )
                for msg_id, data in messages:
                    try:
                        await self._handle_message(data)
                    except Exception:
                        logger.exception("Error handling message %s", msg_id)
                    finally:
                        await event_bus.ack(self.GROUP, msg_id)

            except asyncio.CancelledError:
                logger.info("WorkflowDispatcher cancelled")
                break
            except Exception:
                logger.exception("Dispatcher loop error, retrying in 5s")
                await asyncio.sleep(5)

    def stop(self) -> None:
        self._running = False

    async def _handle_message(self, data: dict) -> None:
        """Route an event to the appropriate workflow action."""
        event_type = data.get("event", "")
        payload = data.get("payload", {})

        if not event_type:
            return

        # Check if any workflow definition is triggered by this event
        async with async_session_factory() as db:
            result = await db.execute(
                select(WorkflowDefinition).where(
                    WorkflowDefinition.trigger_event == event_type,
                    WorkflowDefinition.is_active == True,
                )
            )
            wf_defs = result.scalars().all()

            if not wf_defs:
                return

            engine = WorkflowEngine(db)

            for wf_def in wf_defs:
                entity_id = payload.get(f"{wf_def.entity_type}_id", "")
                if not entity_id:
                    # Try common patterns
                    entity_id = payload.get("entity_id", payload.get("id", ""))

                if not entity_id:
                    logger.warning("No entity_id found in payload for event %s", event_type)
                    continue

                try:
                    await engine.start_workflow(
                        workflow_code=wf_def.code,
                        entity_type=wf_def.entity_type,
                        entity_id=entity_id,
                        context=payload,
                        initiated_by=payload.get("created_by", payload.get("initiated_by", "")),
                    )
                    await db.commit()
                    logger.info("Workflow '%s' started for %s:%s",
                                wf_def.code, wf_def.entity_type, entity_id)
                except Exception:
                    await db.rollback()
                    logger.exception("Failed to start workflow '%s' for event %s",
                                     wf_def.code, event_type)
