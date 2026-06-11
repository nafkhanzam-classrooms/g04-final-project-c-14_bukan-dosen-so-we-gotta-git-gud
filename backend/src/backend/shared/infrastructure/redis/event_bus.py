import json
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as redis
from shared.domain.redis.event_publisher import EventPublisher
from shared.domain.redis.event_subscriber import EventSubscriber


class RedisEventBus(EventPublisher, EventSubscriber):
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        await self.redis.publish(channel, json.dumps(message))

    async def subscribe(
        self, channel: str, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        async for raw in pubsub.listen():
            if raw["type"] == "message":
                data = json.loads(raw["data"])
                await handler(data)
