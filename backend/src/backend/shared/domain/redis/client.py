from abc import ABC, abstractmethod
from typing import Any


class RedisClient(ABC):
    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def ping(self) -> bool: ...

    @abstractmethod
    def pubsub(self) -> Any: ...
