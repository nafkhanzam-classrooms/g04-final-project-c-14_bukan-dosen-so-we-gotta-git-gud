from abc import ABC, abstractmethod
from typing import Any

from classroom.domain.classroom import StudentState


class ClassroomRepository(ABC):
    @abstractmethod
    async def save_room(self, class_code: str, host_session_id: str, ttl: int) -> None: ...

    @abstractmethod
    async def get_room(self, class_code: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def add_student(
        self, class_code: str, session_id: str, student: StudentState
    ) -> None: ...

    @abstractmethod
    async def update_total_slides(self, class_code: str, total: int) -> None: ...

    @abstractmethod
    async def get_all_students(self, class_code: str) -> dict[str, str]: ...

    @abstractmethod
    async def delete_room_data(self, class_code: str) -> None: ...

    @abstractmethod
    async def refresh_room_ttl(self, class_code: str, ttl: int) -> None: ...

    @abstractmethod
    async def remove_student(self, class_code: str, session_id: str) -> None: ...
