from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.edges import HasThought
from bunnyland.core.handlers import HandlerContext

from bunnyland_fortunesim import LuckComponent, WardLuckEvent, spawn_charm
from bunnyland_fortunesim.superstition import WARD_DURATION, WardLuckHandler

EPOCH = 100


def _world_with_character(*, with_luck=True, base=0.0):
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Kitchen")])
    components = [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    if with_luck:
        components.append(LuckComponent(base=base, value=base))
    character = spawn_entity(actor.world, components)
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return actor, room, character


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="ward-luck",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


def _luck(character):
    return character.get_component(LuckComponent).value


# -- happy path --------------------------------------------------------------------------


def test_ward_luck_boosts_luck():
    actor, _room, character = _world_with_character()

    result = WardLuckHandler().execute(_ctx(actor), _cmd(character.id, {"ritual": "knock-on-wood"}))

    assert result.ok
    event = result.events[0]
    assert isinstance(event, WardLuckEvent)
    assert event.ritual == "knock-on-wood"
    assert event.until_epoch == EPOCH + WARD_DURATION
    assert _luck(character) == 1.0


def test_ward_luck_defaults_to_knock_on_wood():
    actor, _room, character = _world_with_character()

    result = WardLuckHandler().execute(_ctx(actor), _cmd(character.id, {}))

    assert result.ok
    assert result.events[0].ritual == "knock-on-wood"


def test_ward_luck_stacks_with_held_charm():
    actor, _room, character = _world_with_character()
    _hold(character, spawn_charm(actor.world, luck=1.0))

    WardLuckHandler().execute(_ctx(actor), _cmd(character.id, {"ritual": "knock-on-wood"}))

    # base 0 + charm 1.0 + ritual 1.0
    assert _luck(character) == 2.0


def test_ward_luck_grants_luck_component_when_missing():
    actor, _room, character = _world_with_character(with_luck=False)

    result = WardLuckHandler().execute(_ctx(actor), _cmd(character.id, {"ritual": "toss-salt"}))

    assert result.ok
    assert character.has_component(LuckComponent)
    assert _luck(character) == 1.0


def test_ward_luck_attaches_mood_thought():
    actor, _room, character = _world_with_character()

    WardLuckHandler().execute(_ctx(actor), _cmd(character.id, {"ritual": "knock-on-wood"}))

    assert list(character.get_relationships(HasThought))


def test_cross_fingers_is_a_smaller_boost():
    actor, _room, character = _world_with_character()

    WardLuckHandler().execute(_ctx(actor), _cmd(character.id, {"ritual": "cross-fingers"}))

    assert _luck(character) == 0.5


# -- rejections --------------------------------------------------------------------------


def test_rejects_invalid_character():
    actor, _room, _character = _world_with_character()
    result = WardLuckHandler().execute(_ctx(actor), _cmd("???", {}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_rejects_missing_character():
    actor, _room, _character = _world_with_character()
    result = WardLuckHandler().execute(_ctx(actor), _cmd("entity_9999", {}))
    assert not result.ok
    assert result.reason == "character does not exist"


def test_rejects_character_without_a_room():
    actor, _room, _character = _world_with_character()
    drifter = spawn_entity(
        actor.world, [IdentityComponent(name="drifter", kind="character"), CharacterComponent()]
    )
    result = WardLuckHandler().execute(_ctx(actor), _cmd(drifter.id, {}))
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_rejects_unknown_ritual():
    actor, _room, character = _world_with_character()
    result = WardLuckHandler().execute(
        _ctx(actor), _cmd(character.id, {"ritual": "sacrifice-goat"})
    )
    assert not result.ok
    assert result.reason == "unknown ritual"
