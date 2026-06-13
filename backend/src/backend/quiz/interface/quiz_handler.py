import logging
from typing import TYPE_CHECKING, Any

from quiz.application.quiz_service import QuizService
from quiz.domain.quiz_payload import (
    QuizAnswerPayload,
    QuizClosePayload,
    QuizStartPayload,
    QuizStopPayload,
)
from quiz.domain.response import QuizErrorResponse
from shared.domain.redis.event_publisher import EventPublisher
from shared.infrastructure.websocket.manager import WSConnectionManager

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class QuizHandler:
    def __init__(
        self, service: QuizService, ws_manager: WSConnectionManager, event_bus: EventPublisher
    ):
        self.service = service
        self.ws_manager = ws_manager
        self.event_bus = event_bus
        self._handlers: dict[str, Callable[[str, dict[str, Any]], Awaitable[None]]] = {
            "quiz:start": self._handle_start,
            "quiz:answer": self._handle_answer,
            "quiz:stop": self._handle_stop,
            "quiz:close": self._handle_close,
        }

    async def __call__(self, event_type: str, session_id: str, payload: dict[str, Any]) -> None:
        logger.debug(f"QuizHandler received event {event_type} from {session_id}")
        handler = self._handlers.get(event_type)
        if handler:
            await handler(session_id, payload)
        else:
            logger.warning(f"Unknown quiz event {event_type}")
            await self.ws_manager.send(
                "quiz:error", session_id, {"message": f"Unknown event '{event_type}'"}
            )

    async def _handle_start(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            data = QuizStartPayload(**payload)
            await self.service.start_quiz(
                session_id, data.class_code, data.question_id, data.options
            )
            await self.event_bus.publish(
                "room_events", {"event": "room:activity", "class_code": data.class_code}
            )
            logger.info("room:activity published for class %s (quiz start)", data.class_code)
        except (PermissionError, ValueError) as e:
            logger.warning(f"Start quiz error: {e}")
            await self._send_error(session_id, str(e))
        except Exception:
            logger.exception("Unexpected error in quiz:start")
            await self._send_error(session_id, "Internal server error")

    async def _handle_stop(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            data = QuizStopPayload(**payload)
            await self.service.stop_quiz(session_id, data.class_code, data.question_id)
            await self.event_bus.publish(
                "room_events", {"event": "room:activity", "class_code": data.class_code}
            )
            logger.info("room:activity published for class %s (quiz stop)", data.class_code)
        except (PermissionError, ValueError) as e:
            logger.warning(f"Stop quiz error: {e}")
            await self._send_error(session_id, str(e))
        except Exception:
            logger.exception("Unexpected error in quiz:stop")
            await self._send_error(session_id, "Internal server error")

    async def _handle_close(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            data = QuizClosePayload(**payload)
            await self.service.close_quiz(
                session_id, data.class_code, data.question_id, data.correct_answer
            )
            await self.event_bus.publish(
                "room_events", {"event": "room:activity", "class_code": data.class_code}
            )
            logger.info("room:activity published for class %s (quiz close)", data.class_code)
        except (PermissionError, ValueError) as e:
            logger.warning(f"Close quiz error: {e}")
            await self._send_error(session_id, str(e))
        except Exception:
            logger.exception("Unexpected error in quiz:close")
            await self._send_error(session_id, "Internal server error")

    async def _handle_answer(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            data = QuizAnswerPayload(**payload)
            await self.service.answer_quiz(
                session_id, data.class_code, data.question_id, data.answer
            )
        except ValueError as e:
            logger.warning(f"Answer quiz error: {e}")
            await self._send_error(session_id, str(e))
        except Exception:
            logger.exception("Unexpected error in quiz:answer")
            await self._send_error(session_id, "Internal server error")

    async def _send_error(self, session_id: str, message: str) -> None:
        response = QuizErrorResponse(message=message)
        await self.ws_manager.send("quiz:error", session_id, data=response.model_dump())
