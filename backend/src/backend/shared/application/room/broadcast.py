import logging
from typing import Any

from shared.domain.room.registry import RoomRegistry
from shared.infrastructure.websocket.manager import WSConnectionManager

logger = logging.getLogger(__name__)


class RoomBroadcastService:
    def __init__(self, registry: RoomRegistry, ws_manager: WSConnectionManager) -> None:
        self.registry = registry
        self.ws_manager = ws_manager

    async def broadcast(self, class_code: str, event: str, data: dict[str, Any]) -> None:
        participants = await self.registry.get_participants(class_code)
        logger.debug(
            "Broadcasting event '%s' to %d participants in room %s",
            event,
            len(participants),
            class_code,
        )
        for session_id in participants:
            await self.ws_manager.send(event, session_id, data)
