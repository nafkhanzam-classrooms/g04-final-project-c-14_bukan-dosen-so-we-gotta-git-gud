from unittest.mock import AsyncMock

import pytest
from shared.infrastructure.websocket.router import WSEventRouter


@pytest.fixture
def router():
    return WSEventRouter()


@pytest.mark.asyncio
async def test_register_and_dispatch(router):
    handler = AsyncMock()
    router.register("classroom", handler)

    await router.dispatch("classroom:create", "sess1", {"code": "X"})

    handler.assert_called_once_with("classroom:create", "sess1", {"code": "X"})


@pytest.mark.asyncio
async def test_dispatch_unknown_prefix_no_error(router):
    # Should not call any handler, just log warning
    await router.dispatch("ghost:event", "sess1", {})
    # No assertion needed, just ensure no exception
