from typing import Any

from redis.asyncio import Redis
from shared.domain.redis.client import RedisClient


class NativeRedisClient(RedisClient):
    def __init__(self, redis: Redis):
        self._redis = redis

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        return await self._redis.execute_command(*args, **kwargs)  # type: ignore[no-untyped-call]

    async def ping(self) -> bool:
        return await self._redis.ping()

    def pubsub(self) -> Any:
        return self._redis.pubsub()
