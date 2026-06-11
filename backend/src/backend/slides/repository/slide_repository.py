import logging
from typing import cast

from redis.asyncio import Redis
from slides.domain.repository_interface import SlideRepository

logger = logging.getLogger(__name__)


class SlideRedisRepository(SlideRepository):
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def update_current_slide(self, class_code: str, slide_number: int) -> None:
        # Current slide number for a room stored with key pattern "room:{class_code}" and field "current_slide"
        key = f"room:{class_code}"
        await self.redis.hset(key, "current_slide", str(slide_number))
        logger.debug("Updated current slide for room %s to %d", class_code, slide_number)

    async def get_room_host(self, class_code: str) -> str | None:
        # Current room's host session id stored with key pattern "room:{class_code}" and field "host_session_id"
        key = f"room:{class_code}"
        host = await self.redis.hget(key, "host_session_id")
        if isinstance(host, bytes):
            host = host.decode("utf-8")
        if not host:
            return None
        logger.debug("Retrieved host for room %s: %s", class_code, host)
        return host

    async def get_room_students(self, class_code: str) -> list[str]:
        # Current room's student's session id stored with key pattern "room:{class_code}:students"
        key = f"room:{class_code}:students"
        raw_students = await self.redis.hkeys(key)

        students = cast("list[str]", raw_students)

        logger.debug("Retrieved %d students for room %s", len(students), class_code)
        return students
