import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from shared.infrastructure.redis.event_bus import RedisEventBus


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.publish = AsyncMock()
    return redis


@pytest.fixture
def event_bus(mock_redis):
    return RedisEventBus(redis_client=mock_redis)


@pytest.mark.asyncio
async def test_publish(event_bus, mock_redis):
    msg = {"event": "slides:ready", "data": {"total_slides": 5}}
    await event_bus.publish("room_events", msg)

    mock_redis.publish.assert_called_once_with("room_events", json.dumps(msg))


@pytest.mark.asyncio
async def test_subscribe_and_handle_message(event_bus, mock_redis):
    # Setup pubsub mock
    pubsub = AsyncMock()
    mock_redis.pubsub.return_value = pubsub
    pubsub.subscribe = AsyncMock()
    # Simulate one message then stop
    pubsub.listen = MagicMock()
    pubsub.listen.return_value = [
        {"type": "message", "data": '{"event": "test", "data": {"key": "val"}}'},
    ]

    handler = AsyncMock()

    # Because the subscribe method runs an infinite loop, we need to make it stop after first message
    # We'll mock the listen generator to raise StopAsyncIteration after one message
    async def mock_listen():
        yield {"type": "message", "data": '{"event": "test", "data": {"key": "val"}}'}

    pubsub.listen = mock_listen

    await event_bus.subscribe("room_events", handler)

    pubsub.subscribe.assert_called_once_with("room_events")
    handler.assert_called_once_with({"event": "test", "data": {"key": "val"}})
