from abc import ABC, abstractmethod


class StudentInfoProvider(ABC):
    @abstractmethod
    async def get_student_names(self, class_code: str) -> dict[str, str]:
        """Return a mapping from session_id to student name."""
        ...

    @abstractmethod
    async def get_all_student_ids(self, class_code: str) -> list[str]:
        """Return all student session IDs currently in the class."""
        ...
