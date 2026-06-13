import logging

from classroom.domain.classroom import Classroom, StudentState
from classroom.domain.repository_interface import ClassroomRepository

logger = logging.getLogger(__name__)


class ClassroomService:
    def __init__(self, repository: ClassroomRepository, room_ttl: int = 1800):
        self.repo = repository
        self.room_ttl = room_ttl

    async def create_room(self, host_id: str, class_code: str) -> None:
        if await self.repo.get_room(class_code):
            logger.warning(f"Room creation failed: Code '{class_code}' already exists.")
            raise ValueError("Class code is already in use.")

        await self.repo.save_room(class_code, host_id, self.room_ttl)
        logger.info(f"Room '{class_code}' created successfully by host '{host_id}'.")

    async def join_room(self, student_id: str, student_name: str, class_code: str) -> StudentState:
        if not await self.repo.get_room(class_code):
            logger.warning(f"Join room failed: Code '{class_code}' not found.")
            raise ValueError("Class not found.")

        student = StudentState(name=student_name)
        await self.repo.add_student(class_code, student_id, student)
        logger.info(f"Student '{student_name}' ({student_id}) joined room '{class_code}'.")

        return student

    async def set_total_slides(self, class_code: str, total_slides: int) -> bool:
        room = await self.repo.get_room(class_code)
        if not room:
            logger.warning(f"Cannot set total_slides: Room '{class_code}' not found.")
            return False

        await self.repo.update_total_slides(class_code, total_slides)
        logger.info(f"Room '{class_code}' total_slides updated to {total_slides}.")
        return True

    async def get_room_state(self, class_code: str) -> Classroom | None:
        room_data = await self.repo.get_room(class_code)
        if not room_data:
            return None

        raw_students = await self.repo.get_all_students(class_code)
        active_students: dict[str, StudentState] = {}

        for session_id, student_json in raw_students.items():
            try:
                active_students[session_id] = StudentState.model_validate_json(student_json)
            except Exception as e:
                logger.warning(f"Failed to parse student state {session_id}: {e}")

        return Classroom(
            class_code=class_code,
            host_session_id=room_data.get("host_session_id", ""),
            current_slide=int(room_data.get("current_slide", 1)),
            total_slides=int(room_data.get("total_slides", 0)),
            active_students=active_students,
        )

    async def verify_host(self, session_id: str, class_code: str) -> None:
        """Verifies if the given session_id is the host of the room."""
        room = await self.repo.get_room(class_code)
        if not room:
            logger.warning("Host verification failed: Room '%s' not found.", class_code)
            raise ValueError("Class not found.")

        if room.get("host_session_id") != session_id:
            logger.warning("Unauthorized action attempt by %s for class %s", session_id, class_code)
            raise PermissionError("Only the host is authorized to perform this action.")

    async def delete_room(self, class_code: str) -> None:
        await self.repo.delete_room_data(class_code)
        logger.info("Room '%s' domain data successfully deleted.", class_code)

    async def remove_student_from_room(self, class_code: str, student_id: str) -> None:
        await self.repo.remove_student(class_code, student_id)
        logger.info("Student %s removed from classroom %s via service", student_id, class_code)

    async def refresh_ttl(self, class_code: str) -> None:
        await self.repo.refresh_room_ttl(class_code, self.room_ttl)
        logger.debug("TTL refreshed via service for class %s", class_code)

    async def handle_student_disconnect(self, session_id: str, class_code: str) -> None:
        room = await self.repo.get_room(class_code)
        if not room:
            logger.warning("Room %s not found during disconnect of %s", class_code, session_id)
            return

        host_id = room.get("host_session_id")
        if session_id == host_id:
            logger.info(
                "Host %s disconnected from class %s: waiting for TTL", session_id, class_code
            )
            return

        await self.remove_student_from_room(class_code, session_id)
        logger.info(
            "Student %s disconnected from class %s: Redis data removed", session_id, class_code
        )
