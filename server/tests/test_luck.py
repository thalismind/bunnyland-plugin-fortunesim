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
from bunnyland.core.components import AffectComponent
from bunnyland.core.edges import HasThought
from bunnyland.mechanics.affect import AffectAggregation

from bunnyland_fortunesim import (
    LuckChangedEvent,
    LuckComponent,
    LuckConsequence,
    effective_luck,
    luck_fragments,
    remember_fortune,
    spawn_charm,
)
from bunnyland_fortunesim.bands import luck_band, luck_multiplier

EPOCH = 100


def _room(world):
    return spawn_entity(world, [RoomComponent(title="Parlor")])


def _character(world, room, *, base=0.0, name="Vin"):
    character = spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="character"),
            CharacterComponent(),
            LuckComponent(base=base),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _luck(character):
    return character.get_component(LuckComponent).value


# -- band classification -----------------------------------------------------------------


def test_luck_bands_by_value():
    assert luck_band(3.0) == "blessed"
    assert luck_band(1.0) == "lucky"
    assert luck_band(0.0) == "even"
    assert luck_band(-1.0) == "unlucky"
    assert luck_band(-3.0) == "cursed"


def test_luck_multiplier_is_neutral_at_zero():
    assert luck_multiplier(0.0) == 1.0
    assert luck_multiplier(2.0) > 1.0
    assert 0.0 < luck_multiplier(-2.0) < 1.0


# -- charm-driven materialisation --------------------------------------------------------


def test_held_charm_raises_luck():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    charm = spawn_charm(actor.world, luck=1.0)
    _hold(character, charm)

    LuckConsequence().process(actor.world, EPOCH)

    assert _luck(character) == 1.0
    assert effective_luck(character) == 1.0


def test_cursed_charm_lowers_luck():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    trinket = spawn_charm(actor.world, luck=-1.5, label="trinket")
    _hold(character, trinket)

    LuckConsequence().process(actor.world, EPOCH)

    assert _luck(character) == -1.5


def test_dropping_a_charm_restores_luck():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    charm = spawn_charm(actor.world, luck=1.0)
    _hold(character, charm)
    LuckConsequence().process(actor.world, EPOCH)
    assert _luck(character) == 1.0

    # Drop the charm into the room and re-run: the bonus is gone.
    character.remove_relationship(Contains, charm.id)
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), charm.id)
    LuckConsequence().process(actor.world, EPOCH + 1)

    assert _luck(character) == 0.0


def test_multiple_charms_stack():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    _hold(character, spawn_charm(actor.world, luck=1.0))
    _hold(character, spawn_charm(actor.world, luck=1.5))

    LuckConsequence().process(actor.world, EPOCH)

    assert _luck(character) == 2.5


def test_base_luck_included():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room, base=0.5)
    _hold(character, spawn_charm(actor.world, luck=1.0))

    LuckConsequence().process(actor.world, EPOCH)

    assert _luck(character) == 1.5


# -- events ------------------------------------------------------------------------------


def test_band_crossing_emits_event():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)  # starts even at value 0.0
    _hold(character, spawn_charm(actor.world, luck=1.0))  # -> lucky

    events = LuckConsequence().process(actor.world, EPOCH)

    assert len(events) == 1
    assert isinstance(events[0], LuckChangedEvent)
    assert events[0].band == "lucky"
    assert events[0].value == 1.0


def test_no_event_when_band_unchanged():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    _hold(character, spawn_charm(actor.world, luck=0.2))  # still even

    assert LuckConsequence().process(actor.world, EPOCH) == []


def test_no_work_when_already_materialised():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    _hold(character, spawn_charm(actor.world, luck=1.0))
    LuckConsequence().process(actor.world, EPOCH)

    # Second pass with no world change does nothing.
    assert LuckConsequence().process(actor.world, EPOCH) == []


def test_character_without_luck_component_is_ignored():
    actor = WorldActor()
    room = _room(actor.world)
    plain = spawn_entity(
        actor.world, [IdentityComponent(name="npc", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), plain.id)

    assert LuckConsequence().process(actor.world, EPOCH) == []
    assert effective_luck(plain) == 0.0


# -- prompt fragments --------------------------------------------------------------------


def test_lucky_character_reads_favor_line():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    _hold(character, spawn_charm(actor.world, luck=1.0))
    LuckConsequence().process(actor.world, EPOCH)

    assert luck_fragments(actor.world, character) == ["Fortune favors you today."]


def test_even_character_has_no_luck_line():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)

    assert luck_fragments(actor.world, character) == []


def test_cursed_character_reads_doom_line():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    _hold(character, spawn_charm(actor.world, luck=-3.0, label="trinket"))
    LuckConsequence().process(actor.world, EPOCH)

    lines = luck_fragments(actor.world, character)
    assert lines and "luck has abandoned you" in lines[0]


def test_luck_fragments_empty_for_character_without_luck():
    actor = WorldActor()
    room = _room(actor.world)
    plain = spawn_entity(
        actor.world, [IdentityComponent(name="npc", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), plain.id)

    assert luck_fragments(actor.world, plain) == []


# -- affect reuse ------------------------------------------------------------------------


def test_remember_fortune_attaches_mood_thought():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)

    thought = remember_fortune(actor.world, character, "lucky", EPOCH)

    assert thought is not None
    edges = list(character.get_relationships(HasThought))
    assert edges and edges[0][1] == thought.id


def test_remember_fortune_neutral_band_does_nothing():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)

    assert remember_fortune(actor.world, character, "even", EPOCH) is None
    assert list(character.get_relationships(HasThought)) == []


def test_fortune_mood_folds_into_affect_component():
    actor = WorldActor()
    room = _room(actor.world)
    character = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="Vin", kind="character"),
            CharacterComponent(),
            LuckComponent(),
            AffectComponent(),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)

    remember_fortune(actor.world, character, "blessed", EPOCH)
    AffectAggregation().process(actor.world, EPOCH)

    assert "content" in character.get_component(AffectComponent).labels
