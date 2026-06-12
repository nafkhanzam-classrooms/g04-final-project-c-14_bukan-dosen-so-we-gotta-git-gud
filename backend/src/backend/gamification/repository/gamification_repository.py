import logging
from typing import cast

from gamification.domain.repository_interface import GamificationRepository
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class GamificationRedisRepository(GamificationRepository):
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def _streaks_key(self, class_code: str) -> str:
        return f"gamification:{class_code}:streaks"

    def _leaderboard_key(self, class_code: str) -> str:
        return f"gamification:{class_code}:leaderboard"

    async def get_streak(self, class_code: str, student_id: str) -> int:
        val = await self._redis.hget(self._streaks_key(class_code), student_id)
        if val is None:
            return 0
        try:
            return int(val)
        except ValueError:
            logger.warning("Invalid streak value for %s/%s: %s", class_code, student_id, val)
            return 0

    async def set_streak(self, class_code: str, student_id: str, streak: int) -> None:
        await self._redis.hset(self._streaks_key(class_code), student_id, str(streak))
        logger.debug("Set streak for %s/%s to %d", class_code, student_id, streak)

    async def get_total_score(self, class_code: str, student_id: str) -> float:
        score = await self._redis.zscore(self._leaderboard_key(class_code), student_id)
        return score if score is not None else 0.0

    async def set_leaderboard_score(self, class_code: str, student_id: str, score: float) -> None:
        await self._redis.zadd(self._leaderboard_key(class_code), {student_id: score})
        logger.debug("Set leaderboard score for %s/%s to %.1f", class_code, student_id, score)

    async def get_leaderboard(self, class_code: str, top_n: int = 10) -> list[tuple[str, float]]:
        key = self._leaderboard_key(class_code)
        result = await self._redis.zrevrange(key, 0, top_n - 1, withscores=True)
        # Ensure proper typing: zrevrange returns list of tuples
        typed_result: list[tuple[str, float]] = cast("list[tuple[str, float]]", result)
        return typed_result
