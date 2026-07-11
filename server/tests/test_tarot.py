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
from bunnyland.core.handlers import HandlerContext
from bunnyland.foundation.social.mechanics import bond_between
from bunnyland.foundation.storyteller.mechanics import IncidentBudgetComponent, StorytellerComponent

from bunnyland_fortunesim import (
    DivinerComponent,
    LuckComponent,
    Reading,
    ReadTarotHandler,
    TarotReadEvent,
    card_meaning,
    card_mood,
    compose_tarot_reading,
    draw_card,
    draw_orientation,
    incident_imminent,
    readings_of,
    spawn_charm,
    spawn_fortune_tool,
    tarot_fragments,
)
from bunnyland_fortunesim.tarot import (
    AUSPICIOUS,
    FORESHADOW_LINE,
    NEUTRAL,
    OMINOUS,
    TAROT_DECK,
)

EPOCH = 100


def _world():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Reading Tent")])
    reader = spawn_entity(
        actor.world,
        [IdentityComponent(name="Mystic", kind="character"), CharacterComponent()],
    )
    client = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="Bram", kind="character"),
            CharacterComponent(),
            LuckComponent(base=0.0, value=0.0),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), reader.id)
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), client.id)
    return actor, room, reader, client


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="read-tarot",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor, epoch=EPOCH):
    return HandlerContext(world=actor.world, epoch=epoch)


def _epoch_for(reader_id, want_mood):
    """Smallest epoch whose first draw has (or lacks) a mood, for deterministic branch tests."""
    for epoch in range(100, 200000, 100):
        card = draw_card(reader_id, 1, epoch)
        orientation = draw_orientation(reader_id, 1, epoch)
        if (card_mood(card[4], orientation) is not None) == want_mood:
            return epoch
    raise AssertionError("no epoch found")


# -- randomness / determinism (roadmap §6) ----------------------------------------------


def test_draw_is_deterministic_for_fixed_counter_and_epoch():
    draws = {draw_card("entity_7", 3, 555) for _ in range(5)}
    assert len(draws) == 1
    assert draw_card("entity_7", 3, 555) == draw_card("entity_7", 3, 555)


def test_successive_draws_differ():
    # Consecutive counters land on different cards for this seed...
    assert draw_card("entity_1", 1, 100) != draw_card("entity_1", 2, 100)
    assert draw_card("entity_1", 2, 100) != draw_card("entity_1", 3, 100)


def test_a_run_of_draws_is_varied_and_unguessable():
    cards = {draw_card("entity_9", n, 100)[0] for n in range(1, 12)}
    assert len(cards) >= 3


def test_orientation_is_upright_or_reversed():
    assert draw_orientation("entity_1", 1, 100) in {"upright", "reversed"}


def test_deck_is_sorted_and_named():
    keys = [card[0] for card in TAROT_DECK]
    assert keys == sorted(keys)
    assert all(card[1] for card in TAROT_DECK)  # every card has a display name


# -- card meaning & mood ----------------------------------------------------------------


def test_card_meaning_flips_with_orientation():
    card = TAROT_DECK[0]
    assert card_meaning(card, "upright") == card[2]
    assert card_meaning(card, "reversed") == card[3]


def test_card_mood_only_for_upright_toned_cards():
    assert card_mood(AUSPICIOUS, "upright") is not None
    assert card_mood(OMINOUS, "upright") is not None
    assert card_mood(NEUTRAL, "upright") is None
    assert card_mood(AUSPICIOUS, "reversed") is None
    assert card_mood(OMINOUS, "reversed") is None


def test_compose_reading_weaves_portent_when_foretold():
    plain = compose_tarot_reading("Bram", "The Sun", "upright", "joy", False)
    portent = compose_tarot_reading("Bram", "The Sun", "upright", "joy", True)
    assert FORESHADOW_LINE not in plain
    assert FORESHADOW_LINE in portent
    reversed_line = compose_tarot_reading("Bram", "The Tower", "reversed", "averted", False)
    assert "reversed" in reversed_line


# -- happy path -------------------------------------------------------------------------


def test_read_tarot_emits_event_and_advances_counter():
    actor, _room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)

    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(client.id)})
    )

    assert result.ok
    event = result.events[0]
    assert isinstance(event, TarotReadEvent)
    assert event.reader_id == str(reader.id)
    assert event.client_id == str(client.id)
    expected = draw_card(str(reader.id), 1, EPOCH)
    assert event.card == expected[0]
    assert reader.get_component(DivinerComponent).draws == 1


def test_second_reading_advances_and_changes_the_draw():
    actor, _room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)
    handler = ReadTarotHandler()

    first = handler.execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(client.id)})
    )
    second = handler.execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(client.id)})
    )

    assert reader.get_component(DivinerComponent).draws == 2
    assert first.events[0].card == draw_card(str(reader.id), 1, EPOCH)[0]
    assert second.events[0].card == draw_card(str(reader.id), 2, EPOCH)[0]


def test_reading_records_typed_edge_and_grows_rapport():
    actor, _room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)

    ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(client.id)})
    )

    edges = readings_of(actor.world, reader)
    assert len(edges) == 1
    edge, target = edges[0]
    assert isinstance(edge, Reading)
    assert target == str(client.id)
    # Rapport routes through the core SocialBond edge, both directions.
    assert bond_between(actor.world, reader.id, client.id).familiarity > 0
    assert bond_between(actor.world, client.id, reader.id).familiarity > 0


