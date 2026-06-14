import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from shared.domain.redis.client import RedisClient
from shared.domain.redis.event_publisher import EventPublisher
from shared.domain.redis.event_subscriber import EventSubscriber

logger = logging.getLogger(__name__)


class RedisEventBus(EventPublisher, EventSubscriber):
    def __init__(self, redis_client: RedisClient) -> None:
        self._client = redis_client
        self._redis = redis_client.pubsub()

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        await self._client.execute("PUBLISH", channel, json.dumps(message))

    async def subscribe(
        self, channel: str, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None:
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        logger.info("Subscribed to Redis channel '%s'", channel)
        try:
            async for raw in pubsub.listen():
                if raw["type"] == "message":
                    try:
                        data = json.loads(raw["data"])
                        logger.debug("Redis event received on channel '%s': %s", channel, data)
                        await handler(data)
                    except Exception:
                        logger.exception("Error processing Redis event on channel %s", channel)
        except Exception:
            logger.exception("Redis subscription to channel '%s' failed", channel)
