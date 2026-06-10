from unittest.mock import AsyncMock, patch

import pytest
import websockets
from shared.infrastructure.ws_manager import WSConnectionManager


@pytest.fixture
def manager():
    return WSConnectionManager()


@pytest.fixture
def mock_websocket():
    return AsyncMock(spec=websockets.ServerConnection)


@pytest.mark.asyncio
async def test_register_new_connection(manager, mock_websocket):
    session_id = "user_123"

    await manager.register(session_id, mock_websocket)

    assert session_id in manager._connections
    assert manager._connections[session_id] == mock_websocket


@pytest.mark.asyncio
async def test_register_duplicate_login(manager, mock_websocket):
    session_id = "user_123"
    old_ws = AsyncMock(spec=websockets.ServerConnection)

    await manager.register(session_id, old_ws)
    await manager.register(session_id, mock_websocket)

    mock_websocket.send.assert_called_once_with(
        "ERROR|DUPLICATE_LOGIN| Your account is logged in another location"
    )
    mock_websocket.close.assert_called_once_with(
        code=1008, reason="Duplicate Login - active session exists"
    )

    old_ws.send.assert_not_called()
    old_ws.close.assert_not_called()

    assert manager._connections[session_id] == old_ws


@pytest.mark.asyncio
async def test_unregister(manager, mock_websocket):
    session_id = "user_123"
    manager._connections[session_id] = mock_websocket

    await manager.unregister(session_id)

    assert session_id not in manager._connections


@pytest.mark.asyncio
@patch("shared.infrastructure.ws_manager.WSMessage")
async def test_send_message(mock_ws_message_cls, manager, mock_websocket):
    session_id = "user_123"
    manager._connections[session_id] = mock_websocket

    # Mock behavior untuk WSMessage
    mock_envelope = mock_ws_message_cls.return_value
    mock_envelope.model_dump_json.return_value = '{"event": "test", "data": {"msg": "hello"}}'

    await manager.send("test", session_id, {"msg": "hello"})

    mock_ws_message_cls.assert_called_once_with(event="test", data={"msg": "hello"})
    mock_websocket.send.assert_called_once_with('{"event": "test", "data": {"msg": "hello"}}')


@pytest.mark.asyncio
@patch("shared.infrastructure.ws_manager.WSMessage")
async def test_broadcast_cleans_up_closed_connections(mock_ws_message_cls, manager):
    ws_aktif = AsyncMock(spec=websockets.ServerConnection)
    ws_putus = AsyncMock(spec=websockets.ServerConnection)

    ws_putus.send.side_effect = websockets.ConnectionClosed(None, None)

    manager._connections["user_aktif"] = ws_aktif
    manager._connections["user_putus"] = ws_putus

    mock_envelope = mock_ws_message_cls.return_value
    mock_envelope.model_dump_json.return_value = '{"event": "bcast"}'

    await manager.broadcast("bcast", {"content": "data"})

    ws_aktif.send.assert_called_once()
    assert "user_aktif" in manager._connections
    assert "user_putus" not in manager._connections