def test_toned_card_attaches_a_mood_thought():
    from bunnyland.core.edges import HasThought

    actor, _room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)
    epoch = _epoch_for(str(reader.id), want_mood=True)

    ReadTarotHandler().execute(
        _ctx(actor, epoch), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(client.id)})
    )

    assert list(client.get_relationships(HasThought))


def test_neutral_card_attaches_no_mood():
    from bunnyland.core.edges import HasThought

    actor, _room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)
    epoch = _epoch_for(str(reader.id), want_mood=False)

    ReadTarotHandler().execute(
        _ctx(actor, epoch), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(client.id)})
    )

    assert not list(client.get_relationships(HasThought))


# -- foretelling / storyteller synergy --------------------------------------------------


def _add_storyteller(actor, *, enabled=True, next_incident_epoch=EPOCH + 100):
    return spawn_entity(
        actor.world,
        [
            StorytellerComponent(enabled=enabled, next_incident_epoch=next_incident_epoch),
            IncidentBudgetComponent(),
        ],
    )


def test_incident_imminent_true_when_storyteller_due_soon():
    actor, *_ = _world()
    _add_storyteller(actor, next_incident_epoch=EPOCH + 100)
    assert incident_imminent(actor.world, EPOCH) is True


def test_incident_imminent_false_when_disabled_or_far_off():
    actor, *_ = _world()
    _add_storyteller(actor, enabled=False, next_incident_epoch=EPOCH + 100)
    assert incident_imminent(actor.world, EPOCH) is False
    actor2, *_ = _world()
    _add_storyteller(actor2, next_incident_epoch=EPOCH + 10_000_000)
    assert incident_imminent(actor2.world, EPOCH) is False


def test_incident_imminent_false_standalone():
    # No storyteller loaded -> the synergy is simply dormant.
    actor, *_ = _world()
    assert incident_imminent(actor.world, EPOCH) is False


def test_reading_foreshadows_an_imminent_incident():
    actor, _room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)
    _add_storyteller(actor, next_incident_epoch=EPOCH + 100)

    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(client.id)})
    )

    assert result.events[0].foretold is True
    assert FORESHADOW_LINE in result.events[0].reading
    assert readings_of(actor.world, reader)[0][0].foretold is True


# -- prompt fragments -------------------------------------------------------------------


def test_tarot_fragment_for_a_diviner():
    actor, _room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)
    ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(client.id)})
    )
    assert any("cards" in line for line in tarot_fragments(actor.world, reader))


def test_tarot_fragment_absent_for_non_diviner():
    actor, _room, _reader, client = _world()
    assert tarot_fragments(actor.world, client) == []
    assert tarot_fragments(actor.world, None) == []


# -- rejections -------------------------------------------------------------------------


def test_rejects_invalid_character():
    actor, *_ = _world()
    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd("???", {"tool_id": "entity_1", "client_id": "entity_1"})
    )
    assert result.reason == "invalid character id"


def test_rejects_missing_character():
    actor, *_ = _world()
    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd("entity_9999", {"tool_id": "entity_1", "client_id": "entity_1"})
    )
    assert result.reason == "character does not exist"


def test_rejects_invalid_tool():
    actor, _room, reader, client = _world()
    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": "???", "client_id": str(client.id)})
    )
    assert result.reason == "invalid tool id"


def test_rejects_missing_tool():
    actor, _room, reader, client = _world()
    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": "entity_9999", "client_id": str(client.id)})
    )
    assert result.reason == "tool does not exist"


def test_rejects_unheld_tool():
    actor, room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world, room_id=room.id)  # on the floor
    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(client.id)})
    )
    assert result.reason == "you are not holding that tool"


def test_rejects_non_fortune_tool():
    actor, _room, reader, client = _world()
    lantern = spawn_entity(
        actor.world,
        [IdentityComponent(name="lantern", kind="item"), PortableComponent(), HoldableComponent()],
    )
    _hold(reader, lantern)
    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(lantern.id), "client_id": str(client.id)})
    )
    assert result.reason == "that is not a fortune-telling tool"


def test_rejects_invalid_client():
    actor, _room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)
    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": "???"})
    )
    assert result.reason == "invalid client id"


def test_rejects_missing_client():
    actor, _room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)
    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": "entity_9999"})
    )
    assert result.reason == "client does not exist"


def test_rejects_unreachable_client():
    actor, room, reader, client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)
    # Move the client into a separate room so they are out of reach.
    room.remove_relationship(Contains, client.id)
    far = spawn_entity(actor.world, [RoomComponent(title="Elsewhere")])
    far.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), client.id)
    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(client.id)})
    )
    assert result.reason == "the client is not here"


def test_rejects_non_character_client():
    actor, room, reader, _client = _world()
    tool = spawn_fortune_tool(actor.world)
    _hold(reader, tool)
    charm = spawn_charm(actor.world, room_id=room.id)  # a reachable item, not a character
    result = ReadTarotHandler().execute(
        _ctx(actor), _cmd(reader.id, {"tool_id": str(tool.id), "client_id": str(charm.id)})
    )
    assert result.reason == "you can only read a fortune for a character"
