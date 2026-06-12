from unittest.mock import AsyncMock, MagicMock

import pytest
from application.message_parser import process_raw_message


@pytest.mark.asyncio
async def test_process_valid_json():
    router = AsyncMock()
    manager = AsyncMock()

    manager.reset_error = MagicMock()
    manager.record_error = MagicMock()

    await process_raw_message('{"event": "test", "data": {"x": 1}}', "sid", router, manager)

    router.dispatch.assert_called_once_with("test", "sid", {"x": 1})


@pytest.mark.asyncio
async def test_process_invalid_json():
    router = AsyncMock()
    manager = AsyncMock()
    manager.record_error = MagicMock(return_value=1)
    manager.reset_error = MagicMock()
    manager.is_tolerance_exceeded = MagicMock(return_value=False)
    manager.max_error_tolerance = 5
    manager.kick = AsyncMock()

    await process_raw_message("{bad json", "sid", router, manager)

    manager.send.assert_called_once_with(
        "error", "sid", {"message": "Invalid JSON format. Warning 1/5"}
    )
    router.dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_process_malformed_json_until_kick():
    router = AsyncMock()
    manager = AsyncMock()
    max_tol = 5
    manager.max_error_tolerance = max_tol

    # Mutable counter
    counter = [0]

    def record_error(session_id: str) -> int:
        counter[0] += 1
        return counter[0]

    def reset_error(session_id: str) -> None:
        counter[0] = 0

    def is_tolerance_exceeded(session_id: str) -> bool:
        return counter[0] >= max_tol

    manager.record_error = MagicMock(side_effect=record_error)
    manager.reset_error = MagicMock(side_effect=reset_error)
    manager.is_tolerance_exceeded = MagicMock(side_effect=is_tolerance_exceeded)
    manager.kick = AsyncMock()

    # Send 5 invalid messages
    for _ in range(5):
        await process_raw_message("{bad", "sess1", router, manager)

    # Only 4 error messages are sent (before the 5th triggers a kick)
    assert manager.send.call_count == 4

    # The last error message should be the 4th warning
    manager.send.assert_any_call("error", "sess1", {"message": "Invalid JSON format. Warning 4/5"})

    # Kick is called exactly once
    manager.kick.assert_called_once_with("sess1", "Too many invalid packets sent.")


@pytest.mark.asyncio
async def test_valid_json_after_errors_resets_counter():
    router = AsyncMock()
    manager = AsyncMock()
    max_tol = 5
    manager.max_error_tolerance = max_tol

    counter = [0]

    def record_error(session_id: str) -> int:
        counter[0] += 1
        return counter[0]

    def reset_error(session_id: str) -> None:
        counter[0] = 0

    def is_tolerance_exceeded(session_id: str) -> bool:
        return counter[0] >= max_tol

    manager.record_error = MagicMock(side_effect=record_error)
    manager.reset_error = MagicMock(side_effect=reset_error)
    manager.is_tolerance_exceeded = MagicMock(side_effect=is_tolerance_exceeded)
    manager.kick = AsyncMock()

    # Cause 3 errors
    for _ in range(3):
        await process_raw_message("bad", "sess1", router, manager)

    # Send a valid message – should reset the counter
    await process_raw_message('{"event": "dummy"}', "sess1", router, manager)
    manager.reset_error.assert_called_once_with("sess1")

    # After reset, 5 new errors should again trigger one kick (after 4 warnings)
    manager.kick.reset_mock()
    for _ in range(5):
        await process_raw_message("{bad", "sess1", router, manager)

    # Only one kick should happen
    manager.kick.assert_called_once_with("sess1", "Too many invalid packets sent.")
