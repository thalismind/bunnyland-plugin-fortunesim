from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.edges import HasThought
from bunnyland.core.handlers import HandlerContext

from bunnyland_fortunesim import (
    FortuneReadEvent,
    LuckComponent,
    ReadFortuneHandler,
    compose_reading,
    spawn_charm,
    spawn_fortune_tool,
)
from bunnyland_fortunesim.fortune import READINGS

EPOCH = 100


def _world_with_seeker(*, base=0.0):
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Reading Room")])
    seeker = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="Vin", kind="character"),
            CharacterComponent(),
            LuckComponent(base=base, value=base),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), seeker.id)
    return actor, room, seeker


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="read-fortune",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


# -- happy path --------------------------------------------------------------------------


def test_read_fortune_produces_a_reading():
    actor, _room, seeker = _world_with_seeker()
    tool = spawn_fortune_tool(actor.world)
    _hold(seeker, tool)

    result = ReadFortuneHandler().execute(_ctx(actor), _cmd(seeker.id, {"tool_id": str(tool.id)}))

    assert result.ok
    event = result.events[0]
    assert isinstance(event, FortuneReadEvent)
    assert event.seeker_id == str(seeker.id)
    assert event.reading in READINGS or event.reading.startswith(tuple(READINGS))


def test_read_fortune_attaches_mood_when_lucky():
    actor, _room, seeker = _world_with_seeker(base=1.0)
    tool = spawn_fortune_tool(actor.world)
    _hold(seeker, tool)

    ReadFortuneHandler().execute(_ctx(actor), _cmd(seeker.id, {"tool_id": str(tool.id)}))

    assert list(seeker.get_relationships(HasThought))


def test_lucky_seeker_reads_brighter_than_cursed():
    lucky = compose_reading("entity_5", EPOCH, 3.0, None)
    cursed = compose_reading("entity_5", EPOCH, -3.0, None)
    assert READINGS.index(_line_of(lucky)) >= READINGS.index(_line_of(cursed))


def _line_of(reading: str) -> str:
    for line in READINGS:
        if reading.startswith(line):
            return line
    raise AssertionError(f"no known reading in {reading!r}")


def test_reading_weaves_in_room_omen():
    from bunnyland_fortunesim import OmenConsequence

    actor, room, seeker = _world_with_seeker()
    tool = spawn_fortune_tool(actor.world)
    _hold(seeker, tool)
    spawn_charm(actor.world, room_id=room.id, luck=1.0)  # auspicious omen in the room
    OmenConsequence().process(actor.world, EPOCH)

    result = ReadFortuneHandler().execute(_ctx(actor), _cmd(seeker.id, {"tool_id": str(tool.id)}))

    assert "You sense it echoed here" in result.events[0].reading


# -- determinism -------------------------------------------------------------------------


def test_compose_reading_is_deterministic():
    readings = {compose_reading("entity_7", EPOCH, 0.5, None) for _ in range(5)}
    assert len(readings) == 1


# -- rejections --------------------------------------------------------------------------


def test_rejects_invalid_character():
    actor, _room, _seeker = _world_with_seeker()
    result = ReadFortuneHandler().execute(_ctx(actor), _cmd("???", {"tool_id": "entity_1"}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_rejects_missing_character():
    actor, _room, _seeker = _world_with_seeker()
    result = ReadFortuneHandler().execute(_ctx(actor), _cmd("entity_9999", {"tool_id": "entity_1"}))
    assert not result.ok
    assert result.reason == "character does not exist"


def test_rejects_invalid_tool_id():
    actor, _room, seeker = _world_with_seeker()
    result = ReadFortuneHandler().execute(_ctx(actor), _cmd(seeker.id, {"tool_id": "???"}))
    assert not result.ok
    assert result.reason == "invalid tool id"


def test_rejects_missing_tool():
    actor, _room, seeker = _world_with_seeker()
    result = ReadFortuneHandler().execute(_ctx(actor), _cmd(seeker.id, {"tool_id": "entity_9999"}))
    assert not result.ok
    assert result.reason == "tool does not exist"


def test_rejects_unheld_tool():
    actor, room, seeker = _world_with_seeker()
    tool = spawn_fortune_tool(actor.world, room_id=room.id)  # on the floor
    result = ReadFortuneHandler().execute(_ctx(actor), _cmd(seeker.id, {"tool_id": str(tool.id)}))
    assert not result.ok
    assert result.reason == "you are not holding that tool"


def test_rejects_non_fortune_tool():
    actor, _room, seeker = _world_with_seeker()
    lantern = spawn_entity(
        actor.world,
        [IdentityComponent(name="lantern", kind="item"), PortableComponent(), HoldableComponent()],
    )
    _hold(seeker, lantern)
    result = ReadFortuneHandler().execute(
        _ctx(actor), _cmd(seeker.id, {"tool_id": str(lantern.id)})
    )
    assert not result.ok
    assert result.reason == "that is not a fortune-telling tool"
