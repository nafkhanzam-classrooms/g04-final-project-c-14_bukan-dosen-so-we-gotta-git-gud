from typing import cast

from classroom.domain.classroom import StudentState
from classroom.domain.repository_interface import ClassroomRepository
from redis.asyncio import Redis


class ClassroomRedisRepository(ClassroomRepository):
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def save_room(self, class_code: str, host_session_id: str) -> None:
        key = f"room:{class_code}"
        await self.redis.hset(
            key,
            mapping={"host_session_id": host_session_id, "current_slide": "1", "total_slides": "0"},
        )

    async def get_room(self, class_code: str) -> dict[str, str] | None:
        data = await self.redis.hgetall(f"room:{class_code}")
        if not data:
            return None
        return cast("dict[str, str]", data)

    async def update_total_slides(self, class_code: str, total: int) -> None:
        key = f"room:{class_code}"
        await self.redis.hset(key, "total_slides", str(total))

    async def add_student(self, class_code: str, session_id: str, student: StudentState) -> None:
        key = f"room:{class_code}:students"
        await self.redis.hset(key, session_id, student.model_dump_json())

    async def get_all_students(self, class_code: str) -> dict[str, str]:
        key = f"room:{class_code}:students"
        data = await self.redis.hgetall(key)
        return cast("dict[str, str]", data)
