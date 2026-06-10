from unittest.mock import AsyncMock

import pytest
from classroom.application.classroom_service import ClassroomService
from classroom.domain.classroom import StudentState
from classroom.interface.classroom_handler import ClassroomHandler
from classroom.repository.classroom_repository import ClassroomRedisRepository
from shared.infrastructure.websocket.manager import WSConnectionManager


# Fixtures
@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.hset = AsyncMock()
    mock.hgetall = AsyncMock()
    return mock


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
def classroom_service(mock_repository):
    return ClassroomService(repository=mock_repository)


@pytest.fixture
def classroom_handler(classroom_service, mock_ws_manager):
    return ClassroomHandler(service=classroom_service, ws_manager=mock_ws_manager)


# ClassroomService tests
@pytest.mark.asyncio
async def test_create_room_success(classroom_service, mock_repository):
    mock_repository.get_room.return_value = None

    await classroom_service.create_room(host_id="host_123", class_code="BIOL101")

    mock_repository.get_room.assert_called_once_with("BIOL101")
    mock_repository.save_room.assert_called_once_with("BIOL101", "host_123")


@pytest.mark.asyncio
async def test_create_room_duplicate_code_raises_error(classroom_service, mock_repository):
    mock_repository.get_room.return_value = {"host_session_id": "other_host"}

    with pytest.raises(ValueError, match="Kode kelas sudah digunakan."):
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

    with pytest.raises(ValueError, match="Kelas tidak ditemukan."):
        await classroom_service.join_room(
            student_id="std_99", student_name="Budi", class_code="KOSONG"
        )

    mock_repository.add_student.assert_not_called()


# ClassroomHandler tests
@pytest.mark.asyncio
async def test_handler_create_classroom_success(
    classroom_handler, mock_ws_manager, mock_repository
):
    classroom_handler.service.create_room = AsyncMock()

    payload = {"class_code": "MATH123"}
    await classroom_handler(event_type="classroom:create", session_id="host_1", payload=payload)

    classroom_handler.service.create_room.assert_called_once_with(
        host_id="host_1", class_code="MATH123"
    )

    mock_ws_manager.send.assert_called_once_with(
        event="classroom:created",
        session_id="host_1",
        data={"class_code": "MATH123", "status": "success"},
    )


@pytest.mark.asyncio
async def test_handler_create_classroom_error(classroom_handler, mock_ws_manager):
    classroom_handler.service.create_room = AsyncMock(
        side_effect=ValueError("Kode kelas sudah digunakan.")
    )

    payload = {"class_code": "MATH123"}
    await classroom_handler(event_type="classroom:create", session_id="host_1", payload=payload)

    mock_ws_manager.send.assert_called_once_with(
        event="classroom:error",
        session_id="host_1",
        data={"message": "Kode kelas sudah digunakan."},
    )


@pytest.mark.asyncio
async def test_handler_join_classroom_success(classroom_handler, mock_ws_manager):
    expected_student = StudentState(name="Andi", is_online=True, stars=0)
    classroom_handler.service.join_room = AsyncMock(return_value=expected_student)

    payload = {"class_code": "MATH123", "student_name": "Andi"}
    await classroom_handler(event_type="classroom:join", session_id="student_1", payload=payload)

    classroom_handler.service.join_room.assert_called_once_with(
        student_id="student_1", student_name="Andi", class_code="MATH123"
    )
    mock_ws_manager.send.assert_called_once_with(
        event="classroom:joined",
        session_id="student_1",
        data={"class_code": "MATH123", "student": expected_student.model_dump()},
    )


@pytest.mark.asyncio
async def test_handler_unknown_event(classroom_handler, mock_ws_manager):
    await classroom_handler(event_type="classroom:ghost_event", session_id="user_1", payload={})

    mock_ws_manager.send.assert_called_once_with(
        event="classroom:error",
        session_id="user_1",
        data={"message": "Unknown event 'classroom:ghost_event'."},
    )


# ClassroomRedisRepository tests
@pytest.mark.asyncio
async def test_save_room(redis_repository, mock_redis):
    class_code = "BIO101"
    host_id = "host_abc"

    await redis_repository.save_room(class_code, host_id)

    mock_redis.hset.assert_called_once_with(
        "room:BIO101", mapping={"host_session_id": host_id, "current_slide": "1"}
    )


@pytest.mark.asyncio
async def test_get_room_found(redis_repository, mock_redis):
    class_code = "BIO101"
    mock_redis.hgetall.return_value = {"host_session_id": "host_abc", "current_slide": "2"}

    room_data = await redis_repository.get_room(class_code)

    mock_redis.hgetall.assert_called_once_with("room:BIO101")
    assert room_data == {"host_session_id": "host_abc", "current_slide": "2"}


@pytest.mark.asyncio
async def test_get_room_not_found(redis_repository, mock_redis):
    class_code = "KOSONG"
    mock_redis.hgetall.return_value = {}

    room_data = await redis_repository.get_room(class_code)

    assert room_data is None


@pytest.mark.asyncio
async def test_add_student(redis_repository, mock_redis):
    class_code = "BIO101"
    session_id = "std_1"
    student = StudentState(name="Budi", is_online=True, stars=5)

    await redis_repository.add_student(class_code, session_id, student)

    mock_redis.hset.assert_called_once_with(
        "room:BIO101:students", session_id, student.model_dump_json()
    )
