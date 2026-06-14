from abc import ABC, abstractmethod


class RoomRegistry(ABC):
    @abstractmethod
    async def add_participant(self, class_code: str, session_id: str) -> None: ...

    @abstractmethod
    async def remove_participant(self, class_code: str, session_id: str) -> None: ...

    @abstractmethod
    async def get_participants(self, class_code: str) -> set[str]: ...

    @abstractmethod
    async def get_room_by_session(self, session_id: str) -> str | None: ...

    @abstractmethod
    async def remove_all_participants(self, class_code: str) -> None: ...

    @abstractmethod
    async def set_room_host(self, class_code: str, host_session_id: str) -> None: ...

    @abstractmethod
    async def get_room_host(self, class_code: str) -> str | None: ...
