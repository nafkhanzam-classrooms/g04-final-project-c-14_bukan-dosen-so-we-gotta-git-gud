from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any


class EventSubscriber(ABC):
    @abstractmethod
    async def subscribe(
        self, channel: str, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None: ...
