from abc import ABC, abstractmethod


class SlideRepository(ABC):
    @abstractmethod
    async def update_current_slide(self, class_code: str, slide_number: int) -> None:
        pass

    @abstractmethod
    async def get_room_host(self, class_code: str) -> str | None:
        pass

    @abstractmethod
    async def get_room_students(self, class_code: str) -> list[str]:
        pass
