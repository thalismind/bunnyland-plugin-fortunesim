from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)

from bunnyland_fortunesim.spatial import holder_of, room_of


def _world():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Parlour")])
    return actor, room


def test_holder_of_finds_the_carrier():
    actor, room = _world()
    person = spawn_entity(actor.world, [IdentityComponent(name="Fen", kind="character")])
    item = spawn_entity(actor.world, [IdentityComponent(name="deck", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), person.id)
    person.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)
    holder = holder_of(actor.world, item.id)
    assert holder is not None and holder.id == person.id


def test_holder_of_none_for_missing_item():
    actor, _room = _world()
    assert holder_of(actor.world, "entity_9999") is None


def test_holder_of_none_when_loose():
    actor, _room = _world()
    loose = spawn_entity(actor.world, [IdentityComponent(name="orphan", kind="item")])
    assert holder_of(actor.world, loose.id) is None


def test_holder_of_none_when_in_a_room():
    actor, room = _world()
    item = spawn_entity(actor.world, [IdentityComponent(name="rug", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), item.id)
    assert holder_of(actor.world, item.id) is None


def test_room_of_resolves_through_a_holder():
    actor, room = _world()
    person = spawn_entity(actor.world, [IdentityComponent(name="Fen", kind="character")])
    item = spawn_entity(actor.world, [IdentityComponent(name="deck", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), person.id)
    person.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)
    found = room_of(actor.world, item.id)
    assert found is not None and found.id == room.id


def test_room_of_none_for_missing_entity():
    actor, _room = _world()
    assert room_of(actor.world, "entity_9999") is None


def test_room_of_none_when_uncontained():
    actor, _room = _world()
    orphan = spawn_entity(actor.world, [IdentityComponent(name="orphan", kind="item")])
    assert room_of(actor.world, orphan.id) is None
