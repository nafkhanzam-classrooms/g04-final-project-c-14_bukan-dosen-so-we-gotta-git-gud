from collections.abc import Awaitable, Callable
from typing import Any

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
            await handler(event_type, session_id, payload)


ws_router = WSEventRouter()
