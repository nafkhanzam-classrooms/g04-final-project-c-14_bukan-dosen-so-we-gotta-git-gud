import logging

from gamification.domain.repository_interface import GamificationRepository
from shared.domain.redis.client import RedisClient

logger = logging.getLogger(__name__)


class GamificationRedisRepository(GamificationRepository):
    def __init__(self, redis_client: RedisClient) -> None:
        self._redis = redis_client

    def _streaks_key(self, class_code: str) -> str:
        return f"gamification:{class_code}:streaks"

    def _leaderboard_key(self, class_code: str) -> str:
        return f"gamification:{class_code}:leaderboard"

    async def get_streak(self, class_code: str, student_id: str) -> int:
        val = await self._redis.execute("HGET", self._streaks_key(class_code), student_id)
        if val is None:
            return 0
        try:
            return int(val)
        except ValueError:
            logger.warning("Invalid streak value for %s/%s: %s", class_code, student_id, val)
            return 0

    async def set_streak(self, class_code: str, student_id: str, streak: int) -> None:
        await self._redis.execute("HSET", self._streaks_key(class_code), student_id, str(streak))
        logger.debug("Set streak for %s/%s to %d", class_code, student_id, streak)

    async def get_total_score(self, class_code: str, student_id: str) -> float:
        score = await self._redis.execute("ZSCORE", self._leaderboard_key(class_code), student_id)
        return float(score) if score is not None else 0.0

    async def set_leaderboard_score(self, class_code: str, student_id: str, score: float) -> None:
        await self._redis.execute("ZADD", self._leaderboard_key(class_code), score, student_id)
        logger.debug("Set leaderboard score for %s/%s to %.1f", class_code, student_id, score)

    async def get_leaderboard(self, class_code: str, top_n: int = 10) -> list[tuple[str, float]]:
        key = self._leaderboard_key(class_code)
        # ZREVRANGE dengan WITHSCORES
        result = await self._redis.execute("ZREVRANGE", key, 0, top_n - 1, "WITHSCORES")
        # result comes as list alternating member, score: [member1, score1, member2, score2, ...]
        if not result:
            return []
        # Convert to list of tuples
        it = iter(result)
        return list(zip(it, map(float, it), strict=False))

    async def delete_gamification_data(self, class_code: str) -> None:
        await self._redis.execute(
            "DEL", self._streaks_key(class_code), self._leaderboard_key(class_code)
        )
        logger.debug("Gamification Redis data deleted for room %s", class_code)
