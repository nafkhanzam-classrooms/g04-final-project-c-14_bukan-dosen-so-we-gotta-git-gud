from unittest.mock import AsyncMock

import pytest
from application.event_handlers import RoomEventHandler


@pytest.fixture
def mock_classroom_service():
    return AsyncMock()


@pytest.fixture
def mock_broadcast_service():
    return AsyncMock()


@pytest.fixture
def event_handler(mock_classroom_service, mock_broadcast_service):
    return RoomEventHandler(mock_classroom_service, mock_broadcast_service)


@pytest.mark.asyncio
async def test_slides_ready_success(event_handler, mock_classroom_service, mock_broadcast_service):
    mock_classroom_service.set_total_slides.return_value = True

    event = {
        "event": "slides:ready",
        "class_code": "BIO101",
        "data": {"total_slides": 10},
    }

    await event_handler(event)

    mock_classroom_service.set_total_slides.assert_called_once_with("BIO101", 10)
    mock_broadcast_service.broadcast.assert_called_once_with(
        class_code="BIO101",
        event="slides:ready",
        data={"total_slides": 10},
    )


@pytest.mark.asyncio
async def test_slides_ready_set_fails_no_broadcast(
    event_handler, mock_classroom_service, mock_broadcast_service
):
    mock_classroom_service.set_total_slides.return_value = False

    event = {
        "event": "slides:ready",
        "class_code": "BIO101",
        "data": {"total_slides": 10},
    }

    await event_handler(event)

    mock_classroom_service.set_total_slides.assert_called_once_with("BIO101", 10)
    mock_broadcast_service.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_event_ignored(event_handler, mock_classroom_service, mock_broadcast_service):
    await event_handler({"event": "unknown:stuff"})

    mock_classroom_service.set_total_slides.assert_not_called()
    mock_broadcast_service.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_missing_class_code_or_total_slides(
    event_handler, mock_classroom_service, mock_broadcast_service
):
    await event_handler({"event": "slides:ready", "class_code": "BIO101"})  # no data.total_slides
    await event_handler({"event": "slides:ready", "data": {"total_slides": 5}})  # no class_code

    mock_classroom_service.set_total_slides.assert_not_called()
    mock_broadcast_service.broadcast.assert_not_called()
