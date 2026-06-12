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
        # Arrange
        # get_streak called twice: first for scoring (returns 0), second for leaderboard (returns 1)
        mock_repo.get_streak.side_effect = [0, 1]
        mock_repo.get_total_score.return_value = 0
        mock_repo.get_leaderboard.return_value = [("s1", 100)]
        mock_student_provider.get_student_names.return_value = {"s1": "Alice"}
        # get_all_student_ids returns empty list by default, which is fine

        # Act
        await service.process_quiz_close(
            class_code="MATH101",
            question_id="q1",
            correct_answer="A",
            answers={"s1": "A"},
            stats={"A": 1},
        )

        # Assert streak and score persisted
        mock_repo.set_streak.assert_called_once_with("MATH101", "s1", 1)
        mock_repo.set_leaderboard_score.assert_called_once_with("MATH101", "s1", 100)

        # Personal update
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

        # Leaderboard broadcast (is_streak=True because streak now = 1)
        mock_broadcast.broadcast.assert_any_call(
            "MATH101",
            "game:leaderboard",
            {
                "class_code": "MATH101",
                "top_students": [{"name": "Alice", "score": 100, "is_streak": True}],
            },
        )

        # quiz:closed broadcast
        mock_broadcast.broadcast.assert_any_call(
            "MATH101",
            "quiz:closed",
            {"question_id": "q1", "correct_answer": "A", "stats": {"A": 1}},
        )

    @pytest.mark.asyncio
    async def test_consecutive_correct_answers_apply_streak_bonus(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        # Student has streak=2, total=500 -> after correct, streak=3, earned=150, total=650
        # get_streak: first call returns 2 (scoring), second call returns 3 (leaderboard)
        mock_repo.get_streak.side_effect = [2, 3]
        mock_repo.get_total_score.return_value = 500
        mock_repo.get_leaderboard.return_value = [("s1", 650)]
        mock_student_provider.get_student_names.return_value = {"s1": "Bob"}

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

        # Leaderboard now shows updated score and streak > 0
        mock_broadcast.broadcast.assert_any_call(
            "MATH101",
            "game:leaderboard",
            {
                "class_code": "MATH101",
                "top_students": [{"name": "Bob", "score": 650, "is_streak": True}],
            },
        )

    @pytest.mark.asyncio
    async def test_wrong_answer_resets_streak_keeps_score_unchanged(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        # Student had streak=5, total=1000, but answers wrong
        # get_streak: first call returns 5 (scoring), second call returns 0 (leaderboard after reset)
        mock_repo.get_streak.side_effect = [5, 0]
        mock_repo.get_total_score.return_value = 1000
        mock_repo.get_leaderboard.return_value = [("s1", 1000)]
        mock_student_provider.get_student_names.return_value = {"s1": "Carol"}

        await service.process_quiz_close(
            class_code="MATH101",
            question_id="q3",
            correct_answer="C",
            answers={"s1": "D"},  # wrong
            stats={"D": 1},
        )

        mock_repo.set_streak.assert_called_once_with("MATH101", "s1", 0)
        # No score change (set_leaderboard_score not called)
        mock_repo.set_leaderboard_score.assert_not_called()

        # Now a wrong answer does trigger a game:score_update (points_earned=0, streak=0)
        mock_ws_manager.send.assert_called_once_with(
            "game:score_update",
            "s1",
            {
                "class_code": "MATH101",
                "points_earned": 0,
                "base_points": 0,
                "streak_bonus": 0,
                "current_streak": 0,
                "total_score": 1000,  # unchanged
            },
        )

        # Leaderboard still broadcast, but is_streak=False
        mock_broadcast.broadcast.assert_any_call(
            "MATH101",
            "game:leaderboard",
            {
                "class_code": "MATH101",
                "top_students": [{"name": "Carol", "score": 1000, "is_streak": False}],
            },
        )

        mock_broadcast.broadcast.assert_any_call(
            "MATH101",
            "quiz:closed",
            {"question_id": "q3", "correct_answer": "C", "stats": {"D": 1}},
        )

    @pytest.mark.asyncio
    async def test_multiple_students_mixed_results(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        # Two students: Alice correct (streak 0 → 1), Bob wrong (streak 3 → 0)
        # get_streak calls: Alice initial (0), Bob initial (3), Alice leaderboard (1), Bob leaderboard (0)
        mock_repo.get_streak.side_effect = [0, 3, 1, 0]
        mock_repo.get_total_score.side_effect = [0, 200, 100, 200]
        mock_repo.get_leaderboard.return_value = [("s1", 100), ("s2", 200)]
        mock_student_provider.get_student_names.return_value = {"s1": "Alice", "s2": "Bob"}

        answers = {"s1": "A", "s2": "D"}
        stats = {"A": 1, "D": 1}

        await service.process_quiz_close(
            class_code="MATH101",
            question_id="q4",
            correct_answer="A",
            answers=answers,
            stats=stats,
        )

        # Check set_streak calls
        assert mock_repo.set_streak.call_args_list == [
            call("MATH101", "s1", 1),
            call("MATH101", "s2", 0),
        ]
        mock_repo.set_leaderboard_score.assert_called_once_with("MATH101", "s1", 100)

        # Personal update: Alice gets positive update, Bob gets zero
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

        # Leaderboard: Alice is_streak=True, Bob is_streak=False
        mock_broadcast.broadcast.assert_any_call(
            "MATH101",
            "game:leaderboard",
            {
                "class_code": "MATH101",
                "top_students": [
                    {"name": "Alice", "score": 100, "is_streak": True},
                    {"name": "Bob", "score": 200, "is_streak": False},
                ],
            },
        )

        mock_broadcast.broadcast.assert_any_call(
            "MATH101",
            "quiz:closed",
            {"question_id": "q4", "correct_answer": "A", "stats": stats},
        )

    @pytest.mark.asyncio
    async def test_leaderboard_limited_to_top_10(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        mock_repo.get_streak.side_effect = [0, 1]  # for one correct answer then leaderboard
        mock_repo.get_total_score.return_value = 0
        mock_repo.get_leaderboard.return_value = [("s1", 10)]
        mock_student_provider.get_student_names.return_value = {"s1": "Test"}

        await service.process_quiz_close(
            class_code="C", question_id="q", correct_answer="X", answers={"s1": "X"}, stats={"X": 1}
        )

        mock_repo.get_leaderboard.assert_called_once_with("C", top_n=10)

    @pytest.mark.asyncio
    async def test_quiz_closed_broadcast_always_contains_correct_answer_and_stats(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        # No answers -> scoring loop does nothing; inactivity check uses empty list from get_all_student_ids
        mock_repo.get_leaderboard.return_value = []
        mock_student_provider.get_student_names.return_value = {}

        await service.process_quiz_close(
            class_code="C1", question_id="q99", correct_answer="Z", answers={}, stats={}
        )

        mock_broadcast.broadcast.assert_any_call(
            "C1",
            "quiz:closed",
            {"question_id": "q99", "correct_answer": "Z", "stats": {}},
        )

    @pytest.mark.asyncio
    async def test_inactivity_penalty_resets_streak_for_non_responders(
        self, service, mock_repo, mock_ws_manager, mock_broadcast, mock_student_provider
    ):
        # Alice answered correctly, Bob did not answer
        mock_student_provider.get_all_student_ids.return_value = ["s1", "s2"]
        answers = {"s1": "A"}
        # get_streak: Alice scoring (0), Bob inactivity check (3), Alice leaderboard (1), Bob leaderboard (0)
        mock_repo.get_streak.side_effect = [0, 3, 1, 0]
        # get_total_score: Alice old (0), Bob old (500), then leaderboard values (100, 500) – note: get_total_score is called for leaderboard? Not needed. The code for leaderboard only calls get_leaderboard, not get_total_score. So we only need side_effect for the scoring part.
        mock_repo.get_total_score.side_effect = [0, 500]  # Alice old_total, Bob old_total
        mock_repo.get_leaderboard.return_value = [("s1", 100), ("s2", 500)]
        mock_student_provider.get_student_names.return_value = {"s1": "Alice", "s2": "Bob"}

        await service.process_quiz_close(
            class_code="C1", question_id="q", correct_answer="A", answers=answers, stats={"A": 1}
        )

        # s2's streak was reset to 0
        mock_repo.set_streak.assert_any_call("C1", "s2", 0)
        # s2 received a score update with 0 earned
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
        # s1 also got a positive update
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
        # Leaderboard still includes both
        mock_broadcast.broadcast.assert_any_call(
            "C1",
            "game:leaderboard",
            {
                "class_code": "C1",
                "top_students": [
                    {"name": "Alice", "score": 100, "is_streak": True},
                    {"name": "Bob", "score": 500, "is_streak": False},
                ],
            },
        )


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
