import asyncio
import logging

import websockets

from application.bootstrap import Application
from application.config import settings
from application.message_parser import process_raw_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    app = Application()
    await app.start_background_tasks()

    async def handler(websocket: websockets.ServerConnection) -> None:
        session_id = await app.ws_manager.establish(websocket)
        if not session_id:
            return
        await app.ws_manager.send("connection:assigned", session_id, {"session_id": session_id})
        try:
            async for raw_msg in websocket:
                await process_raw_message(raw_msg, session_id, app.ws_router, app.ws_manager)
        except websockets.ConnectionClosed:
            pass
        finally:
            await app.ws_manager.unregister(session_id)
            await app.room_registry.remove_participant_by_session(session_id)

    async with websockets.serve(
        handler,
        settings.ws_host,
        settings.ws_port,
        ping_interval=settings.ws_ping_interval,
        ping_timeout=settings.ws_ping_timeout,
    ) as server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
