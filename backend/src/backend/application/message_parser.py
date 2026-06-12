import json
import logging

from shared.infrastructure.websocket.manager import WSConnectionManager
from shared.infrastructure.websocket.router import WSEventRouter

logger = logging.getLogger(__name__)


async def process_raw_message(
    raw_msg: str | bytes, session_id: str, router: WSEventRouter, manager: WSConnectionManager
) -> None:
    if isinstance(raw_msg, bytes):
        raw_msg = raw_msg.decode("utf-8")

    logger.debug("Received raw message from session %s: %s", session_id, raw_msg)

    try:
        payload = json.loads(raw_msg)

        manager.reset_error(session_id)
    except json.JSONDecodeError:
        current_errors = manager.record_error(session_id)
        logger.warning("Invalid JSON from session %s: %s", session_id, raw_msg, exc_info=True)

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

    logger.debug("Parsed event '%s' from session %s", event_type, session_id)

    if event_type:
        await router.dispatch(event_type, session_id, event_data)
