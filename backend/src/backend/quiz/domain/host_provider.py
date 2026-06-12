from abc import ABC, abstractmethod


class HostProvider(ABC):
    @abstractmethod
    async def get_host(self, class_code: str) -> str | None: ...
