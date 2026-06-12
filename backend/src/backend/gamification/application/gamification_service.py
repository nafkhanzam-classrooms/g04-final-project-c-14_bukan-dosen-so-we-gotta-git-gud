import logging
from typing import Any

from gamification.domain.repository_interface import GamificationRepository
from gamification.domain.student_provider import StudentInfoProvider
from shared.application.room.broadcast import RoomBroadcastService
from shared.infrastructure.websocket.manager import WSConnectionManager

logger = logging.getLogger(__name__)


class GamificationService:
    def __init__(
        self,
        repo: GamificationRepository,
        student_info_provider: StudentInfoProvider,
        ws_manager: WSConnectionManager,
        broadcast_service: RoomBroadcastService,
        base_score: int = 100,
        streak_multiplier: int = 25,
    ) -> None:
        self._repo = repo
        self._student_provider = student_info_provider
        self._ws_manager = ws_manager
        self._broadcast = broadcast_service
        self.base_score = base_score
        self.streak_multiplier = streak_multiplier

    async def process_quiz_close(
        self,
        class_code: str,
        question_id: str,
        correct_answer: str,
        answers: dict[str, str],
        stats: dict[str, int],
    ) -> None:
        logger.info(
            "Processing quiz close for class=%s, question=%s, answers=%d",
            class_code,
            question_id,
            len(answers),
        )

        # 1. Score each student who submitted an answer
        for student_id, answer in answers.items():
            is_correct = answer == correct_answer
            old_streak = await self._repo.get_streak(class_code, student_id)
            old_total = await self._repo.get_total_score(class_code, student_id)

            if is_correct:
                new_streak = old_streak + 1
                if new_streak == 1:
                    points_earned = self.base_score
                    bonus = 0
                else:
                    bonus = self.streak_multiplier * (new_streak - 1)
                    points_earned = self.base_score + bonus

                new_total = old_total + points_earned
                await self._repo.set_streak(class_code, student_id, new_streak)
                await self._repo.set_leaderboard_score(class_code, student_id, new_total)

                logger.debug(
                    "Student %s correct: streak=%d, earned=%d (base=%d, bonus=%d), total=%d",
                    student_id,
                    new_streak,
                    points_earned,
                    self.base_score,
                    bonus,
                    new_total,
                )

                await self._ws_manager.send(
                    "game:score_update",
                    student_id,
                    {
                        "class_code": class_code,
                        "points_earned": points_earned,
                        "base_points": self.base_score,
                        "streak_bonus": bonus,
                        "current_streak": new_streak,
                        "total_score": new_total,
                    },
                )
            else:
                # Wrong answer: reset streak, keep total, send update
                await self._repo.set_streak(class_code, student_id, 0)
                logger.debug("Student %s wrong: streak reset", student_id)
                await self._ws_manager.send(
                    "game:score_update",
                    student_id,
                    {
                        "class_code": class_code,
                        "points_earned": 0,
                        "base_points": 0,
                        "streak_bonus": 0,
                        "current_streak": 0,
                        "total_score": old_total,
                    },
                )

        # 2. Penalise inactivity
        all_student_ids = await self._student_provider.get_all_student_ids(class_code)
        non_responders = [sid for sid in all_student_ids if sid not in answers]

        for sid in non_responders:
            current_streak = await self._repo.get_streak(class_code, sid)
            if current_streak > 0:
                # Reset streak for non‑responders to 0
                await self._repo.set_streak(class_code, sid, 0)
                old_total = await self._repo.get_total_score(class_code, sid)
                logger.debug(
                    "Student %s did not answer - streak reset from %d to 0", sid, current_streak
                )
                await self._ws_manager.send(
                    "game:score_update",
                    sid,
                    {
                        "class_code": class_code,
                        "points_earned": 0,
                        "base_points": 0,
                        "streak_bonus": 0,
                        "current_streak": 0,
                        "total_score": old_total,
                    },
                )
            else:
                # Streak already 0
                logger.debug("Student %s did not answer, streak already 0", sid)

        # 3. Broadcast quiz:closed
        await self._broadcast.broadcast(
            class_code,
            "quiz:closed",
            {
                "question_id": question_id,
                "correct_answer": correct_answer,
                "stats": stats,
            },
        )
        logger.info("quiz:closed broadcast for class %s", class_code)

    async def get_formatted_leaderboard(
        self, class_code: str, top_n: int = 10
    ) -> list[dict[str, Any]]:
        """Constructs the final leaderboard for frontend consumption."""
        try:
            top = await self._repo.get_leaderboard(class_code, top_n=top_n)
            names = await self._student_provider.get_student_names(class_code)
            top_students = []
            for sid, score in top:
                name = names.get(sid, "Unknown")
                streak = await self._repo.get_streak(class_code, sid)
                top_students.append({"name": name, "score": int(score), "is_streak": streak > 0})
            return top_students
        except Exception:
            logger.exception("Failed to build final leaderboard for class %s", class_code)
            return []

    async def cleanup_gamification_data(self, class_code: str) -> None:
        await self._repo.delete_gamification_data(class_code)
        logger.info("Gamification data fully cleaned up for room %s", class_code)
