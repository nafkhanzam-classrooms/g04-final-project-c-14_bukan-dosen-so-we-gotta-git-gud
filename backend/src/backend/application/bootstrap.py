import asyncio
import logging

from classroom.application.classroom_service import ClassroomService
from classroom.interface.classroom_handler import ClassroomHandler
from classroom.repository.classroom_repository import ClassroomRedisRepository
from redis.asyncio import Redis
from shared.application.room.broadcast import RoomBroadcastService
from shared.infrastructure.redis.event_bus import RedisEventBus
from shared.infrastructure.room.in_memory_registry import InMemoryRoomRegistry
from shared.infrastructure.websocket.manager import WSConnectionManager
from shared.infrastructure.websocket.router import WSEventRouter
from slides.application.slide_service import SlideService
from slides.interface.slide_handler import SlideHandler
from slides.repository.slide_repository import SlideRedisRepository

from application.event_handlers import RoomEventHandler


class Application:
    def __init__(self) -> None:
        # Low‑level infrastructure
        self.redis = Redis(host="redis", port=6379, db=0, decode_responses=True)
        self.ws_manager = WSConnectionManager()
        self.room_registry = InMemoryRoomRegistry()
        self.event_bus = RedisEventBus(self.redis)

        # Repositories
        classroom_repo = ClassroomRedisRepository(self.redis)
        slide_repo = SlideRedisRepository(self.redis)

        # Services
        self.classroom_service = ClassroomService(classroom_repo)
        self.broadcast_service = RoomBroadcastService(self.room_registry, self.ws_manager)
        self.slide_service = SlideService(slide_repo)

        # Handlers
        self.classroom_handler = ClassroomHandler(
            service=self.classroom_service,
            ws_manager=self.ws_manager,
            room_registry=self.room_registry,
        )

        self.slide_handler = SlideHandler(
            service=self.slide_service,
            broadcast_service=self.broadcast_service,
            ws_manager=self.ws_manager,
        )

        # Event handler and router
        self.event_handler = RoomEventHandler(self.classroom_service, self.broadcast_service)
        self.ws_router = WSEventRouter()
        self.ws_router.register("classroom", self.classroom_handler)
        self.ws_router.register("slides", self.slide_handler)

    async def start_background_tasks(self) -> None:
        try:
            await self.redis.ping()
            logging.info("Redis connection established successfully.")
        except Exception as e:
            logging.error(f"Redis connection failed: {e}")
            raise

        asyncio.create_task(self.event_bus.subscribe("room_events", self.event_handler))
