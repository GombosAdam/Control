"""Redis pub/sub + Redis Streams EventBus for inter-service communication."""

import asyncio
import json
import logging
from typing import AsyncIterator

import redis.asyncio as aioredis

from common.config import settings

logger = logging.getLogger(__name__)

STREAM_KEY = "events:stream"
STREAM_MAXLEN = 50000


class EventBus:
    """Async Redis pub/sub + Streams event bus."""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or settings.REDIS_URL
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def publish(self, event_type: str, payload: dict) -> None:
        """Dual-write: XADD to stream + PUBLISH to pub/sub channel."""
        r = await self._get_redis()
        message = json.dumps({"event": event_type, "payload": payload})

        # Stream (persistent, at-least-once)
        try:
            await r.xadd(
                STREAM_KEY,
                {"event": event_type, "data": message},
                maxlen=STREAM_MAXLEN,
                approximate=True,
            )
        except Exception:
            logger.exception("Failed to XADD event %s to stream", event_type)

        # Pub/sub (backward compat, fire-and-forget)
        await r.publish(f"events:{event_type}", message)
        logger.info("Published event: %s", event_type)

    async def subscribe(self, *event_types: str) -> AsyncIterator[dict]:
        """Subscribe to one or more event types via pub/sub. Yields event dicts."""
        r = await self._get_redis()
        pubsub = r.pubsub()
        channels = [f"events:{et}" for et in event_types]
        await pubsub.subscribe(*channels)
        logger.info("Subscribed to events: %s", ", ".join(event_types))
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield data
                    except json.JSONDecodeError:
                        logger.warning("Invalid event JSON: %s", message["data"])
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()

    # ── Redis Streams methods ──

    async def create_consumer_group(self, group: str, start_id: str = "0") -> None:
        """Create a consumer group on the event stream."""
        r = await self._get_redis()
        try:
            await r.xgroup_create(STREAM_KEY, group, id=start_id, mkstream=True)
            logger.info("Consumer group '%s' created on %s", group, STREAM_KEY)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug("Consumer group '%s' already exists", group)
            else:
                raise

    async def read_stream(self, group: str, consumer: str,
                          count: int = 10, block: int = 5000) -> list[tuple[str, dict]]:
        """Read messages from a consumer group. Returns list of (msg_id, data)."""
        r = await self._get_redis()
        results = await r.xreadgroup(group, consumer, {STREAM_KEY: ">"}, count=count, block=block)
        messages = []
        if results:
            for _stream, entries in results:
                for msg_id, fields in entries:
                    try:
                        data = json.loads(fields.get("data", "{}"))
                        messages.append((msg_id, data))
                    except json.JSONDecodeError:
                        logger.warning("Invalid stream message: %s", msg_id)
        return messages

    async def ack(self, group: str, *msg_ids: str) -> None:
        """Acknowledge processed messages."""
        r = await self._get_redis()
        if msg_ids:
            await r.xack(STREAM_KEY, group, *msg_ids)

    async def get_pending(self, group: str, count: int = 100) -> list:
        """Get pending messages info for the group."""
        r = await self._get_redis()
        try:
            return await r.xpending_range(STREAM_KEY, group, min="-", max="+", count=count)
        except Exception:
            logger.exception("Failed to get pending messages for group %s", group)
            return []

    async def claim_stale(self, group: str, consumer: str,
                          min_idle_ms: int = 600000, count: int = 10) -> list[tuple[str, dict]]:
        """Claim stale messages from other consumers (XCLAIM)."""
        r = await self._get_redis()
        pending = await self.get_pending(group, count)
        if not pending:
            return []
        stale_ids = [p["message_id"] for p in pending if p.get("time_since_delivered", 0) >= min_idle_ms]
        if not stale_ids:
            return []
        claimed = await r.xclaim(STREAM_KEY, group, consumer, min_idle_time=min_idle_ms, message_ids=stale_ids)
        messages = []
        for msg_id, fields in claimed:
            if fields:
                try:
                    data = json.loads(fields.get("data", "{}"))
                    messages.append((msg_id, data))
                except json.JSONDecodeError:
                    pass
        return messages

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None


# Singleton instance
event_bus = EventBus()
