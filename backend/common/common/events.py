"""Redis pub/sub EventBus for inter-service communication."""

import asyncio
import json
import logging
from typing import AsyncIterator

import redis.asyncio as aioredis

from common.config import settings

logger = logging.getLogger(__name__)


class EventBus:
    """Async Redis pub/sub event bus."""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or settings.REDIS_URL
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def publish(self, event_type: str, payload: dict) -> None:
        """Publish an event to the Redis channel."""
        r = await self._get_redis()
        message = json.dumps({"event": event_type, "payload": payload})
        await r.publish(f"events:{event_type}", message)
        logger.info("Published event: %s", event_type)

    async def subscribe(self, *event_types: str) -> AsyncIterator[dict]:
        """Subscribe to one or more event types. Yields event dicts."""
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

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None


# Singleton instance
event_bus = EventBus()
