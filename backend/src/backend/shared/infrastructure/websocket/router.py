import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

HandlerType = Callable[[str, str, dict[str, Any]], Awaitable[None]]


class WSEventRouter:
    def __init__(self, delimiter: str = ":"):
        self._routes: dict[str, HandlerType] = {}
        self.delimiter = delimiter

    def register(self, prefix: str, handler: HandlerType) -> None:
        self._routes[prefix] = handler

    async def dispatch(self, event_type: str, session_id: str, payload: dict[str, Any]) -> None:
        prefix = event_type.split(self.delimiter, 1)[0]

        handler = self._routes.get(prefix)

        if handler:
            logger.debug(
                "Dispatching event '%s' (prefix '%s') to handler for session %s",
                event_type,
                prefix,
                session_id,
            )
            await handler(event_type, session_id, payload)
        else:
            logger.warning(
                f"No router prefix found for '{prefix}' (Full event: '{event_type}') from session '{session_id}'."
            )
