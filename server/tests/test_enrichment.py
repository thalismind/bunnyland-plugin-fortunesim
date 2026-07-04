from __future__ import annotations

import asyncio

from bunnyland.core import (
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import ObjectGeneratedEvent, RoomGeneratedEvent, event_base
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_fortunesim import CharmComponent, OmenComponent
from bunnyland_fortunesim.components import AUSPICIOUS, FOREBODING


def _actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_fortunesim"]), actor)
    return actor


def _publish(actor, event):
    asyncio.run(actor.bus.publish(event))


def _object(actor, *, tags=(), description=""):
    entity = spawn_entity(actor.world, [IdentityComponent(name="thing", kind="item")])
    event = ObjectGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="thing",
        entity_kind="object",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        object_key="thing",
    )
    _publish(actor, event)
    return entity


def _room(actor, *, tags=(), description=""):
    entity = spawn_entity(actor.world, [RoomComponent(title="Somewhere")])
    event = RoomGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="room",
        entity_kind="room",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        room_key="room",
    )
    _publish(actor, event)
    return entity


# -- objects -----------------------------------------------------------------------------


def test_lucky_object_becomes_a_charm():
    actor = _actor()
    entity = _object(actor, tags=("clover",), description="a four-leaf clover")
    assert entity.has_component(CharmComponent)
    assert not entity.get_component(CharmComponent).cursed


def test_cursed_object_becomes_a_negative_charm():
    actor = _actor()
    entity = _object(actor, description="a hexed, cursed little doll")
    assert entity.has_component(CharmComponent)
    assert entity.get_component(CharmComponent).cursed


def test_cursed_wins_over_lucky_terms():
    actor = _actor()
    # Mentions both "charm" and "cursed"; cursed is checked first.
    entity = _object(actor, tags=("charm",), description="a cursed charm")
    assert entity.get_component(CharmComponent).cursed


def test_plain_object_is_not_a_charm():
    actor = _actor()
    entity = _object(actor, tags=("wooden", "storage"), description="a plain crate")
    assert not entity.has_component(CharmComponent)


# -- rooms -------------------------------------------------------------------------------


def test_ominous_room_gets_foreboding_omen():
    actor = _actor()
    room = _room(actor, tags=("haunted",), description="an eerie, forsaken crypt")
    assert room.has_component(OmenComponent)
    omen = room.get_component(OmenComponent)
    assert omen.kind == FOREBODING
    assert omen.source == "worldgen"


def test_auspicious_room_gets_auspicious_omen():
    actor = _actor()
    room = _room(actor, tags=("shrine",), description="a hallowed, sunlit sanctuary")
    omen = room.get_component(OmenComponent)
    assert omen.kind == AUSPICIOUS
    assert omen.source == "worldgen"


def test_plain_room_gets_no_omen():
    actor = _actor()
    room = _room(actor, tags=("cozy",), description="a plain wooden kitchen")
    assert not room.has_component(OmenComponent)
