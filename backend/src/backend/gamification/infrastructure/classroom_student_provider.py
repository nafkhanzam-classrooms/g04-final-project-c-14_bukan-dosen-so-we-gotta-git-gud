import logging

from classroom.application.classroom_service import ClassroomService
from gamification.domain.student_provider import StudentInfoProvider

logger = logging.getLogger(__name__)


class ClassroomStudentInfoProvider(StudentInfoProvider):
    def __init__(self, classroom_service: ClassroomService) -> None:
        self._classroom_service = classroom_service

    async def get_student_names(self, class_code: str) -> dict[str, str]:
        room_state = await self._classroom_service.get_room_state(class_code)
        if not room_state:
            logger.warning("Classroom %s not found for student name lookup", class_code)
            return {}
        return {sid: student.name for sid, student in room_state.active_students.items()}

    async def get_all_student_ids(self, class_code: str) -> list[str]:
        room_state = await self._classroom_service.get_room_state(class_code)
        if not room_state:
            logger.warning("Classroom %s not found for student id lookup", class_code)
            return []
        return list(room_state.active_students.keys())
