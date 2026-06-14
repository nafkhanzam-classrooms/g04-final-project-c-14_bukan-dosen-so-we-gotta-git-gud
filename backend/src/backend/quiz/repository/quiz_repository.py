import json
import logging
from typing import cast

from quiz.domain.repository_interface import QuizRepository
from shared.domain.redis.client import RedisClient

logger = logging.getLogger(__name__)


class QuizRedisRepository(QuizRepository):
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client

    def _quiz_key(self, class_code: str, question_id: str) -> str:
        return f"quiz:{class_code}:{question_id}"

    def _answers_key(self, class_code: str, question_id: str) -> str:
        return f"quiz:{class_code}:{question_id}:answers"

    async def start_quiz(self, class_code: str, question_id: str, options: list[str]) -> None:
        key = self._quiz_key(class_code, question_id)
        await self.redis.execute("HSET", key, "options", json.dumps(options), "is_active", "1")
        logger.debug(f"Quiz started in Redis: {key}")

    async def stop_quiz(self, class_code: str, question_id: str) -> None:
        key = self._quiz_key(class_code, question_id)
        await self.redis.execute("HSET", key, "is_active", "0")
        logger.debug(f"Quiz stopped: {key}")

    async def is_active(self, class_code: str, question_id: str) -> bool:
        key = self._quiz_key(class_code, question_id)
        active = await self.redis.execute("HGET", key, "is_active")
        result: bool = active == "1"
        return result

    async def add_answer(
        self, class_code: str, question_id: str, student_id: str, answer: str
    ) -> bool:
        # Check if the quiz is still active
        if not await self.is_active(class_code, question_id):
            logger.debug(f"Quiz {class_code}/{question_id} inactive, answer rejected")
            return False

        answers_key = self._answers_key(class_code, question_id)
        added = await self.redis.execute("HSETNX", answers_key, student_id, answer)
        if added:
            logger.debug(f"Answer added: {student_id} -> {answer}")
        else:
            logger.debug(f"Duplicate answer ignored: {student_id}")
        return bool(added)

    async def get_answers(self, class_code: str, question_id: str) -> dict[str, str]:
        answers_key = self._answers_key(class_code, question_id)
        raw = await self.redis.execute("HGETALL", answers_key)
        return cast("dict[str, str]", raw)

    async def close_quiz(self, class_code: str, question_id: str, correct_answer: str) -> None:
        key = self._quiz_key(class_code, question_id)
        answers_key = self._answers_key(class_code, question_id)
        await self.redis.execute("DEL", key, answers_key)
        logger.debug(f"Quiz data deleted: {key}")

    async def get_options(self, class_code: str, question_id: str) -> list[str] | None:
        key = self._quiz_key(class_code, question_id)
        opts = await self.redis.execute("HGET", key, "options")
        if opts:
            return cast("list[str]", json.loads(opts))
        return None

    async def delete_all_class_data(self, class_code: str) -> None:
        # Use SCAN to safely find and delete any lingering quiz keys for this class
        cursor = 0
        pattern = f"quiz:{class_code}:*"
        while True:
            cursor, keys = await self.redis.execute("SCAN", cursor, "MATCH", pattern)
            if keys:
                await self.redis.execute("DEL", *keys)
            if int(cursor) == 0:
                break
        logger.debug("All quiz Redis data deleted for room %s", class_code)
