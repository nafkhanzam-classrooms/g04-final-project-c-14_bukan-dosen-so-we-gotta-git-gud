from typing import Any

from classroom.application.classroom_service import ClassroomService
from shared.application.room.broadcast import RoomBroadcastService


class RoomEventHandler:
    def __init__(
        self, classroom_service: ClassroomService, broadcast_service: RoomBroadcastService
    ) -> None:
        self.classroom_service = classroom_service
        self.broadcast_service = broadcast_service
        self._event_handlers = {"slides:ready": self._handle_slides_ready}

    async def __call__(self, message: dict[str, Any]) -> None:
        event_type = message.get("event")
        if not isinstance(event_type, str):
            return
        handler = self._event_handlers.get(event_type)
        if handler:
            await handler(message)

    async def _handle_slides_ready(self, event_data: dict[str, Any]) -> None:
        class_code = event_data.get("class_code")
        total_slides = event_data.get("data", {}).get("total_slides")
        if not class_code or total_slides is None:
            return
        success = await self.classroom_service.set_total_slides(class_code, total_slides)
        if success:
            await self.broadcast_service.broadcast(
                class_code=class_code, event="slides:ready", data={"total_slides": total_slides}
            )
