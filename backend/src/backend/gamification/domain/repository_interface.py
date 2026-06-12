from abc import ABC, abstractmethod


class GamificationRepository(ABC):
    @abstractmethod
    async def get_streak(self, class_code: str, student_id: str) -> int:
        """Return the current streak for a student (0 if not found)."""
        ...

    @abstractmethod
    async def set_streak(self, class_code: str, student_id: str, streak: int) -> None:
        """Save the updated streak."""
        ...

    @abstractmethod
    async def get_total_score(self, class_code: str, student_id: str) -> float:
        """Return total score from the leaderboard ZSET (0 if missing)."""
        ...

    @abstractmethod
    async def set_leaderboard_score(self, class_code: str, student_id: str, score: float) -> None:
        """Add or update the student's score in the ZSET."""
        ...

    @abstractmethod
    async def get_leaderboard(self, class_code: str, top_n: int = 10) -> list[tuple[str, float]]:
        """Return top_n entries as (student_id, score) descending."""
        ...

    @abstractmethod
    async def delete_gamification_data(self, class_code: str) -> None: ...
