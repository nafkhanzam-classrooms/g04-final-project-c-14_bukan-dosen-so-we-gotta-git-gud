import json

from shared.infrastructure.websocket.manager import WSConnectionManager
from shared.infrastructure.websocket.router import WSEventRouter


async def process_raw_message(
    raw_msg: str | bytes, session_id: str, router: WSEventRouter, manager: WSConnectionManager
) -> None:
    if isinstance(raw_msg, bytes):
        raw_msg = raw_msg.decode("utf-8")
    try:
        payload = json.loads(raw_msg)
    except json.JSONDecodeError:
        await manager.send("error", session_id, {"message": "Invalid JSON format."})
        return
    event_type = payload.get("event")
    event_data = payload.get("data", {})
    if event_type:
        await router.dispatch(event_type, session_id, event_data)
