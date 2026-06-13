import logging
from typing import TYPE_CHECKING, Any

from shared.application.room.broadcast import RoomBroadcastService
from shared.domain.redis.event_publisher import EventPublisher
from shared.infrastructure.websocket.manager import WSConnectionManager
from slides.application.slide_service import SlideService
from slides.domain.response import SlidesChangedResponse, SlidesErrorResponse
from slides.domain.slide_payload import ChangeSlidePayload

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class SlideHandler:
    def __init__(
        self,
        service: SlideService,
        broadcast_service: RoomBroadcastService,
        ws_manager: WSConnectionManager,
        event_bus: EventPublisher,
    ):
        self.service = service
        self.broadcast_service = broadcast_service
        self.ws_manager = ws_manager
        self.event_bus = event_bus
        self._event_handlers: dict[str, Callable[[str, dict[str, Any]], Awaitable[None]]] = {
            "slides:change": self._handle_slide_change,
        }

    async def __call__(self, event_type: str, session_id: str, payload: dict[str, Any]) -> None:
        logger.debug("SlideHandler processing event '%s' from session %s", event_type, session_id)
        handler = self._event_handlers.get(event_type)
        if handler:
            await handler(session_id, payload)
        else:
            logger.warning("Unknown slides event '%s' from session %s", event_type, session_id)

    async def _handle_slide_change(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            data = ChangeSlidePayload.model_validate(payload)

            await self.service.change_slide(
                session_id=session_id, class_code=data.class_code, slide_number=data.slide_number
            )

            response = SlidesChangedResponse(slide_number=data.slide_number)

            await self.broadcast_service.broadcast(
                class_code=data.class_code,
                event="slides:changed",
                data=response.model_dump(),
            )

            await self.event_bus.publish(
                "room_events", {"event": "room:activity", "class_code": data.class_code}
            )
            logger.info("room:activity published for class %s (slide change)", data.class_code)

            logger.info(
                "Slide changed to %d in room '%s' by host %s",
                data.slide_number,
                data.class_code,
                session_id,
            )

        except PermissionError as e:
            await self.ws_manager.send(
                "slides:error", session_id, data=SlidesErrorResponse(message=str(e)).model_dump()
            )
        except ValueError as e:
            await self.ws_manager.send(
                "slides:error", session_id, data=SlidesErrorResponse(message=str(e)).model_dump()
            )

        except Exception:
            logger.exception("Unexpected error in slide change handler for session %s", session_id)
            await self.ws_manager.send(
                "slides:error",
                session_id,
                data=SlidesErrorResponse(message="Internal server error").model_dump(),
            )
