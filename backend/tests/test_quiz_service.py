from unittest.mock import AsyncMock

import pytest
from gamification.application.gamification_service import GamificationService
from quiz.application.quiz_service import QuizService
from quiz.domain.host_provider import HostProvider
from quiz.domain.repository_interface import QuizRepository
from shared.application.room.broadcast import RoomBroadcastService


@pytest.fixture
def mock_quiz_repo():
    return AsyncMock(spec=QuizRepository)


@pytest.fixture
def mock_host_provider():
    return AsyncMock(spec=HostProvider)


@pytest.fixture
def mock_broadcast():
    return AsyncMock(spec=RoomBroadcastService)


@pytest.fixture
def mock_gamification():
    return AsyncMock(spec=GamificationService)


@pytest.fixture
def service(mock_quiz_repo, mock_host_provider, mock_broadcast, mock_gamification):
    return QuizService(
        quiz_repo=mock_quiz_repo,
        host_provider=mock_host_provider,
        broadcast=mock_broadcast,
        gamification=mock_gamification,
    )


@pytest.mark.asyncio
async def test_start_quiz_success(service, mock_quiz_repo, mock_host_provider, mock_broadcast):
    session_id = "host123"
    class_code = "MATH123"
    question_id = "q1"
    options = ["A", "B", "C"]

    mock_host_provider.get_host.return_value = session_id
    mock_quiz_repo.is_active.return_value = False

    await service.start_quiz(session_id, class_code, question_id, options)

    mock_quiz_repo.start_quiz.assert_called_once_with(class_code, question_id, options)
    mock_broadcast.broadcast.assert_called_once_with(
        class_code=class_code,
        event="quiz:started",
        data={
            "class_code": class_code,
            "question_id": question_id,
            "options": options,
        },
    )


@pytest.mark.asyncio
async def test_start_quiz_unauthorized(service, mock_host_provider):
    mock_host_provider.get_host.return_value = "other_host"
    with pytest.raises(PermissionError, match="Only host"):
        await service.start_quiz("session_x", "MATH123", "q1", ["A"])


@pytest.mark.asyncio
async def test_start_quiz_already_active(service, mock_host_provider, mock_quiz_repo):
    mock_host_provider.get_host.return_value = "host1"
    mock_quiz_repo.is_active.return_value = True
    with pytest.raises(ValueError, match="already active"):
        await service.start_quiz("host1", "MATH123", "q1", ["A"])


@pytest.mark.asyncio
async def test_answer_quiz_success(service, mock_quiz_repo, mock_broadcast):
    class_code = "MATH123"
    question_id = "q1"
    student_id = "stu1"
    answer = "B"

    mock_quiz_repo.is_active.return_value = True
    mock_quiz_repo.add_answer.return_value = True
    mock_quiz_repo.get_answers.return_value = {"stu1": "B"}

    await service.answer_quiz(student_id, class_code, question_id, answer)

    mock_quiz_repo.add_answer.assert_called_once_with(class_code, question_id, student_id, answer)
    mock_broadcast.broadcast.assert_called_once_with(
        class_code=class_code,
        event="quiz:answer_received",
        data={
            "class_code": class_code,
            "question_id": question_id,
            "total_answered": 1,
        },
    )


@pytest.mark.asyncio
async def test_answer_quiz_inactive(service, mock_quiz_repo):
    mock_quiz_repo.is_active.return_value = False
    with pytest.raises(ValueError, match="not active"):
        await service.answer_quiz("stu1", "MATH123", "q1", "A")


@pytest.mark.asyncio
async def test_answer_quiz_duplicate_ignored(service, mock_quiz_repo, mock_broadcast):
    mock_quiz_repo.is_active.return_value = True
    mock_quiz_repo.add_answer.return_value = False
    mock_quiz_repo.get_answers.return_value = {"stu1": "B"}

    await service.answer_quiz("stu1", "MATH123", "q1", "C")

    mock_quiz_repo.add_answer.assert_called_once_with("MATH123", "q1", "stu1", "C")
    mock_broadcast.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_stop_quiz_success(service, mock_host_provider, mock_quiz_repo, mock_broadcast):
    session_id = "host1"
    class_code = "MATH123"
    question_id = "q1"

    mock_host_provider.get_host.return_value = session_id

    await service.stop_quiz(session_id, class_code, question_id)

    mock_quiz_repo.stop_quiz.assert_called_once_with(class_code, question_id)
    mock_broadcast.broadcast.assert_called_once_with(
        class_code=class_code,
        event="quiz:stopped",
        data={
            "class_code": class_code,
            "question_id": question_id,
        },
    )


@pytest.mark.asyncio
async def test_stop_quiz_unauthorized(service, mock_host_provider):
    mock_host_provider.get_host.return_value = "other"
    with pytest.raises(PermissionError, match="Only host"):
        await service.stop_quiz("not_host", "MATH123", "q1")


@pytest.mark.asyncio
async def test_close_quiz_delegates_to_gamification_and_cleans_up(
    service, mock_host_provider, mock_quiz_repo, mock_broadcast, mock_gamification
):
    """close_quiz now hands off to gamification and no longer broadcasts quiz:closed directly."""
    session_id = "host1"
    class_code = "MATH123"
    question_id = "q1"
    correct_answer = "B"

    mock_host_provider.get_host.return_value = session_id
    mock_quiz_repo.get_answers.return_value = {"s1": "A", "s2": "B", "s3": "B"}

    await service.close_quiz(session_id, class_code, question_id, correct_answer)

    # Verify gamification was called with correct arguments
    expected_stats = {"A": 1, "B": 2}
    mock_gamification.process_quiz_close.assert_called_once_with(
        class_code=class_code,
        question_id=question_id,
        correct_answer=correct_answer,
        answers={"s1": "A", "s2": "B", "s3": "B"},
        stats=expected_stats,
    )
    # Quiz data is deleted
    mock_quiz_repo.close_quiz.assert_called_once_with(class_code, question_id, correct_answer)
    # No direct broadcast of quiz:closed from QuizService
    mock_broadcast.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_close_quiz_unauthorized(service, mock_host_provider):
    mock_host_provider.get_host.return_value = "other"
    with pytest.raises(PermissionError, match="Only host"):
        await service.close_quiz("not_host", "MATH123", "q1", "B")


@pytest.mark.asyncio
async def test_quiz_delete_all_class_data():
    from quiz.repository.quiz_repository import QuizRedisRepository

    mock_redis = AsyncMock()
    repo = QuizRedisRepository(mock_redis)

    mock_redis.scan.side_effect = [
        (10, [b"quiz:MATH123:q1", b"quiz:MATH123:q1:answers"]),
        (0, [b"quiz:MATH123:q2"]),
    ]

    await repo.delete_all_class_data("MATH123")

    assert mock_redis.scan.call_count == 2
    mock_redis.delete.assert_any_call(b"quiz:MATH123:q1", b"quiz:MATH123:q1:answers")
    mock_redis.delete.assert_any_call(b"quiz:MATH123:q2")
