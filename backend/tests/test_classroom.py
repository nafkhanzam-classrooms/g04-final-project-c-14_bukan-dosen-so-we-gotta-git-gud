from unittest.mock import AsyncMock

import pytest
from classroom.application.classroom_service import ClassroomService
from classroom.domain.classroom import StudentState
from classroom.interface.classroom_handler import ClassroomHandler
from classroom.repository.classroom_repository import ClassroomRedisRepository
from gamification.application.gamification_service import GamificationService
from quiz.application.quiz_service import QuizService
from shared.application.room.broadcast import RoomBroadcastService
from shared.domain.room.registry import RoomRegistry
from shared.infrastructure.websocket.manager import WSConnectionManager


# Fixtures
@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def redis_repository(mock_redis):
    return ClassroomRedisRepository(redis_client=mock_redis)


@pytest.fixture
def mock_repository():
    return AsyncMock(spec=ClassroomRedisRepository)


@pytest.fixture
def mock_ws_manager():
    return AsyncMock(spec=WSConnectionManager)


@pytest.fixture
def mock_room_registry():
    return AsyncMock(spec=RoomRegistry)


@pytest.fixture
def mock_broadcast_service():
    return AsyncMock(spec=RoomBroadcastService)


@pytest.fixture
def mock_gamification_service():
    return AsyncMock(spec=GamificationService)


@pytest.fixture
def mock_quiz_service():
    return AsyncMock(spec=QuizService)


@pytest.fixture
def classroom_service(mock_repository):
    return ClassroomService(repository=mock_repository)


@pytest.fixture
def classroom_handler(
    classroom_service,
    mock_ws_manager,
    mock_room_registry,
    mock_broadcast_service,
    mock_gamification_service,
    mock_quiz_service,
):
    return ClassroomHandler(
        service=classroom_service,
        ws_manager=mock_ws_manager,
        room_registry=mock_room_registry,
        broadcast_service=mock_broadcast_service,
        gamification_service=mock_gamification_service,
        quiz_service=mock_quiz_service,
    )


# ClassroomService tests
@pytest.mark.asyncio
async def test_create_room_success(classroom_service, mock_repository):
    mock_repository.get_room.return_value = None

    await classroom_service.create_room(host_id="host_123", class_code="BIOL101")

    mock_repository.get_room.assert_called_once_with("BIOL101")
    mock_repository.save_room.assert_called_once_with("BIOL101", "host_123", 1800)


@pytest.mark.asyncio
async def test_create_room_duplicate_code_raises_error(classroom_service, mock_repository):
    mock_repository.get_room.return_value = {"host_session_id": "other_host"}

    with pytest.raises(ValueError, match="Class code is already in use."):
        await classroom_service.create_room(host_id="host_123", class_code="BIOL101")

    mock_repository.save_room.assert_not_called()


@pytest.mark.asyncio
async def test_join_room_success(classroom_service, mock_repository):
    mock_repository.get_room.return_value = {"host_session_id": "host_123"}

    student = await classroom_service.join_room(
        student_id="std_99", student_name="Budi", class_code="BIOL101"
    )

    assert isinstance(student, StudentState)
    assert student.name == "Budi"
    assert student.is_online is True

    mock_repository.add_student.assert_called_once_with("BIOL101", "std_99", student)


@pytest.mark.asyncio
async def test_join_room_not_found_raises_error(classroom_service, mock_repository):
    mock_repository.get_room.return_value = None

    with pytest.raises(ValueError, match="Class not found."):
        await classroom_service.join_room(
            student_id="std_99", student_name="Budi", class_code="KOSONG"
        )

    mock_repository.add_student.assert_not_called()


@pytest.mark.asyncio
async def test_set_total_slides_success(classroom_service, mock_repository):
    mock_repository.get_room.return_value = {"host_session_id": "host_1"}

    result = await classroom_service.set_total_slides("BIOL101", 10)

    assert result is True
    mock_repository.update_total_slides.assert_called_once_with("BIOL101", 10)


@pytest.mark.asyncio
async def test_set_total_slides_room_not_found(classroom_service, mock_repository):
    mock_repository.get_room.return_value = None

    result = await classroom_service.set_total_slides("GHOST", 5)

    assert result is False
    mock_repository.update_total_slides.assert_not_called()


@pytest.mark.asyncio
async def test_verify_host_success(classroom_service, mock_repository):
    mock_repository.get_room.return_value = {"host_session_id": "real_host"}
    await classroom_service.verify_host("real_host", "MATH123")
    mock_repository.get_room.assert_called_once_with("MATH123")


@pytest.mark.asyncio
async def test_verify_host_not_found(classroom_service, mock_repository):
    mock_repository.get_room.return_value = None
    with pytest.raises(ValueError, match="Class not found"):
        await classroom_service.verify_host("host_1", "MATH123")


@pytest.mark.asyncio
async def test_verify_host_permission_error(classroom_service, mock_repository):
    mock_repository.get_room.return_value = {"host_session_id": "real_host"}
    with pytest.raises(PermissionError, match="Only the host is authorized"):
        await classroom_service.verify_host("imposter_session", "MATH123")


@pytest.mark.asyncio
async def test_delete_room_success(classroom_service, mock_repository):
    await classroom_service.delete_room("MATH123")
    mock_repository.delete_room_data.assert_called_once_with("MATH123")


