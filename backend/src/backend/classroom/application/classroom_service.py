import logging

from classroom.domain.classroom import StudentState
from classroom.repository.classroom_repository import ClassroomRedisRepository

logger = logging.getLogger(__name__)


class ClassroomService:
    def __init__(self, repository: ClassroomRedisRepository):
        self.repo = repository

    async def create_room(self, host_id: str, class_code: str) -> None:
        if await self.repo.get_room(class_code):
            logger.warning(f"Room creation failed: Code '{class_code}' already exists.")
            raise ValueError("Class code is already in use.")

        await self.repo.save_room(class_code, host_id)
        logger.info(f"Room '{class_code}' created successfully by host '{host_id}'.")

    async def join_room(self, student_id: str, student_name: str, class_code: str) -> StudentState:
        if not await self.repo.get_room(class_code):
            logger.warning(f"Join room failed: Code '{class_code}' not found.")
            raise ValueError("Class not found.")

        student = StudentState(name=student_name)
        await self.repo.add_student(class_code, student_id, student)
        logger.info(f"Student '{student_name}' ({student_id}) joined room '{class_code}'.")

        return student
