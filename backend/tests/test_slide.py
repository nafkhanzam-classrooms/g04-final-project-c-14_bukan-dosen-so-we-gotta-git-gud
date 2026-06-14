from unittest.mock import AsyncMock

import pytest
from shared.application.room.broadcast import RoomBroadcastService
from shared.domain.redis.event_publisher import EventPublisher
from shared.infrastructure.websocket.manager import WSConnectionManager
from slides.application.slide_service import SlideService
from slides.domain.repository_interface import SlideRepository
from slides.interface.slide_handler import SlideHandler


@pytest.fixture
def mock_event_bus():
    return AsyncMock(spec=EventPublisher)


@pytest.mark.asyncio
async def test_repository_update_current_slide() -> None:
    mock_redis = AsyncMock()
    from slides.repository.slide_repository import SlideRedisRepository

    repo = SlideRedisRepository(redis_client=mock_redis)
    await repo.update_current_slide("XYZ123", 5)

    mock_redis.execute.assert_called_once_with("HSET", "room:XYZ123", "current_slide", "5")


@pytest.mark.asyncio
async def test_repository_get_room_host() -> None:
    mock_redis = AsyncMock()
    mock_redis.execute.return_value = "host_session_999"
    from slides.repository.slide_repository import SlideRedisRepository

    repo = SlideRedisRepository(redis_client=mock_redis)
    host_id = await repo.get_room_host("XYZ123")

    mock_redis.execute.assert_called_once_with("HGET", "room:XYZ123", "host_session_id")
    assert host_id == "host_session_999"


@pytest.mark.asyncio
async def test_repository_get_room_students() -> None:
    mock_redis = AsyncMock()
    mock_redis.execute.return_value = ["student_1", "student_2"]
    from slides.repository.slide_repository import SlideRedisRepository

    repo = SlideRedisRepository(redis_client=mock_redis)
    students = await repo.get_room_students("XYZ123")

    mock_redis.execute.assert_called_once_with("HKEYS", "room:XYZ123:students")
    assert students == ["student_1", "student_2"]


@pytest.mark.asyncio
async def test_service_change_slide_success() -> None:
    mock_repo = AsyncMock(spec=SlideRepository)
    mock_repo.get_room_host.return_value = "host_123"
    mock_repo.get_room_students.return_value = ["student_A", "student_B"]

    service = SlideService(repository=mock_repo)

    await service.change_slide("host_123", "XYZ123", 3)

    mock_repo.update_current_slide.assert_called_once_with("XYZ123", 3)


@pytest.mark.asyncio
async def test_service_change_slide_not_host() -> None:
    mock_repo = AsyncMock(spec=SlideRepository)
    mock_repo.get_room_host.return_value = "host_123"

    service = SlideService(repository=mock_repo)

    with pytest.raises(PermissionError, match="Only Host is allowed to change the slide."):
        await service.change_slide("imposter_456", "XYZ123", 3)

    mock_repo.update_current_slide.assert_not_called()


@pytest.mark.asyncio
async def test_service_change_slide_room_not_found() -> None:
    mock_repo = AsyncMock(spec=SlideRepository)
    mock_repo.get_room_host.return_value = None

    service = SlideService(repository=mock_repo)

    with pytest.raises(ValueError, match="Class not found."):
        await service.change_slide("host_123", "GHOST_ROOM", 3)


@pytest.mark.asyncio
async def test_handler_change_slide_success(mock_event_bus: AsyncMock) -> None:
    mock_service = AsyncMock(spec=SlideService)
    mock_service.change_slide.return_value = ["student_1", "student_2"]

    mock_ws_manager = AsyncMock(spec=WSConnectionManager)
    mock_broadcast_service = AsyncMock(spec=RoomBroadcastService)

    handler = SlideHandler(
        service=mock_service,
        broadcast_service=mock_broadcast_service,
        ws_manager=mock_ws_manager,
        event_bus=mock_event_bus,
    )

    payload = {"class_code": "XYZ123", "slide_number": 4}
    await handler("slides:change", "host_123", payload)

    mock_service.change_slide.assert_called_once_with(
        session_id="host_123", class_code="XYZ123", slide_number=4
    )

    mock_broadcast_service.broadcast.assert_called_once_with(
        class_code="XYZ123",
        event="slides:changed",
        data={"slide_number": 4},
    )

    mock_event_bus.publish.assert_called_once_with(
        "room_events",
        {"event": "room:activity", "class_code": "XYZ123"},
    )

    mock_ws_manager.send.assert_not_called()


@pytest.mark.asyncio
async def test_handler_change_slide_permission_denied(mock_event_bus: AsyncMock) -> None:
    mock_service = AsyncMock(spec=SlideService)
    mock_service.change_slide.side_effect = PermissionError(
        "Only Host is allowed to change the slide."
    )

    mock_ws_manager = AsyncMock(spec=WSConnectionManager)
    mock_broadcast_service = AsyncMock(spec=RoomBroadcastService)

    handler = SlideHandler(
        service=mock_service,
        broadcast_service=mock_broadcast_service,
        ws_manager=mock_ws_manager,
        event_bus=mock_event_bus,
    )

    payload = {"class_code": "XYZ123", "slide_number": 4}
    await handler("slides:change", "hacker_123", payload)

    mock_ws_manager.send.assert_called_once_with(
        "slides:error",
        "hacker_123",
        data={"class_code": "XYZ123", "message": "Only Host is allowed to change the slide."},
    )

    mock_broadcast_service.broadcast.assert_not_called()
    mock_event_bus.publish.assert_not_called()
