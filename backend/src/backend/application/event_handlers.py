import logging
from typing import Any

from classroom.application.classroom_service import ClassroomService
from shared.application.room.broadcast import RoomBroadcastService

logger = logging.getLogger(__name__)


class RoomEventHandler:
    def __init__(
        self, classroom_service: ClassroomService, broadcast_service: RoomBroadcastService
    ) -> None:
        self.classroom_service = classroom_service
        self.broadcast_service = broadcast_service
        self._event_handlers = {"slides:ready": self._handle_slides_ready}

    async def __call__(self, message: dict[str, Any]) -> None:
        event_type = message.get("event")
        logger.debug("RoomEventHandler received event: %s", event_type)
        if not isinstance(event_type, str):
            return
        handler = self._event_handlers.get(event_type)
        if handler:
            await handler(message)
        else:
            logger.debug("No handler for event '%s'", event_type)

    async def _handle_slides_ready(self, event_data: dict[str, Any]) -> None:
        class_code = event_data.get("class_code")
        total_slides = event_data.get("data", {}).get("total_slides")
        if not class_code or total_slides is None:
            logger.warning("Invalid slides:ready event data: %s", event_data)
            return
        success = await self.classroom_service.set_total_slides(class_code, total_slides)
        if success:
            logger.info("slides:ready processed for class %s (total=%d)", class_code, total_slides)
            await self.broadcast_service.broadcast(
                class_code=class_code, event="slides:ready", data={"total_slides": total_slides}
            )
        else:
            logger.warning("Failed to set total_slides for class %s", class_code)
