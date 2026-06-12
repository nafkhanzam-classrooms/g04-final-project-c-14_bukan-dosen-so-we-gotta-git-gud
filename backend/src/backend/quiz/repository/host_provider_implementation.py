from quiz.domain.host_provider import HostProvider
from slides.domain.repository_interface import SlideRepository


class SlideHostProvider(HostProvider):
    def __init__(self, slide_repo: SlideRepository):
        self._slide_repo = slide_repo

    async def get_host(self, class_code: str) -> str | None:
        return await self._slide_repo.get_room_host(class_code)
