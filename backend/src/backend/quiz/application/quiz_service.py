import logging

from gamification.application.gamification_service import GamificationService
from quiz.domain.host_provider import HostProvider
from quiz.domain.repository_interface import QuizRepository
from shared.application.room.broadcast import RoomBroadcastService

logger = logging.getLogger(__name__)


class QuizService:
    def __init__(
        self,
        quiz_repo: QuizRepository,
        host_provider: HostProvider,
        broadcast: RoomBroadcastService,
        gamification: GamificationService,
    ):
        self.quiz_repo = quiz_repo
        self.host_provider = host_provider
        self.broadcast = broadcast
        self.gamification = gamification

    async def start_quiz(
        self, session_id: str, class_code: str, question_id: str, options: list[str]
    ) -> None:
        host = await self.host_provider.get_host(class_code)
        if host != session_id:
            logger.warning(
                f"Unauthorized quiz start attempt by {session_id} for class {class_code}"
            )
            raise PermissionError("Only host can start a quiz.")

        if await self.quiz_repo.is_active(class_code, question_id):
            logger.warning(f"Quiz already active: {class_code}/{question_id}")
            raise ValueError("A quiz is already active for this question.")

        await self.quiz_repo.start_quiz(class_code, question_id, options)
        logger.info(f"Quiz started: class={class_code}, question={question_id}, options={options}")

        await self.broadcast.broadcast(
            class_code=class_code,
            event="quiz:started",
            data={"question_id": question_id, "options": options},
        )

    async def answer_quiz(
        self, student_id: str, class_code: str, question_id: str, answer: str
    ) -> None:
        if not await self.quiz_repo.is_active(class_code, question_id):
            logger.warning(f"Answer rejected: quiz {class_code}/{question_id} not active")
            raise ValueError("Quiz is not active.")

        success = await self.quiz_repo.add_answer(class_code, question_id, student_id, answer)
        if not success:
            logger.debug(
                f"Duplicate answer ignored from {student_id} for {class_code}/{question_id}"
            )
            return  # already answered, silently ignore

        answers_count = len(await self.quiz_repo.get_answers(class_code, question_id))
        logger.info(f"Answer recorded: {student_id} -> {answer} (total answered: {answers_count})")

        await self.broadcast.broadcast(
            class_code=class_code,
            event="quiz:answer_received",
            data={"total_answered": answers_count},
        )

    async def stop_quiz(self, session_id: str, class_code: str, question_id: str) -> None:
        host = await self.host_provider.get_host(class_code)
        if host != session_id:
            logger.warning(f"Unauthorized quiz stop by {session_id}")
            raise PermissionError("Only host can stop a quiz.")

        await self.quiz_repo.stop_quiz(class_code, question_id)
        logger.info(f"Quiz stopped: class={class_code}, question={question_id}")

        await self.broadcast.broadcast(
            class_code=class_code, event="quiz:stopped", data={"question_id": question_id}
        )

    async def close_quiz(
        self, session_id: str, class_code: str, question_id: str, correct_answer: str
    ) -> None:
        host = await self.host_provider.get_host(class_code)
        if host != session_id:
            logger.warning(f"Unauthorized quiz close by {session_id}")
            raise PermissionError("Only host can close a quiz.")

        # 1. Fetch answers and compute stats
        answers = await self.quiz_repo.get_answers(class_code, question_id)
        stats = self._calculate_stats(answers)
        logger.info(f"Quiz closing: class={class_code}, question={question_id}, stats={stats}")

        # 2. Delegate to gamification
        await self.gamification.process_quiz_close(
            class_code=class_code,
            question_id=question_id,
            correct_answer=correct_answer,
            answers=answers,
            stats=stats,
        )

        # 3. Delete quiz data from Redis
        await self.quiz_repo.close_quiz(class_code, question_id, correct_answer)
        logger.info(f"Quiz data deleted for class={class_code}, question={question_id}")

    def _calculate_stats(self, answers: dict[str, str]) -> dict[str, int]:
        stats: dict[str, int] = {}
        for ans in answers.values():
            stats[ans] = stats.get(ans, 0) + 1
        return stats
