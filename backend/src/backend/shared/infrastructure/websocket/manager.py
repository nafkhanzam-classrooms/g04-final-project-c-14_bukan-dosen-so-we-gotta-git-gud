import logging
from typing import Any

import websockets
from shared.domain.websocket.envelope import WSMessage

logger = logging.getLogger(__name__)


class WSConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, websockets.ServerConnection] = {}

    async def register(self, session_id: str, websocket: websockets.ServerConnection) -> None:
        # 1. Duplicate Login
        if session_id in self._connections:
            logger.warning(
                f"Duplicate login detected for '{session_id}'. Kicking new connection..."
            )
            try:
                await websocket.send(
                    "ERROR|DUPLICATE_LOGIN| Your account is logged in another location"
                )
                await websocket.close(code=1008, reason="Duplicate Login - active session exists")
            except websockets.ConnectionClosed:
                pass

            return

        # 2. Normal scenario + could also be used for reconnect
        self._connections[session_id] = websocket
        logger.info(f"User '{session_id}' registered. Total online: {len(self._connections)}")

    async def unregister(self, session_id: str) -> None:
        if session_id in self._connections:
            del self._connections[session_id]
            logger.info(f"User '{session_id}' left. Total online: {len(self._connections)}")
        pass

    async def send(self, event: str, session_id: str, data: dict[str, Any]) -> None:
        websocket = self._connections.get(session_id)
        if websocket:
            envelope = WSMessage(event=event, data=data)
            await websocket.send(envelope.model_dump_json())

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        # For-loop through all connected users
        for user_id, websocket in list(self._connections.items()):
            try:
                envelope = WSMessage(event=event, data=data)
                await websocket.send(envelope.model_dump_json())
            except websockets.ConnectionClosed:  # if connected user has left during a broadcast
                await self.unregister(user_id)
        pass


ws_manager = WSConnectionManager()
