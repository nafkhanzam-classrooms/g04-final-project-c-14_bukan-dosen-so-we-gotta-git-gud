import logging
from typing import TYPE_CHECKING, Any

from classroom.application.classroom_service import ClassroomService
from classroom.domain.class_payload import (
    CreateClassPayload,
    EndClassroomPayload,
    JoinClassroomPayload,
)
from classroom.domain.response import (
    ClassroomCreatedResponse,
    ClassroomEndedResponse,
    ClassroomErrorResponse,
    ClassroomJoinedResponse,
    TopStudentResponse,
)
from gamification.application.gamification_service import GamificationService
from quiz.application.quiz_service import QuizService
from shared.application.room.broadcast import RoomBroadcastService
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
        broadcast_service: RoomBroadcastService,
        gamification_service: GamificationService,
        quiz_service: QuizService,
    ):
        self.service = service
        self.ws_manager = ws_manager
        self.room_registry = room_registry
        self.broadcast_service = broadcast_service
        self.gamification_service = gamification_service
        self.quiz_service = quiz_service
        self._event_handlers: dict[str, Callable[[str, dict[str, Any]], Awaitable[None]]] = {
            "classroom:create": self._handle_create,
            "classroom:join": self._handle_join,
            "classroom:sync": self._handle_sync,
            "classroom:end": self._handle_end,
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

            response_data = ClassroomCreatedResponse(class_code=data.class_code)

            await self.ws_manager.send(
                event="classroom:created",
                session_id=session_id,
                data=response_data.model_dump(),
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

            await self.service.join_room(
                student_id=session_id, student_name=data.student_name, class_code=data.class_code
            )

            await self.room_registry.add_participant(data.class_code, session_id)

            response = ClassroomJoinedResponse(
                class_code=data.class_code, student_name=data.student_name
            )
            await self.ws_manager.send(
                event="classroom:joined",
                session_id=session_id,
                data=response.model_dump(),
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
        response = ClassroomErrorResponse(message=error_message)
        await self.ws_manager.send(
            event="classroom:error",
            session_id=session_id,
            data=response.model_dump(),
        )

    async def _handle_end(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            data = EndClassroomPayload.model_validate(payload)
            class_code = data.class_code

            logger.info("Session %s attempting to end classroom %s", session_id, class_code)

            # 1. Authorize: Check if sender is the legitimate host
            await self.service.verify_host(session_id, class_code)

            # 2. Retrieve final formatted leaderboard (must happen before room data is deleted)
            top_students = await self.gamification_service.get_formatted_leaderboard(class_code)

            # 3. Broadcast termination event to all participants
            top = [TopStudentResponse.model_validate(student) for student in top_students]

            response = ClassroomEndedResponse(class_code=class_code, top_students=top)
            await self.broadcast_service.broadcast(
                class_code=class_code,
                event="classroom:ended",
                data=response.model_dump(),
            )

            # 4. Clean up distributed Redis data
            await self.gamification_service.cleanup_gamification_data(class_code)
            await self.quiz_service.cleanup_quiz_data(class_code)
            await self.service.delete_room(class_code)

            # 5. Flush memory registry
            await self.room_registry.remove_all_participants(class_code)

            logger.info("Classroom %s successfully ended and fully cleaned up.", class_code)

        except ValueError as e:
            logger.warning("Validation error on room end (Session: %s): %s", session_id, e)
            await self._send_error(session_id, str(e))
        except PermissionError as e:
            logger.warning("Permission error on room end (Session: %s): %s", session_id, e)
            await self._send_error(session_id, str(e))
        except Exception as e:
            logger.error(
                "Unexpected error in classroom:end (Session: %s): %s", session_id, e, exc_info=True
            )
            await self._send_error(session_id, "Failed to end classroom due to internal error.")
