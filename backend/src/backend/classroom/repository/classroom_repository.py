import logging
from typing import cast

from classroom.domain.classroom import StudentState
from classroom.domain.repository_interface import ClassroomRepository
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class ClassroomRedisRepository(ClassroomRepository):
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def save_room(self, class_code: str, host_session_id: str, ttl: int) -> None:
        logger.debug("Saving room %s with host %s", class_code, host_session_id)
        key = f"room:{class_code}"
        students_key = f"room:{class_code}:students"
        await self.redis.hset(
            key,
            mapping={"host_session_id": host_session_id, "current_slide": "1", "total_slides": "0"},
        )
        await self.redis.expire(key, ttl)
        await self.redis.expire(students_key, ttl)
        logger.info("Room %s created with TTL %d seconds", class_code, ttl)

    async def get_room(self, class_code: str) -> dict[str, str] | None:
        data = await self.redis.hgetall(f"room:{class_code}")
        logger.debug("Fetched room %s data: %s", class_code, "exists" if data else "missing")
        if not data:
            return None
        return cast("dict[str, str]", data)

    async def update_total_slides(self, class_code: str, total: int) -> None:
        logger.debug("Updating total_slides for room %s to %d", class_code, total)
        key = f"room:{class_code}"
        await self.redis.hset(key, "total_slides", str(total))

    async def add_student(self, class_code: str, session_id: str, student: StudentState) -> None:
        logger.debug(
            "Adding student %s (session %s) to room %s", student.name, session_id, class_code
        )
        key = f"room:{class_code}:students"
        await self.redis.hset(key, session_id, student.model_dump_json())

    async def get_all_students(self, class_code: str) -> dict[str, str]:
        key = f"room:{class_code}:students"
        data = await self.redis.hgetall(key)
        logger.debug("Fetched %d students for room %s", len(data), class_code)
        return cast("dict[str, str]", data)

    async def remove_student(self, class_code: str, session_id: str) -> None:
        key = f"room:{class_code}:students"
        removed = await self.redis.hdel(key, session_id)
        if removed:
            logger.info("Student %s removed from Redis for class %s", session_id, class_code)
        else:
            logger.debug(
                "Student %s was not in Redis for class %s (already removed?)",
                session_id,
                class_code,
            )

    async def refresh_room_ttl(self, class_code: str, ttl: int = 1800) -> None:
        key = f"room:{class_code}"
        students_key = f"room:{class_code}:students"
        await self.redis.expire(key, ttl)
        await self.redis.expire(students_key, ttl)
        logger.debug("TTL refreshed for room %s (%d seconds)", class_code, ttl)

    async def delete_room_data(self, class_code: str) -> None:
        await self.redis.delete(f"room:{class_code}", f"room:{class_code}:students")
        logger.debug("Classroom Redis data deleted for room %s", class_code)
