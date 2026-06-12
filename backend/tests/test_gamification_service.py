from unittest.mock import AsyncMock, MagicMock, call

import pytest
from gamification.application.gamification_service import GamificationService


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_streak = AsyncMock()
    repo.set_streak = AsyncMock()
    repo.get_total_score = AsyncMock()
    repo.set_leaderboard_score = AsyncMock()
    repo.get_leaderboard = AsyncMock()
    repo.delete_gamification_data = AsyncMock()
    return repo


@pytest.fixture
def mock_student_provider():
    provider = MagicMock()
    provider.get_student_names = AsyncMock()
    provider.get_all_student_ids = AsyncMock(return_value=[])
    return provider


@pytest.fixture
def mock_ws_manager():
    ws = MagicMock()
    ws.send = AsyncMock()
    return ws


@pytest.fixture
def mock_broadcast():
    bc = MagicMock()
    bc.broadcast = AsyncMock()
    return bc


@pytest.fixture
def service(mock_repo, mock_student_provider, mock_ws_manager, mock_broadcast):
    return GamificationService(
        repo=mock_repo,
        student_info_provider=mock_student_provider,
        ws_manager=mock_ws_manager,
        broadcast_service=mock_broadcast,
        base_score=100,
        streak_multiplier=25,
    )


class TestProcessQuizClose:
    @pytest.mark.asyncio
    async def test_correct_first_answer_gives_base_score_no_bonus(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        mock_repo.get_streak.return_value = 0
        mock_repo.get_total_score.return_value = 0

        await service.process_quiz_close(
            class_code="MATH101",
            question_id="q1",
            correct_answer="A",
            answers={"s1": "A"},
            stats={"A": 1},
        )

        mock_repo.set_streak.assert_called_once_with("MATH101", "s1", 1)
        mock_repo.set_leaderboard_score.assert_called_once_with("MATH101", "s1", 100)

        mock_ws_manager.send.assert_called_once_with(
            "game:score_update",
            "s1",
            {
                "class_code": "MATH101",
                "points_earned": 100,
                "base_points": 100,
                "streak_bonus": 0,
                "current_streak": 1,
                "total_score": 100,
            },
        )

        mock_broadcast.broadcast.assert_called_once_with(
            "MATH101",
            "quiz:closed",
            {"question_id": "q1", "correct_answer": "A", "stats": {"A": 1}},
        )

    @pytest.mark.asyncio
    async def test_consecutive_correct_answers_apply_streak_bonus(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        mock_repo.get_streak.return_value = 2
        mock_repo.get_total_score.return_value = 500

        await service.process_quiz_close(
            class_code="MATH101",
            question_id="q2",
            correct_answer="B",
            answers={"s1": "B"},
            stats={"B": 1},
        )

        mock_repo.set_streak.assert_called_once_with("MATH101", "s1", 3)
        mock_repo.set_leaderboard_score.assert_called_once_with("MATH101", "s1", 650)
        mock_ws_manager.send.assert_called_once_with(
            "game:score_update",
            "s1",
            {
                "class_code": "MATH101",
                "points_earned": 150,
                "base_points": 100,
                "streak_bonus": 50,
                "current_streak": 3,
                "total_score": 650,
            },
        )

    @pytest.mark.asyncio
    async def test_wrong_answer_resets_streak_keeps_score_unchanged(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        mock_repo.get_streak.return_value = 5
        mock_repo.get_total_score.return_value = 1000

        await service.process_quiz_close(
            class_code="MATH101",
            question_id="q3",
            correct_answer="C",
            answers={"s1": "D"},
            stats={"D": 1},
        )

        mock_repo.set_streak.assert_called_once_with("MATH101", "s1", 0)
        mock_repo.set_leaderboard_score.assert_not_called()

        mock_ws_manager.send.assert_called_once_with(
            "game:score_update",
            "s1",
            {
                "class_code": "MATH101",
                "points_earned": 0,
                "base_points": 0,
                "streak_bonus": 0,
                "current_streak": 0,
                "total_score": 1000,
            },
        )

        mock_broadcast.broadcast.assert_called_once_with(
            "MATH101",
            "quiz:closed",
            {"question_id": "q3", "correct_answer": "C", "stats": {"D": 1}},
        )

    @pytest.mark.asyncio
    async def test_multiple_students_mixed_results(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        mock_repo.get_streak.side_effect = [0, 3]
        mock_repo.get_total_score.side_effect = [0, 200]

        answers = {"s1": "A", "s2": "D"}
        stats = {"A": 1, "D": 1}

        await service.process_quiz_close(
            class_code="MATH101",
            question_id="q4",
            correct_answer="A",
            answers=answers,
            stats=stats,
        )

        assert mock_repo.set_streak.call_args_list == [
            call("MATH101", "s1", 1),
            call("MATH101", "s2", 0),
        ]
        mock_repo.set_leaderboard_score.assert_called_once_with("MATH101", "s1", 100)

        assert mock_ws_manager.send.call_count == 2
        mock_ws_manager.send.assert_any_call(
            "game:score_update",
            "s1",
            {
                "class_code": "MATH101",
                "points_earned": 100,
                "base_points": 100,
                "streak_bonus": 0,
                "current_streak": 1,
                "total_score": 100,
            },
        )
        mock_ws_manager.send.assert_any_call(
            "game:score_update",
            "s2",
            {
                "class_code": "MATH101",
                "points_earned": 0,
                "base_points": 0,
                "streak_bonus": 0,
                "current_streak": 0,
                "total_score": 200,
            },
        )

        mock_broadcast.broadcast.assert_called_once_with(
            "MATH101",
            "quiz:closed",
            {"question_id": "q4", "correct_answer": "A", "stats": stats},
        )

    @pytest.mark.asyncio
    async def test_quiz_closed_broadcast_always_contains_correct_answer_and_stats(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        await service.process_quiz_close(
            class_code="C1", question_id="q99", correct_answer="Z", answers={}, stats={}
        )

        mock_broadcast.broadcast.assert_called_once_with(
            "C1",
            "quiz:closed",
            {"question_id": "q99", "correct_answer": "Z", "stats": {}},
        )

    @pytest.mark.asyncio
    async def test_inactivity_penalty_resets_streak_for_non_responders(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        mock_student_provider.get_all_student_ids.return_value = ["s1", "s2"]
        answers = {"s1": "A"}

        # side_effect order:
        # 1. get_streak for s1 (scoring loop)
        # 2. get_streak for s2 (inactivity loop)
        mock_repo.get_streak.side_effect = [0, 3]
        mock_repo.get_total_score.side_effect = [0, 500]

        await service.process_quiz_close(
            class_code="C1", question_id="q", correct_answer="A", answers=answers, stats={"A": 1}
        )

        mock_repo.set_streak.assert_any_call("C1", "s2", 0)
        mock_ws_manager.send.assert_any_call(
            "game:score_update",
            "s2",
            {
                "class_code": "C1",
                "points_earned": 0,
                "base_points": 0,
                "streak_bonus": 0,
                "current_streak": 0,
                "total_score": 500,
            },
        )
        mock_ws_manager.send.assert_any_call(
            "game:score_update",
            "s1",
            {
                "class_code": "C1",
                "points_earned": 100,
                "base_points": 100,
                "streak_bonus": 0,
                "current_streak": 1,
                "total_score": 100,
            },
        )


# Tests for the new classroom:end cleanup features
@pytest.mark.asyncio
async def test_get_formatted_leaderboard(service, mock_repo, mock_student_provider):
    class_code = "MATH123"

    mock_repo.get_leaderboard.return_value = [("sess_1", 500.0), ("sess_2", 300.0)]
    mock_student_provider.get_student_names.return_value = {"sess_1": "Alice", "sess_2": "Bob"}

    async def mock_get_streak(cc, sid):
        return 2 if sid == "sess_1" else 0

    mock_repo.get_streak = AsyncMock(side_effect=mock_get_streak)

    result = await service.get_formatted_leaderboard(class_code, top_n=2)

    assert len(result) == 2
    assert result[0] == {"name": "Alice", "score": 500, "is_streak": True}
    assert result[1] == {"name": "Bob", "score": 300, "is_streak": False}


@pytest.mark.asyncio
async def test_gamification_delete_data():
    from gamification.repository.gamification_repository import GamificationRedisRepository

    mock_redis = AsyncMock()
    repo = GamificationRedisRepository(mock_redis)

    await repo.delete_gamification_data("MATH123")

    mock_redis.delete.assert_called_once_with(
        "gamification:MATH123:streaks", "gamification:MATH123:leaderboard"
    )
