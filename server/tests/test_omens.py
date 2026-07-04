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
    OmenClearedEvent,
    OmenComponent,
    OmenConsequence,
    OmenSightedEvent,
    omen_fragments,
    spawn_charm,
    spawn_cursed_trinket,
)
from bunnyland_fortunesim.components import AUSPICIOUS, FOREBODING

EPOCH = 100


def _room(world, *, title="Cellar"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room):
    character = spawn_entity(
        world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _omen(room):
    return room.get_component(OmenComponent) if room.has_component(OmenComponent) else None


# -- dynamic omens from loose charms -----------------------------------------------------


def test_loose_cursed_charm_casts_foreboding():
    actor = WorldActor()
    room = _room(actor.world)
    spawn_cursed_trinket(actor.world, room_id=room.id)

    events = OmenConsequence().process(actor.world, EPOCH)

    assert _omen(room).kind == FOREBODING
    assert len(events) == 1
    assert isinstance(events[0], OmenSightedEvent)
    assert events[0].kind == FOREBODING


def test_loose_lucky_charm_casts_auspicious():
    actor = WorldActor()
    room = _room(actor.world)
    spawn_charm(actor.world, room_id=room.id, luck=1.0)

    OmenConsequence().process(actor.world, EPOCH)

    assert _omen(room).kind == AUSPICIOUS


def test_cursed_charm_wins_over_lucky():
    actor = WorldActor()
    room = _room(actor.world)
    spawn_charm(actor.world, room_id=room.id, luck=1.0)
    spawn_cursed_trinket(actor.world, room_id=room.id)

    OmenConsequence().process(actor.world, EPOCH)

    assert _omen(room).kind == FOREBODING


def test_plain_room_has_no_omen():
    actor = WorldActor()
    room = _room(actor.world)

    assert OmenConsequence().process(actor.world, EPOCH) == []
    assert _omen(room) is None


def test_removing_the_charm_clears_dynamic_omen():
    actor = WorldActor()
    room = _room(actor.world)
    trinket = spawn_cursed_trinket(actor.world, room_id=room.id)
    OmenConsequence().process(actor.world, EPOCH)
    assert _omen(room) is not None

    actor.world.remove(trinket.id)
    events = OmenConsequence().process(actor.world, EPOCH + 1)

    assert _omen(room) is None
    assert len(events) == 1
    assert isinstance(events[0], OmenClearedEvent)


def test_stable_dynamic_omen_does_not_re_emit():
    actor = WorldActor()
    room = _room(actor.world)
    spawn_cursed_trinket(actor.world, room_id=room.id)
    OmenConsequence().process(actor.world, EPOCH)

    # Same window, same charms -> no new event.
    assert OmenConsequence().process(actor.world, EPOCH) == []


def test_worldgen_omen_is_left_untouched():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(
        OmenComponent(kind=FOREBODING, omen="ominous-locale", text="Dread hangs here.",
                      source="worldgen")
    )
    # Even with a lucky charm loose, the sticky worldgen omen stays.
    spawn_charm(actor.world, room_id=room.id, luck=1.0)

    assert OmenConsequence().process(actor.world, EPOCH) == []
    assert _omen(room).source == "worldgen"


# -- determinism -------------------------------------------------------------------------


def test_dynamic_omen_text_is_deterministic():
    texts = set()
    for _ in range(3):
        actor = WorldActor()
        room = spawn_entity(actor.world, [RoomComponent(title="Cellar")])
        spawn_cursed_trinket(actor.world, room_id=room.id)
        OmenConsequence().process(actor.world, EPOCH)
        texts.add(_omen(room).text)
    # The room id is stable across identical worlds, so the omen text is too.
    assert len(texts) == 1


# -- prompt fragments --------------------------------------------------------------------


def test_omen_fragment_renders_room_omen():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    spawn_cursed_trinket(actor.world, room_id=room.id)
    OmenConsequence().process(actor.world, EPOCH)

    lines = omen_fragments(actor.world, character)

    assert lines == [_omen(room).text]


def test_omen_fragment_empty_without_omen():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)

    assert omen_fragments(actor.world, character) == []


def test_omen_fragment_none_character():
    actor = WorldActor()
    assert omen_fragments(actor.world, None) == []


def test_omen_fragment_character_without_room():
    actor = WorldActor()
    character = spawn_entity(
        actor.world, [IdentityComponent(name="drifter", kind="character"), CharacterComponent()]
    )
    assert omen_fragments(actor.world, character) == []
