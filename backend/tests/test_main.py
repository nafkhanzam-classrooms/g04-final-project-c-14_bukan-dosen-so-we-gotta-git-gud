import json
from unittest.mock import AsyncMock, patch

import pytest
from application.main import handle_connection


@pytest.fixture
def mock_websocket():
    ws = AsyncMock()
    # Secara default loop 'async for message in websocket' langsung selesai
    ws.__aiter__.return_value = []
    return ws


@pytest.mark.asyncio
@patch("application.main.ws_manager")
@patch("application.main.ws_router")
async def test_handle_connection_new_session(mock_router, mock_manager, mock_websocket):
    # Setup semua method pendukung ws_manager sebagai AsyncMock
    mock_manager.register = AsyncMock()
    mock_manager.send = AsyncMock()
    mock_manager.unregister = AsyncMock()

    # Bypass pengecekan duplicate login agar tidak return early
    mock_manager._connections.__contains__.return_value = True

    # First frame meminta session baru (session_id = None)
    mock_websocket.recv.return_value = json.dumps(
        {"event": "connection:init", "data": {"session_id": None}}
    )

    await handle_connection(mock_websocket)

    # Pastikan register dipanggil dan mendapatkan session_id hasil generate server
    mock_manager.register.assert_called_once()
    generated_session_id = mock_manager.register.call_args[0][0]
    assert len(generated_session_id) > 0

    # Pastikan server mengirim balik token via event 'connection:assigned'
    mock_manager.send.assert_called_once_with(
        event="connection:assigned",
        session_id=generated_session_id,
        data={"session_id": generated_session_id},
    )
    mock_manager.unregister.assert_called_once_with(generated_session_id)


@pytest.mark.asyncio
@patch("application.main.ws_manager")
@patch("application.main.ws_router")
async def test_handle_connection_invalid_first_frame(mock_router, mock_manager, mock_websocket):
    mock_manager.register = AsyncMock()
    mock_manager.send = AsyncMock()
    mock_manager.unregister = AsyncMock()
    mock_manager._connections.__contains__.return_value = True

    # First frame berupa json rusak / invalid
    mock_websocket.recv.return_value = "BUKAN_JSON_VALID"

    await handle_connection(mock_websocket)

    # Sesuai logika main.py, jika rusak maka fallback menjadi penanganan sesi baru
    mock_manager.register.assert_called_once()
    generated_session_id = mock_manager.register.call_args[0][0]

    mock_manager.send.assert_called_once_with(
        event="connection:assigned",
        session_id=generated_session_id,
        data={"session_id": generated_session_id},
    )


@pytest.mark.asyncio
@patch("application.main.ws_manager")
@patch("application.main.ws_router")
async def test_handle_connection_dispatch_loop(mock_router, mock_manager, mock_websocket):
    mock_manager.register = AsyncMock()
    mock_manager.send = AsyncMock()
    mock_manager.unregister = AsyncMock()
    mock_router.dispatch = AsyncMock()
    mock_manager._connections.__contains__.return_value = True

    # First frame membawa session_id lama (reconnect)
    mock_websocket.recv.return_value = json.dumps(
        {"event": "connection:init", "data": {"session_id": "user_tetap"}}
    )

    # Simulasikan ada 1 pesan masuk di dalam loop iterasi brikutnya
    mock_websocket.__aiter__.return_value = [
        json.dumps({"event": "classroom:create", "data": {"class_code": "BIO1"}})
    ]

    await handle_connection(mock_websocket)

    # Memastikan router berhasil meneruskan event ke handler yang tepat
    mock_router.dispatch.assert_called_once_with(
        "classroom:create", "user_tetap", {"class_code": "BIO1"}
    )
