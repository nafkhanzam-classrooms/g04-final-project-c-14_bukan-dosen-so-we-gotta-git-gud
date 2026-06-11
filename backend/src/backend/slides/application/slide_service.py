import logging

from slides.domain.repository_interface import SlideRepository

logger = logging.getLogger(__name__)


class SlideService:
    def __init__(self, repository: SlideRepository):
        self.repo = repository

    async def change_slide(self, session_id: str, class_code: str, slide_number: int) -> None:
        host_id = await self.repo.get_room_host(class_code)

        if not host_id:
            logger.warning("Slide change failed: class %s not found", class_code)
            raise ValueError("Class not found.")

        if host_id != session_id:
            logger.warning(
                "Unauthorized slide change attempt by %s for class %s", session_id, class_code
            )
            raise PermissionError("Only Host is allowed to change the slide.")

        await self.repo.update_current_slide(class_code, slide_number)
