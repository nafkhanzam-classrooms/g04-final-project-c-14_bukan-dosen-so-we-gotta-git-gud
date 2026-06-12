from typing import Any
from unittest.mock import AsyncMock

import pytest
from quiz.application.quiz_service import QuizService
from quiz.interface.quiz_handler import QuizHandler


@pytest.fixture
def mock_service():
    return AsyncMock(spec=QuizService)


@pytest.fixture
def mock_ws_manager():
    mgr = AsyncMock()
    return mgr


@pytest.fixture
def handler(mock_service, mock_ws_manager):
    return QuizHandler(service=mock_service, ws_manager=mock_ws_manager)


# Event notifier helper
async def call_handler(
    handler: QuizHandler, event_type: str, session_id: str, payload: dict[str, Any]
) -> None:
    await handler(event_type, session_id, payload)


@pytest.mark.asyncio
async def test_handle_start_success(handler, mock_service):
    payload = {"class_code": "MATH123", "question_id": "q1", "options": ["A", "B", "C"]}
    await call_handler(handler, "quiz:start", "host1", payload)
    mock_service.start_quiz.assert_called_once_with("host1", "MATH123", "q1", ["A", "B", "C"])


@pytest.mark.asyncio
async def test_handle_start_validation_error(handler, mock_service, mock_ws_manager):
    # Missing 'question_id'
    payload = {"class_code": "MATH123", "options": ["A"]}
    await call_handler(handler, "quiz:start", "host1", payload)
    mock_service.start_quiz.assert_not_called()
    mock_ws_manager.send.assert_called_once()
    args, _ = mock_ws_manager.send.call_args
    assert args[0] == "quiz:error"
    assert args[1] == "host1"
    assert "question_id" in args[2]["message"]


@pytest.mark.asyncio
async def test_answer_quiz_success(handler, mock_service):
    payload = {"class_code": "MATH123", "question_id": "q1", "answer": "B"}
    await call_handler(handler, "quiz:answer", "stu1", payload)
    mock_service.answer_quiz.assert_called_once_with("stu1", "MATH123", "q1", "B")


@pytest.mark.asyncio
async def test_stop_quiz_success(handler, mock_service):
    payload = {"class_code": "MATH123", "question_id": "q1"}
    await call_handler(handler, "quiz:stop", "host1", payload)
    mock_service.stop_quiz.assert_called_once_with("host1", "MATH123", "q1")


@pytest.mark.asyncio
async def test_close_quiz_success(handler, mock_service):
    payload = {"class_code": "MATH123", "question_id": "q1", "correct_answer": "B"}
    await call_handler(handler, "quiz:close", "host1", payload)
    mock_service.close_quiz.assert_called_once_with("host1", "MATH123", "q1", "B")


@pytest.mark.asyncio
async def test_permission_error_triggers_error_message(handler, mock_service, mock_ws_manager):
    mock_service.start_quiz.side_effect = PermissionError("Only host can start a quiz.")
    payload = {"class_code": "MATH123", "question_id": "q1", "options": ["A", "B"]}
    await call_handler(handler, "quiz:start", "not_host", payload)
    mock_ws_manager.send.assert_called_with(
        "quiz:error", "not_host", {"message": "Only host can start a quiz."}
    )


@pytest.mark.asyncio
async def test_value_error_triggers_error_message(handler, mock_service, mock_ws_manager):
    mock_service.answer_quiz.side_effect = ValueError("Quiz is not active.")
    payload = {"class_code": "MATH123", "question_id": "q1", "answer": "A"}
    await call_handler(handler, "quiz:answer", "stu1", payload)
    mock_ws_manager.send.assert_called_with(
        "quiz:error", "stu1", {"message": "Quiz is not active."}
    )


@pytest.mark.asyncio
async def test_unknown_event(handler, mock_service, mock_ws_manager):
    await call_handler(handler, "quiz:unknown", "s1", {})
    mock_service.assert_not_awaited()
    mock_ws_manager.send.assert_called_with(
        "quiz:error", "s1", {"message": "Unknown event 'quiz:unknown'"}
    )


@pytest.mark.asyncio
async def test_internal_exception_returns_generic_error(handler, mock_service, mock_ws_manager):
    mock_service.start_quiz.side_effect = Exception("Boom")
    payload = {"class_code": "MATH123", "question_id": "q1", "options": ["A", "B"]}  # valid
    await call_handler(handler, "quiz:start", "host1", payload)
    mock_ws_manager.send.assert_called_with(
        "quiz:error", "host1", {"message": "Internal server error"}
    )
