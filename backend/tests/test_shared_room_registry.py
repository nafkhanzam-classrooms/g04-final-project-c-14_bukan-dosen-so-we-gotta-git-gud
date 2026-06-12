import pytest
from shared.infrastructure.room.in_memory_registry import InMemoryRoomRegistry


@pytest.fixture
def registry():
    return InMemoryRoomRegistry()


@pytest.mark.asyncio
async def test_add_and_get_participants(registry):
    await registry.add_participant("class1", "sessA")
    await registry.add_participant("class1", "sessB")
    await registry.add_participant("class2", "sessC")

    assert await registry.get_participants("class1") == {"sessA", "sessB"}
    assert await registry.get_participants("class2") == {"sessC"}


@pytest.mark.asyncio
async def test_remove_participant(registry):
    await registry.add_participant("class1", "sessA")
    await registry.remove_participant("class1", "sessA")

    assert await registry.get_participants("class1") == set()


@pytest.mark.asyncio
async def test_remove_participant_by_session(registry):
    await registry.add_participant("class1", "sessA")
    await registry.remove_participant_by_session("sessA")

    assert await registry.get_participants("class1") == set()


@pytest.mark.asyncio
async def test_remove_nonexistent_no_error(registry):
    await registry.remove_participant("ghost", "sessX")
    await registry.remove_participant_by_session("sessY")


@pytest.mark.asyncio
async def test_remove_all_participants(registry):
    class_code = "MATH123"

    await registry.add_participant(class_code, "student_1")
    await registry.add_participant(class_code, "student_2")

    assert await registry.get_room_by_session("student_1") == class_code
    assert len(await registry.get_participants(class_code)) == 2

    await registry.remove_all_participants(class_code)

    assert await registry.get_room_by_session("student_1") is None
    assert len(await registry.get_participants(class_code)) == 0
