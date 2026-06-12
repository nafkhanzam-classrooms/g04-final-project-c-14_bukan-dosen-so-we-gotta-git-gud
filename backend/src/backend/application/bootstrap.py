import asyncio
import logging

from classroom.application.classroom_service import ClassroomService
from classroom.interface.classroom_handler import ClassroomHandler
from classroom.repository.classroom_repository import ClassroomRedisRepository
from gamification.application.gamification_service import GamificationService
from gamification.infrastructure.classroom_student_provider import ClassroomStudentInfoProvider
from gamification.repository.gamification_repository import GamificationRedisRepository
from quiz.application.quiz_service import QuizService
from quiz.interface.quiz_handler import QuizHandler
from quiz.repository.host_provider_implementation import SlideHostProvider
from quiz.repository.quiz_repository import QuizRedisRepository
from redis.asyncio import Redis
from shared.application.room.broadcast import RoomBroadcastService
from shared.infrastructure.redis.event_bus import RedisEventBus
from shared.infrastructure.room.in_memory_registry import InMemoryRoomRegistry
from shared.infrastructure.websocket.manager import WSConnectionManager
from shared.infrastructure.websocket.router import WSEventRouter
from slides.application.slide_service import SlideService
from slides.interface.slide_handler import SlideHandler
from slides.repository.slide_repository import SlideRedisRepository

from application.config import settings
from application.event_handlers import RoomEventHandler

logger = logging.getLogger(__name__)


class Application:
    def __init__(self) -> None:
        # Low‑level infrastructure
        self.redis = Redis(host="redis", port=6379, db=0, decode_responses=True)
        self.ws_manager = WSConnectionManager(max_error_tolerance=settings.max_error_tolerance)
        self.room_registry = InMemoryRoomRegistry()
        self.event_bus = RedisEventBus(self.redis)

        # Repositories
        classroom_repo = ClassroomRedisRepository(self.redis)
        slide_repo = SlideRedisRepository(self.redis)
        quiz_repo = QuizRedisRepository(self.redis)
        host_provider = SlideHostProvider(slide_repo)
        gamification_repo = GamificationRedisRepository(self.redis)

        # Services
        self.classroom_service = ClassroomService(classroom_repo)
        self.broadcast_service = RoomBroadcastService(self.room_registry, self.ws_manager)
        self.slide_service = SlideService(slide_repo)

        student_info_provider = ClassroomStudentInfoProvider(self.classroom_service)
        self.gamification_service = GamificationService(
            repo=gamification_repo,
            student_info_provider=student_info_provider,
            ws_manager=self.ws_manager,
            broadcast_service=self.broadcast_service,
            base_score=settings.gamification_base_score,
            streak_multiplier=settings.gamification_streak_multiplier,
        )

        self.quiz_service = QuizService(
            quiz_repo,
            host_provider,
            self.broadcast_service,
            self.gamification_service,
        )

        # Handlers
        self.classroom_handler = ClassroomHandler(
            service=self.classroom_service,
            ws_manager=self.ws_manager,
            room_registry=self.room_registry,
            broadcast_service=self.broadcast_service,
            gamification_service=self.gamification_service,
            quiz_service=self.quiz_service,
        )

        self.slide_handler = SlideHandler(
            service=self.slide_service,
            broadcast_service=self.broadcast_service,
            ws_manager=self.ws_manager,
        )

        self.quiz_handler = QuizHandler(self.quiz_service, self.ws_manager)

        # Event handler and router
        self.event_handler = RoomEventHandler(self.classroom_service, self.broadcast_service)
        self.ws_router = WSEventRouter()
        self.ws_router.register("classroom", self.classroom_handler)
        self.ws_router.register("slides", self.slide_handler)
        self.ws_router.register("quiz", self.quiz_handler)

    async def start_background_tasks(self) -> None:
        try:
            await self.redis.ping()
            logger.info("Redis connection established successfully.")
        except Exception as e:
            logger.error("Redis connection failed: %s", e)
            raise

        asyncio.create_task(self.event_bus.subscribe("room_events", self.event_handler))
        logger.info("Background tasks started (Redis subscriber for 'room_events').")
