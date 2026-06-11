from unittest.mock import AsyncMock

import pytest
from shared.application.room.broadcast import RoomBroadcastService


@pytest.fixture
def mock_registry():
    return AsyncMock()


@pytest.fixture
def mock_ws_manager():
    return AsyncMock()


@pytest.fixture
def broadcast_service(mock_registry, mock_ws_manager):
    return RoomBroadcastService(registry=mock_registry, ws_manager=mock_ws_manager)


@pytest.mark.asyncio
async def test_broadcast_sends_to_all_participants(
    broadcast_service, mock_registry, mock_ws_manager
):
    mock_registry.get_participants.return_value = {"sess1", "sess2"}

    await broadcast_service.broadcast("class1", "slides:changed", {"slide": 3})

    assert mock_ws_manager.send.call_count == 2
    mock_ws_manager.send.assert_any_call("slides:changed", "sess1", {"slide": 3})
    mock_ws_manager.send.assert_any_call("slides:changed", "sess2", {"slide": 3})
