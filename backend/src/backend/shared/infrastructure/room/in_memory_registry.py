import logging

from shared.domain.room.registry import RoomRegistry

logger = logging.getLogger(__name__)


class InMemoryRoomRegistry(RoomRegistry):
    def __init__(self) -> None:
        self._rooms: dict[str, set[str]] = {}
        self._session_room: dict[str, str] = {}

    async def add_participant(self, class_code: str, session_id: str) -> None:
        self._rooms.setdefault(class_code, set()).add(session_id)
        self._session_room[session_id] = class_code
        logger.debug("Session %s added to room %s", session_id, class_code)

    async def remove_participant(self, class_code: str, session_id: str) -> None:
        if class_code in self._rooms:
            self._rooms[class_code].discard(session_id)
            logger.debug("Session %s removed from room %s", session_id, class_code)

    async def get_participants(self, class_code: str) -> set[str]:
        return self._rooms.get(class_code, set())

    async def remove_participant_by_session(self, session_id: str) -> None:
        class_code = self._session_room.pop(session_id, None)
        if class_code and class_code in self._rooms:
            self._rooms[class_code].discard(session_id)
            logger.debug("Session %s fully removed from room %s", session_id, class_code)

    async def get_room_by_session(self, session_id: str) -> str | None:
        return self._session_room.get(session_id)

    async def remove_all_participants(self, class_code: str) -> None:
        participants = self._rooms.pop(class_code, set())
        for session_id in participants:
            self._session_room.pop(session_id, None)
            logger.debug("Session %s removed during class %s termination", session_id, class_code)
        logger.info("All participants removed from registry for room %s", class_code)
