import asyncio
import json
from typing import Any

import pytest
from shared.domain.redis.client import RedisClient
from shared.infrastructure.redis.event_bus import RedisEventBus


class FakePubSub:
    """Simulates a redis PubSub object that can subscribe and listen."""

    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.channel: str | None = None
        self._messages = messages

    async def subscribe(self, channel: str) -> None:
        self.channel = channel

    async def listen(self) -> Any:
        for msg in self._messages:
            yield msg


class FakeRedisClient(RedisClient):
    """Implements just enough of RedisClient to satisfy RedisEventBus."""

    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []
        self.pubsub_messages: list[dict[str, Any]] = []

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        if args and args[0] == "PUBLISH":
            channel: str = args[1]
            raw_msg: str = args[2]
            self.published.append((channel, raw_msg))
            return len(raw_msg)
        return None

    async def ping(self) -> bool:
        return True

    def pubsub(self) -> FakePubSub:
        return FakePubSub(self.pubsub_messages)


# Fixtures
@pytest.fixture
def fake_redis() -> FakeRedisClient:
    return FakeRedisClient()


@pytest.fixture
def event_bus(fake_redis: FakeRedisClient) -> RedisEventBus:
    return RedisEventBus(redis_client=fake_redis)


# Tests
@pytest.mark.asyncio
async def test_publish(event_bus: RedisEventBus, fake_redis: FakeRedisClient) -> None:
    msg: dict[str, Any] = {"event": "slides:ready", "data": {"total_slides": 5}}
    await event_bus.publish("room_events", msg)

    assert len(fake_redis.published) == 1
    channel, raw_msg = fake_redis.published[0]
    assert channel == "room_events"
    assert json.loads(raw_msg) == msg


@pytest.mark.asyncio
async def test_subscribe_and_handle_message(
    event_bus: RedisEventBus, fake_redis: FakeRedisClient
) -> None:
    test_data: dict[str, Any] = {"event": "test", "data": {"key": "val"}}
    fake_redis.pubsub_messages = [{"type": "message", "data": json.dumps(test_data)}]

    received: list[dict[str, Any]] = []

    async def my_handler(data: dict[str, Any]) -> None:
        received.append(data)

    await asyncio.wait_for(event_bus.subscribe("room_events", my_handler), timeout=1)

    assert len(received) == 1
    assert received[0] == test_data
