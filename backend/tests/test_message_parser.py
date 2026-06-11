from unittest.mock import AsyncMock

import pytest
from application.message_parser import process_raw_message


@pytest.mark.asyncio
async def test_process_valid_json():
    router = AsyncMock()
    manager = AsyncMock()

    await process_raw_message('{"event": "test", "data": {"x": 1}}', "sid", router, manager)

    router.dispatch.assert_called_once_with("test", "sid", {"x": 1})


@pytest.mark.asyncio
async def test_process_invalid_json():
    router = AsyncMock()
    manager = AsyncMock()

    await process_raw_message("{bad json", "sid", router, manager)

    manager.send.assert_called_once_with("error", "sid", {"message": "Invalid JSON format."})
