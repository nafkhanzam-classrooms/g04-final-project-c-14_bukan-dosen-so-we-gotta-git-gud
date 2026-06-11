import json
from unittest.mock import AsyncMock, patch

import pytest
import websockets
from application.message_parser import process_raw_message


# process_raw_message tests
@pytest.mark.asyncio
async def test_process_valid_json_dispatches():
    router = AsyncMock()
    manager = AsyncMock()
    payload = {"event": "classroom:create", "data": {"class_code": "X"}}

    await process_raw_message(json.dumps(payload), "sess1", router, manager)

    router.dispatch.assert_called_once_with("classroom:create", "sess1", {"class_code": "X"})
    manager.send.assert_not_called()


@pytest.mark.asyncio
async def test_process_bytes_message():
    router = AsyncMock()
    manager = AsyncMock()
    payload = {"event": "test", "data": {}}

    await process_raw_message(json.dumps(payload).encode(), "sess1", router, manager)

    router.dispatch.assert_called_once_with("test", "sess1", {})


@pytest.mark.asyncio
async def test_process_invalid_json_sends_error():
    router = AsyncMock()
    manager = AsyncMock()

    await process_raw_message("not json", "sess1", router, manager)

    manager.send.assert_called_once_with("error", "sess1", {"message": "Invalid JSON format."})
    router.dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_process_no_event_does_nothing():
    router = AsyncMock()
    manager = AsyncMock()

    await process_raw_message('{"data": {}}', "sess1", router, manager)

    router.dispatch.assert_not_called()
    manager.send.assert_not_called()


# main handler loop tests (using patched Application)
@pytest.mark.asyncio
@patch("application.main.Application")
@patch("application.main.process_raw_message", new_callable=AsyncMock)
async def test_handler_new_session_and_message_loop(mock_parser, mockapp):
    # Setup mocked application
    app_instance = mockapp.return_value
    ws_manager = app_instance.ws_manager
    ws_manager.establish = AsyncMock(return_value="new_sess")
    ws_manager.send = AsyncMock()
    ws_manager.unregister = AsyncMock()
    ws_router = app_instance.ws_router
    room_registry = app_instance.room_registry
    room_registry.remove_participant_by_session = AsyncMock()

    # Simulate a websocket connection
    ws = AsyncMock(spec=websockets.ServerConnection)
    # First recv returns a valid session_id (reconnect/ new session response ignored here)
    ws.recv.return_value = json.dumps({"data": {"session_id": None}})
    # Simulate one incoming message then connection closed
    ws.__aiter__.return_value = [json.dumps({"event": "dummy", "data": {}})]
    ws.send = AsyncMock()

    async def handler(websocket: websockets.ServerConnection) -> None:
        session_id = await ws_manager.establish(websocket)
        if not session_id:
            return
        await ws_manager.send("connection:assigned", session_id, {"session_id": session_id})
        try:
            async for raw_msg in websocket:
                await mock_parser(raw_msg, session_id, ws_router, ws_manager)
        except websockets.ConnectionClosed:
            pass
        finally:
            await ws_manager.unregister(session_id)
            await room_registry.remove_participant_by_session(session_id)

    await handler(ws)

    ws_manager.establish.assert_called_once_with(ws)
    ws_manager.send.assert_any_call("connection:assigned", "new_sess", {"session_id": "new_sess"})
    mock_parser.assert_called_once_with(
        json.dumps({"event": "dummy", "data": {}}), "new_sess", ws_router, ws_manager
    )
    ws_manager.unregister.assert_called_once_with("new_sess")
    room_registry.remove_participant_by_session.assert_called_once_with("new_sess")
