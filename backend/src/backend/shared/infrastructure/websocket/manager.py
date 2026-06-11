import contextlib
import json
import logging
import secrets
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

    async def establish(self, websocket: websockets.ServerConnection) -> str | None:
        try:
            first_frame = await websocket.recv()
        except websockets.ConnectionClosed:
            return None

        payload: dict[str, Any] = {}
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            payload = json.loads(first_frame)

        data = payload.get("data")
        session_id = data.get("session_id") if isinstance(data, dict) else None

        if not session_id:
            session_id = secrets.token_urlsafe(24)
            logger.info(f"New session created: {session_id}")
        else:
            logger.info(f"Reconnect attempt: {session_id}")

        await self.register(session_id, websocket)
        # register() already returns without adding if duplicate login, and closes the new socket.
        # If the session_id was already present, the new websocket is kicked, and session_id is not stored.
        # So check if it's actually registered now:
        if session_id not in self._connections:
            return None  # duplicate login handled, caller can stop

        return session_id
