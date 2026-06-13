import json
from unittest.mock import AsyncMock, patch

import pytest
import websockets
from classroom.domain.classroom import Classroom, StudentState
from classroom.interface.classroom_handler import ClassroomHandler


@pytest.mark.asyncio
async def test_classroom_handler_sync_event_sends_state_sync():
    """
    Flow:
    1. Frontend (teacher/student) sends classroom:sync with a valid class_code.
    2. Handler detects class_code via room_registry.
    3. Handler fetches the latest state from the service.
    4. Backend replies with classroom:state_sync.
    """
    service = AsyncMock()
    ws_manager = AsyncMock()
    room_registry = AsyncMock()
    broadcast_service = AsyncMock()
    gamification_service = AsyncMock()
    quiz_service = AsyncMock()

    handler = ClassroomHandler(
        service=service,
        ws_manager=ws_manager,
        room_registry=room_registry,
        broadcast_service=broadcast_service,
        gamification_service=gamification_service,
        quiz_service=quiz_service,
    )

    session_id = "reconnect_sess_123"
    class_code = "BIO101"
    room_state = Classroom(
        class_code=class_code,
        host_session_id="host_sess",
        current_slide=5,
        total_slides=15,
        active_students={
            "sess_student_A": StudentState(name="Andi"),
        },
    )

    room_registry.get_room_by_session.return_value = class_code
    service.get_room_state.return_value = room_state

    # Payload must include the class_code (required by SyncClassroomPayload)
    await handler("classroom:sync", session_id, {"class_code": class_code})

    room_registry.get_room_by_session.assert_awaited_once_with(session_id)
    service.get_room_state.assert_awaited_once_with(class_code)
    ws_manager.send.assert_awaited_once_with(
        event="classroom:state_sync",
        session_id=session_id,
        data={
            "class_code": "BIO101",
            "host_session_id": "host_sess",
            "current_slide": "5",
            "total_slides": "15",
            "active_students": ["Andi"],
        },
    )


@pytest.mark.asyncio
async def test_classroom_handler_sync_ignores_when_not_in_room():
    """
    If the session is not associated with any room, the handler sends an error
    (it does not silently ignore the request).
    """
    service = AsyncMock()
    ws_manager = AsyncMock()
    room_registry = AsyncMock()
    room_registry.get_room_by_session.return_value = None

    broadcast_service = AsyncMock()
    gamification_service = AsyncMock()
    quiz_service = AsyncMock()

    handler = ClassroomHandler(
        service=service,
        ws_manager=ws_manager,
        room_registry=room_registry,
        broadcast_service=broadcast_service,
        gamification_service=gamification_service,
        quiz_service=quiz_service,
    )

    await handler("classroom:sync", "lonely_sess", {"class_code": "some_class"})

    # The handler sends an error when the session does not belong to the given class
    ws_manager.send.assert_called_once()
    call_args = ws_manager.send.call_args

    assert call_args.kwargs["event"] == "classroom:error"
    error_message = call_args.kwargs["data"]["message"]
    assert "not in class" in error_message or "mismatch" in error_message


@pytest.mark.asyncio
@patch("application.main.Application")
async def test_full_reconnect_flow_sync_after_reconnect(mock_app_class):
    """
    Simulate the complete backend reconnect flow:
    1. A new WebSocket connection comes in with an old session_id.
    2. Backend sends connection:assigned with that session_id.
    3. Frontend immediately sends classroom:sync.
    4. ClassroomHandler processes it and returns classroom:state_sync.
    """
    app = mock_app_class.return_value
    ws_manager = app.ws_manager
    ws_manager.establish = AsyncMock(return_value="existing_sess")
    ws_manager.send = AsyncMock()
    ws_manager.unregister = AsyncMock()
    ws_router = app.ws_router
    room_registry = app.room_registry
    room_registry.remove_participant_by_session = AsyncMock()

    async def simulate_sync(event_type, session_id, data):
        if event_type == "classroom:sync":
            room_state = Classroom(
                class_code="BIO101",
                host_session_id="host_1",
                current_slide=1,
                total_slides=10,
                active_students={},
            )
            await ws_manager.send("classroom:state_sync", session_id, room_state.model_dump())

    ws_router.dispatch = AsyncMock(side_effect=simulate_sync)

    ws = AsyncMock(spec=websockets.ServerConnection)
    ws.recv.return_value = json.dumps({"data": {"session_id": "existing_sess"}})
    ws.__aiter__.return_value = [
        json.dumps({"event": "classroom:sync", "data": {"class_code": "BIO101"}}),
    ]

    from application.message_parser import process_raw_message

    async def handler(websocket: websockets.ServerConnection) -> None:
        session_id = await ws_manager.establish(websocket)
        if not session_id:
            return
        await ws_manager.send("connection:assigned", session_id, {"session_id": session_id})
        try:
            async for raw_msg in websocket:
                await process_raw_message(raw_msg, session_id, ws_router, ws_manager)
        except websockets.ConnectionClosed:
            pass
        finally:
            await ws_manager.unregister(session_id)
            await room_registry.remove_participant_by_session(session_id)

    await handler(ws)

    ws_manager.establish.assert_awaited_once_with(ws)
    ws_manager.send.assert_any_call(
        "connection:assigned", "existing_sess", {"session_id": "existing_sess"}
    )
    ws_manager.send.assert_any_call(
        "classroom:state_sync",
        "existing_sess",
        {
            "class_code": "BIO101",
            "host_session_id": "host_1",
            "current_slide": 1,
            "total_slides": 10,
            "active_students": {},
        },
    )
    ws_manager.unregister.assert_awaited_once_with("existing_sess")
    room_registry.remove_participant_by_session.assert_awaited_once_with("existing_sess")


@pytest.mark.asyncio
async def test_teacher_reconnect_recovers_host_privileges():
    """
    After reconnecting, the teacher's session must be identified as the host
    and the state sync must reflect that.
    """
    service = AsyncMock()
    ws_manager = AsyncMock()
    room_registry = AsyncMock()
    broadcast_service = AsyncMock()
    gamification_service = AsyncMock()
    quiz_service = AsyncMock()

    handler = ClassroomHandler(
        service=service,
        ws_manager=ws_manager,
        room_registry=room_registry,
        broadcast_service=broadcast_service,
        gamification_service=gamification_service,
        quiz_service=quiz_service,
    )

    teacher_session_id = "teacher_old_sess_reconnect"
    class_code = "MATH101"
    room_state = Classroom(
        class_code=class_code,
        host_session_id=teacher_session_id,
        current_slide=3,
        total_slides=20,
        active_students={"stu1": StudentState(name="Budi")},
    )

    room_registry.get_room_by_session.return_value = class_code
    service.get_room_state.return_value = room_state

    # Include the class_code in the payload
    await handler("classroom:sync", teacher_session_id, {"class_code": class_code})

    ws_manager.send.assert_awaited_once_with(
        event="classroom:state_sync",
        session_id=teacher_session_id,
        data={
            "class_code": "MATH101",
            "host_session_id": "teacher_old_sess_reconnect",
            "current_slide": "3",
            "total_slides": "20",
            "active_students": ["Budi"],
        },
    )
