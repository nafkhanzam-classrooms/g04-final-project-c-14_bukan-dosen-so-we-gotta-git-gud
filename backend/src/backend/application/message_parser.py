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

        manager.reset_error(session_id)
    except json.JSONDecodeError:
        current_errors = manager.record_error(session_id)
        if manager.is_tolerance_exceeded(session_id):
            await manager.kick(session_id, "Too many invalid packets sent.")
        else:
            await manager.send(
                "error",
                session_id,
                {
                    "message": f"Invalid JSON format. Warning {current_errors}/{manager.max_error_tolerance}"
                },
            )
        return

    event_type = payload.get("event")
    event_data = payload.get("data", {})

    if event_type:
        await router.dispatch(event_type, session_id, event_data)
