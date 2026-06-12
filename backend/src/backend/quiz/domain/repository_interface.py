from abc import ABC, abstractmethod


class QuizRepository(ABC):
    @abstractmethod
    async def start_quiz(self, class_code: str, question_id: str, options: list[str]) -> None: ...

    @abstractmethod
    async def stop_quiz(self, class_code: str, question_id: str) -> None: ...

    @abstractmethod
    async def is_active(self, class_code: str, question_id: str) -> bool: ...

    @abstractmethod
    async def add_answer(
        self, class_code: str, question_id: str, student_id: str, answer: str
    ) -> bool: ...

    @abstractmethod
    async def get_answers(self, class_code: str, question_id: str) -> dict[str, str]: ...

    @abstractmethod
    async def close_quiz(self, class_code: str, question_id: str, correct_answer: str) -> None: ...

    @abstractmethod
    async def get_options(self, class_code: str, question_id: str) -> list[str] | None: ...
