import logging
from typing import TYPE_CHECKING, Any

from classroom.application.classroom_service import ClassroomService
from classroom.domain.class_payload import CreateClassPayload, JoinClassroomPayload
from shared.domain.room.registry import RoomRegistry
from shared.infrastructure.websocket.manager import WSConnectionManager

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class ClassroomHandler:
    def __init__(
        self,
        service: ClassroomService,
        ws_manager: WSConnectionManager,
        room_registry: RoomRegistry,
    ):
        self.service = service
        self.ws_manager = ws_manager
        self.room_registry = room_registry
        self._event_handlers: dict[str, Callable[[str, dict[str, Any]], Awaitable[None]]] = {
            "classroom:create": self._handle_create,
            "classroom:join": self._handle_join,
            "classroom:sync": self._handle_sync,
        }

    async def __call__(self, event_type: str, session_id: str, payload: dict[str, Any]) -> None:
        logger.debug(
            "ClassroomHandler processing event '%s' from session %s", event_type, session_id
        )
        handler = self._event_handlers.get(event_type)
        if not handler:
            logger.warning(
                f"Unknown classroom event '{event_type}' received from session '{session_id}'."
            )
            await self.ws_manager.send(
                event="classroom:error",
                session_id=session_id,
                data={"message": f"Unknown event '{event_type}'."},
            )
            return

        await handler(session_id, payload)

    async def _handle_create(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            data = CreateClassPayload.model_validate(payload)

            await self.service.create_room(host_id=session_id, class_code=data.class_code)

            await self.room_registry.add_participant(data.class_code, session_id)

            await self.ws_manager.send(
                event="classroom:created",
                session_id=session_id,
                data={"class_code": data.class_code, "status": "success"},
            )
        except ValueError as e:
            logger.warning(f"Validation error on room creation (Session: {session_id}): {e}")
            await self._send_error(session_id, str(e))
        except Exception as e:
            logger.error(
                f"Unexpected error in classroom:create (Session: {session_id}): {e}", exc_info=True
            )
            await self._send_error(session_id, f"Failed to create classroom: {e}")

    async def _handle_join(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            data = JoinClassroomPayload.model_validate(payload)

            student_state = await self.service.join_room(
                student_id=session_id,
                student_name=data.student_name,
                class_code=data.class_code,
            )

            await self.room_registry.add_participant(data.class_code, session_id)

            await self.ws_manager.send(
                event="classroom:joined",
                session_id=session_id,
                data={"class_code": data.class_code, "student": student_state.model_dump()},
            )
        except ValueError as e:
            logger.warning(f"Validation error on room join (Session: {session_id}): {e}")
            await self._send_error(session_id, str(e))
        except Exception as e:
            logger.error(
                f"Unexpected error in classroom:join (Session: {session_id}): {e}", exc_info=True
            )
            await self._send_error(session_id, f"Failed to join classroom: {e}")

    async def _handle_sync(self, session_id: str, _payload: dict[str, Any]) -> None:
        class_code = await self.room_registry.get_room_by_session(session_id)
        if not class_code:
            logger.info(f"Sync ignored: Session '{session_id}' is not associated with any class.")
            return

        room_state = await self.service.get_room_state(class_code)
        if not room_state:
            await self._send_error(session_id, "Failed to fetch classroom data.")
            return

        await self.ws_manager.send(
            event="classroom:state_sync", session_id=session_id, data=room_state.model_dump()
        )
        logger.info(f"Class state '{class_code}' successfully synced for session '{session_id}'.")

    async def _send_error(self, session_id: str, error_message: str) -> None:
        await self.ws_manager.send(
            event="classroom:error",
            session_id=session_id,
            data={"message": error_message},
        )
