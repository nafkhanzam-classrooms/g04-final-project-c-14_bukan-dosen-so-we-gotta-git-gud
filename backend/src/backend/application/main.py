import asyncio
import json
import logging
import secrets

import websockets
from classroom.application.classroom_service import ClassroomService
from classroom.interface.classroom_handler import ClassroomHandler
from classroom.repository.classroom_repository import ClassroomRedisRepository
from shared.infrastructure.redis.client import redis_db
from shared.infrastructure.websocket.manager import ws_manager
from shared.infrastructure.websocket.router import ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def bootstrap_dependencies() -> None:
    classroom_repo = ClassroomRedisRepository(redis_client=redis_db)
    classroom_service = ClassroomService(repository=classroom_repo)
    classroom_handler = ClassroomHandler(service=classroom_service, ws_manager=ws_manager)

    ws_router.register("classroom", classroom_handler)


async def handle_connection(websocket: websockets.ServerConnection) -> None:
    session_id = None
    try:
        # First frame identification
        first_frame = await websocket.recv()

        try:
            payload = json.loads(first_frame)
            if payload.get("event") == "connection:init":
                session_id = payload.get("data", {}).get("session_id")
        except (json.JSONDecodeError, TypeError):
            pass

        # Session_id creation or reuse
        if not session_id:
            session_id = secrets.token_urlsafe(24)
            logger.info(f"New session created: {session_id}")
        else:
            logger.info(f"Existing session attempting to reconnect: {session_id}")

        await ws_manager.register(session_id, websocket)

        if session_id not in ws_manager._connections:
            return

        await ws_manager.send(
            event="connection:assigned", session_id=session_id, data={"session_id": session_id}
        )

        # Main loop for next frames
        async for message in websocket:
            try:
                if isinstance(message, bytes):
                    message = message.decode("utf-8")

                payload = json.loads(message)
                event_type = payload.get("event")
                event_data = payload.get("data", {})

                if event_type:
                    await ws_router.dispatch(event_type, session_id, event_data)

            except json.JSONDecodeError:
                await ws_manager.send("error", session_id, {"message": "Invalid JSON format."})

    except websockets.ConnectionClosed:
        pass
    finally:
        if session_id:
            await ws_manager.unregister(session_id)


async def main() -> None:
    bootstrap_dependencies()

    async with websockets.serve(handle_connection, "0.0.0.0", 6767) as server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
