import json
from unittest.mock import AsyncMock, patch

import pytest
import websockets
from shared.infrastructure.websocket.manager import WSConnectionManager


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

    old_ws.close.assert_called_once_with(code=4000, reason="Session replaced by a new connection")

    assert manager._connections[session_id] == mock_websocket


@pytest.mark.asyncio
async def test_unregister(manager, mock_websocket):
    session_id = "user_123"
    manager._connections[session_id] = mock_websocket

    await manager.unregister(session_id)

    assert session_id not in manager._connections


@pytest.mark.asyncio
@patch("shared.infrastructure.websocket.manager.WSMessage")
async def test_send_message(mock_ws_message_cls, manager, mock_websocket):
    session_id = "user_123"
    manager._connections[session_id] = mock_websocket

    mock_envelope = mock_ws_message_cls.return_value
    mock_envelope.model_dump_json.return_value = '{"event": "test", "data": {"msg": "hello"}}'

    await manager.send("test", session_id, {"msg": "hello"})

    mock_ws_message_cls.assert_called_once_with(event="test", data={"msg": "hello"})
    mock_websocket.send.assert_called_once_with('{"event": "test", "data": {"msg": "hello"}}')


@pytest.mark.asyncio
async def test_establish_new_session(manager):
    ws = AsyncMock(spec=websockets.ServerConnection)
    # First frame without session_id
    ws.recv.return_value = json.dumps({"data": {"session_id": None}})

    session_id = await manager.establish(ws)

    assert session_id is not None
    assert len(session_id) > 0
    assert session_id in manager._connections
    ws.send.assert_not_called()  # No error send


@pytest.mark.asyncio
async def test_establish_reconnect_existing(manager):
    # Pre-register a session
    old_ws = AsyncMock(spec=websockets.ServerConnection)
    manager._connections["existing_sess"] = old_ws

    # New connection tries to reconnect with same id
    new_ws = AsyncMock(spec=websockets.ServerConnection)
    new_ws.recv.return_value = json.dumps({"data": {"session_id": "existing_sess"}})

    session_id = await manager.establish(new_ws)

    assert session_id == "existing_sess"

    new_ws.send.assert_not_called()

    old_ws.close.assert_called_once_with(code=4000, reason="Session replaced by a new connection")

    assert manager._connections["existing_sess"] == new_ws


@pytest.mark.asyncio
async def test_establish_reconnect_after_disconnect(manager):
    # No previous connection for this id, but client sends it
    new_ws = AsyncMock(spec=websockets.ServerConnection)
    new_ws.recv.return_value = json.dumps({"data": {"session_id": "reconnect_me"}})

    session_id = await manager.establish(new_ws)

    assert session_id == "reconnect_me"
    assert "reconnect_me" in manager._connections
