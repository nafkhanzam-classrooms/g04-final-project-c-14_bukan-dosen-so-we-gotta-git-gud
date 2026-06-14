import asyncio
from typing import Any

from redis.asyncio import Redis
from shared.domain.redis.client import RedisClient


class RateLimitedRedis(RedisClient):
    def __init__(self, redis: Redis, max_concurrency: int = 200):
        self._redis = redis
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        async with self._semaphore:
            return await self._redis.execute_command(*args, **kwargs)  # type: ignore[no-untyped-call]

    async def ping(self) -> bool:
        return await self._redis.ping()

    def pubsub(self) -> Any:
        return self._redis.pubsub()