# ClassroomHandler tests
@pytest.mark.asyncio
async def test_handler_create_classroom_success(classroom_handler, mock_ws_manager):
    classroom_handler.service.create_room = AsyncMock()

    await classroom_handler("classroom:create", "host_1", {"class_code": "MATH123"})

    classroom_handler.service.create_room.assert_called_once_with(
        host_id="host_1", class_code="MATH123"
    )
    mock_ws_manager.send.assert_called_once_with(
        event="classroom:created",
        session_id="host_1",
        data={"class_code": "MATH123"},
    )


@pytest.mark.asyncio
async def test_handler_create_classroom_error(classroom_handler, mock_ws_manager):
    classroom_handler.service.create_room = AsyncMock(
        side_effect=ValueError("Class code is already in use.")
    )

    await classroom_handler("classroom:create", "host_1", {"class_code": "MATH123"})

    mock_ws_manager.send.assert_called_once_with(
        event="classroom:error",
        session_id="host_1",
        data={"class_code": None, "message": "Class code is already in use."},
    )


@pytest.mark.asyncio
async def test_handler_join_classroom_success(
    classroom_handler, mock_ws_manager, mock_room_registry
):
    await classroom_handler(
        "classroom:join", "student_1", {"class_code": "MATH123", "student_name": "Andi"}
    )

    mock_room_registry.add_participant.assert_called_once_with("MATH123", "student_1")
    mock_ws_manager.send.assert_called_once_with(
        event="classroom:joined",
        session_id="student_1",
        data={"class_code": "MATH123", "student_name": "Andi"},
    )


@pytest.mark.asyncio
async def test_handler_unknown_event(classroom_handler, mock_ws_manager):
    await classroom_handler("classroom:ghost_event", "user_1", {})

    mock_ws_manager.send.assert_called_once_with(
        event="classroom:error",
        session_id="user_1",
        data={"message": "Unknown event 'classroom:ghost_event'."},
    )


@pytest.mark.asyncio
async def test_handler_end_classroom_success(
    classroom_handler,
    mock_ws_manager,
    mock_broadcast_service,
    mock_gamification_service,
    mock_quiz_service,
    mock_room_registry,
):
    session_id = "host_session"
    class_code = "MATH123"
    fake_leaderboard = [
        {"name": "Budi", "score": 1250, "is_streak": True},
        {"name": "Andi", "score": 1100, "is_streak": False},
    ]

    classroom_handler.service.verify_host = AsyncMock()
    classroom_handler.service.delete_room = AsyncMock()
    mock_gamification_service.get_formatted_leaderboard.return_value = fake_leaderboard

    await classroom_handler("classroom:end", session_id, {"class_code": class_code})

    classroom_handler.service.verify_host.assert_called_once_with(session_id, class_code)
    mock_gamification_service.get_formatted_leaderboard.assert_called_once_with(class_code)
    mock_broadcast_service.broadcast.assert_called_once_with(
        class_code=class_code,
        event="classroom:ended",
        data={"class_code": class_code, "top_students": fake_leaderboard},
    )
    mock_gamification_service.cleanup_gamification_data.assert_called_once_with(class_code)
    mock_quiz_service.cleanup_quiz_data.assert_called_once_with(class_code)
    classroom_handler.service.delete_room.assert_called_once_with(class_code)
    mock_room_registry.remove_all_participants.assert_called_once_with(class_code)


@pytest.mark.asyncio
async def test_handler_end_classroom_unauthorized(classroom_handler, mock_ws_manager):
    classroom_handler.service.verify_host = AsyncMock(
        side_effect=PermissionError("Only the host is authorized.")
    )
    await classroom_handler("classroom:end", "imposter", {"class_code": "MATH123"})
    mock_ws_manager.send.assert_called_once_with(
        event="classroom:error",
        session_id="imposter",
        data={"class_code": None, "message": "Only the host is authorized."},
    )


# ClassroomRedisRepository tests
@pytest.mark.asyncio
async def test_save_room(redis_repository, mock_redis):
    class_code = "BIO101"
    host_id = "host_abc"

    await redis_repository.save_room(class_code, host_id, ttl=1800)

    mock_redis.hset.assert_called_once_with(
        "room:BIO101",
        mapping={"host_session_id": host_id, "current_slide": "1", "total_slides": "0"},
    )


@pytest.mark.asyncio
async def test_get_room_found(redis_repository, mock_redis):
    mock_redis.hgetall.return_value = {"host_session_id": "host_abc", "current_slide": "2"}

    room_data = await redis_repository.get_room("BIO101")

    mock_redis.hgetall.assert_called_once_with("room:BIO101")
    assert room_data == {"host_session_id": "host_abc", "current_slide": "2"}


@pytest.mark.asyncio
async def test_get_room_not_found(redis_repository, mock_redis):
    mock_redis.hgetall.return_value = {}

    room_data = await redis_repository.get_room("KOSONG")

    assert room_data is None


@pytest.mark.asyncio
async def test_update_total_slides(redis_repository, mock_redis):
    await redis_repository.update_total_slides("BIO101", 12)
    mock_redis.hset.assert_called_once_with("room:BIO101", "total_slides", "12")


@pytest.mark.asyncio
async def test_add_student(redis_repository, mock_redis):
    student = StudentState(name="Budi", is_online=True, stars=5)
    await redis_repository.add_student("BIO101", "std_1", student)

    mock_redis.hset.assert_called_once_with(
        "room:BIO101:students", "std_1", student.model_dump_json()
    )


@pytest.mark.asyncio
async def test_classroom_delete_room_data(redis_repository, mock_redis):
    await redis_repository.delete_room_data("MATH123")
    mock_redis.delete.assert_called_once_with("room:MATH123", "room:MATH123:students")
