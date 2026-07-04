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

from bunnyland_fortunesim import (
    CharmComponent,
    charm_fragments,
    held_charm_bonus,
    spawn_charm,
    spawn_cursed_trinket,
    spawn_talisman,
)


def _room(world):
    return spawn_entity(world, [RoomComponent(title="Den")])


def _character(world, room):
    character = spawn_entity(
        world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def test_spawn_charm_defaults_to_lucky():
    actor = WorldActor()
    charm = spawn_charm(actor.world)
    assert charm.has_component(CharmComponent)
    assert charm.get_component(CharmComponent).luck == 1.0
    assert not charm.get_component(CharmComponent).cursed


def test_spawn_talisman_is_stronger():
    actor = WorldActor()
    talisman = spawn_talisman(actor.world)
    assert talisman.get_component(CharmComponent).luck == 2.0


def test_spawn_cursed_trinket_is_negative():
    actor = WorldActor()
    trinket = spawn_cursed_trinket(actor.world)
    assert trinket.get_component(CharmComponent).cursed


def test_spawn_charm_places_into_room():
    from bunnyland.core.ecs import contents

    actor = WorldActor()
    room = _room(actor.world)
    charm = spawn_charm(actor.world, room_id=room.id)
    assert charm.id in set(contents(room))


def test_held_charm_bonus_sums_held_charms():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    _hold(character, spawn_charm(actor.world, luck=1.0))
    _hold(character, spawn_cursed_trinket(actor.world, luck=-0.5))

    assert held_charm_bonus(actor.world, character) == 0.5


def test_held_charm_bonus_ignores_loose_charms():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    spawn_charm(actor.world, room_id=room.id, luck=1.0)  # on the floor, not held

    assert held_charm_bonus(actor.world, character) == 0.0


def test_charm_fragment_first_person_for_holder():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    _hold(character, spawn_charm(actor.world, luck=1.0, label="rabbit's foot"))

    lines = charm_fragments(actor.world, character)

    assert lines == ["You carry a lucky rabbit's foot."]


def test_cursed_charm_fragment_reads_wrong():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    _hold(character, spawn_cursed_trinket(actor.world, label="doll"))

    lines = charm_fragments(actor.world, character)

    assert lines == ["You carry a cursed doll; it feels wrong in your hand."]


def test_no_charm_fragments_when_empty_handed():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)

    assert charm_fragments(actor.world, character) == []


def test_charm_fragments_none_character():
    actor = WorldActor()
    assert charm_fragments(actor.world, None) == []
