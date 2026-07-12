"""Fortune-teller & tarot: draw a card for a client with controlled randomness.

The headline v2 mechanic. A diviner reads a **client** (another character in reach) with a held
tarot tool via the ``read-tarot`` verb. Unlike the deterministic self-reading in :mod:`.fortune`,
a tarot draw wants to feel *unpredictable* — yet the codebase forbids ``random`` and wall-clock
time so tests and the coverage gate stay stable.

Controlled randomness (roadmap §6): each diviner carries a :class:`DivinerComponent` with a
**draw counter** that advances on every reading. The drawn card is a :mod:`hashlib` digest of the
diviner id, that ever-increasing counter, and the world ``epoch`` — reduced over the **sorted**
deck. So a fixed ``(counter, epoch)`` always yields the same card (fully testable), successive
draws move to a fresh, effectively unguessable card, and the result never depends on
``PYTHONHASHSEED``.

Core reuse: the card's tone drives an :class:`~bunnyland.core.components.AffectComponent` mood on
the client (through the stock ``ThoughtComponent`` -> affect flow); rapport routes through the
Foundation Social's ``SocialBond`` typed edge; and when a storyteller incident
is imminent the reading **foreshadows** it. Each reading is recorded as a :class:`.edges.Reading`
typed edge from the teller to the client.

Validation order: invalid caster -> missing caster -> invalid tool -> missing tool -> not held ->
wrong kind -> invalid client -> missing/unreachable client -> not a character -> apply.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import CharacterComponent, spawn_entity
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.components import AffectDelta, ThoughtComponent
from bunnyland.core.ecs import entity_name, replace_component
from bunnyland.core.edges import HasThought
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_entity,
    require_reachable_entity,
)
from bunnyland.foundation.social.mechanics import adjust_bond
from bunnyland.foundation.storyteller.mechanics import IncidentBudgetComponent, StorytellerComponent
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .bands import digest_unit, luck_band
from .edges import Reading
from .fortune import FortuneToolComponent
from .luck import effective_luck
from .spatial import holder_of, room_of

#: Card tone.
AUSPICIOUS = "auspicious"
OMINOUS = "ominous"
NEUTRAL = "neutral"

#: The deck: ``(key, name, upright, reversed, tone)`` sorted by key for stable indexing.
#: Generic tarot arcana — no brand names.
TAROT_DECK: tuple[tuple[str, str, str, str, str], ...] = tuple(
    sorted(
        (
            (
                "death",
                "Death",
                "an ending clears the way for what comes next",
                "you cling to what is already passing",
                OMINOUS,
            ),
            (
                "the-devil",
                "The Devil",
                "a temptation binds you tighter than you know",
                "old chains loosen and fall away",
                OMINOUS,
            ),
            (
                "the-empress",
                "The Empress",
                "abundance and growth gather around you",
                "something you tend is being stifled",
                AUSPICIOUS,
            ),
            (
                "the-fool",
                "The Fool",
                "a fresh, open-hearted beginning beckons",
                "a reckless step invites folly",
                NEUTRAL,
            ),
            (
                "the-hanged-man",
                "The Hanged Man",
                "surrender reveals a new way to see",
                "a sacrifice is being wasted",
                NEUTRAL,
            ),
            (
                "the-hermit",
                "The Hermit",
                "quiet reflection lights the path",
                "loneliness weighs heavier than it should",
                NEUTRAL,
            ),
            (
                "the-lovers",
                "The Lovers",
                "a bond deepens into real harmony",
                "a bond of yours is being tested",
                AUSPICIOUS,
            ),
            (
                "the-magician",
                "The Magician",
                "you hold the power to shape events",
                "your will is scattered and unfocused",
                AUSPICIOUS,
            ),
            (
                "the-moon",
                "The Moon",
                "hidden things stir beneath the surface",
                "a lingering confusion finally clears",
                OMINOUS,
            ),
            (
                "the-star",
                "The Star",
                "hope and renewal are close at hand",
                "faith wavers just when you need it",
                AUSPICIOUS,
            ),
            (
                "the-sun",
                "The Sun",
                "warmth, joy, and plain success shine on you",
                "a passing cloud dims your gladness",
                AUSPICIOUS,
            ),
            (
                "the-tower",
                "The Tower",
                "a sudden upheaval shakes what seemed solid",
                "you narrowly avert a collapse",
                OMINOUS,
            ),
            (
                "the-wheel",
                "The Wheel of Fortune",
                "fortune's wheel turns your way",
                "fortune's wheel turns against you",
                NEUTRAL,
            ),
            (
                "the-world",
                "The World",
                "a long effort reaches its fulfilment",
                "a journey stalls just short of its end",
                AUSPICIOUS,
            ),
            (
                "temperance",
                "Temperance",
                "patience and balance carry you through",
                "excess is knocking you off balance",
                NEUTRAL,
            ),
        )
    )
)

#: How long a tarot mood lingers before it decays (game seconds).
TAROT_MOOD_TTL = 2 * 3600

#: Per-tone mood for an **upright** card; a reversed card blocks/releases the mood (``None``).
_TONE_MOOD: dict[str, tuple[str, str, AffectDelta]] = {
    AUSPICIOUS: (
        "heartened",
        "The reading leaves you quietly hopeful.",
        AffectDelta(valence=6, confidence=3),
    ),
    OMINOUS: (
        "shaken",
        "The reading leaves a cold unease in you.",
        AffectDelta(valence=-6, stress=3, fear=2),
    ),
}

#: An incident this close (in game seconds) reads as "gathering" and gets foreshadowed.
FORESHADOW_WINDOW = 6 * 3600

#: The portent line woven into a reading that foreshadows a coming storyteller incident.
FORESHADOW_LINE = "The cards shiver in your hands — something is gathering on the horizon."


@dataclass(frozen=True)
class DivinerComponent(Component):
    """A fortune-teller's running draw counter (the controlled-randomness seed)."""

    draws: int = 0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person:
            return ()
        return ("You have the knack for reading the cards.",)


class TarotReadEvent(DomainEvent):
    """A diviner read a tarot card for a client."""

    reader_id: str
    client_id: str
    card: str
    orientation: str
    meaning: str
    reading: str
    band: str
    foretold: bool


def draw_card(reader_id: str, draw_count: int, epoch: int) -> tuple[str, str, str, str, str]:
    """Return the deck entry drawn for ``(reader, draw_count, epoch)`` (deterministic)."""
    index = int(digest_unit(reader_id, draw_count, epoch) * len(TAROT_DECK))
    return TAROT_DECK[index]


def draw_orientation(reader_id: str, draw_count: int, epoch: int) -> str:
    """Return ``"upright"`` or ``"reversed"`` for a draw (deterministic, hash-derived)."""
    unit = digest_unit(reader_id, draw_count, epoch, "orientation")
    return "reversed" if unit < 0.5 else "upright"


def card_meaning(card: tuple[str, str, str, str, str], orientation: str) -> str:
    """The upright or reversed meaning line for a drawn card."""
    _key, _name, upright, reversed_, _tone = card
    return reversed_ if orientation == "reversed" else upright


def card_mood(tone: str, orientation: str) -> tuple[str, str, AffectDelta] | None:
    """The ``(label, text, delta)`` mood a card casts, or ``None``.

    An upright card carries its tone's mood; a reversed card blocks (auspicious) or releases
    (ominous) it, so only upright auspicious/ominous cards leave a feeling.
    """
    if orientation == "reversed":
        return None
    return _TONE_MOOD.get(tone)


def remember_tarot(
    world: World,
    client: Entity,
    mood: tuple[str, str, AffectDelta],
    epoch: int,
    *,
    source_event_id: str | None = None,
) -> Entity:
    """Attach a decaying tarot-mood thought to ``client`` (reuses the core affect flow)."""
    label, text, delta = mood
    thought = spawn_entity(
        world,
        [
            ThoughtComponent(
                label=label,
                text=text,
                affect_delta=delta,
                created_at_epoch=epoch,
                expires_at_epoch=epoch + TAROT_MOOD_TTL,
                source_event_id=source_event_id,
            )
        ],
    )
    client.add_relationship(HasThought(), thought.id)
    return thought


def incident_imminent(world: World, epoch: int) -> bool:
    """True if a storyteller has an enabled incident due within :data:`FORESHADOW_WINDOW`.

    Dormant by design when no storyteller is loaded: with no ``StorytellerComponent`` entity the
    reading simply carries no foretelling.
    """
    query = world.query().with_all([StorytellerComponent, IncidentBudgetComponent])
    for entity in query.execute_entities():
        storyteller = entity.get_component(StorytellerComponent)
        countdown = storyteller.next_incident_epoch - epoch
        if storyteller.enabled and 0 <= countdown <= FORESHADOW_WINDOW:
            return True
    return False


def compose_tarot_reading(
    client_name: str, card_name: str, orientation: str, meaning: str, foretold: bool
) -> str:
    """Assemble the reading prose from the drawn card, its meaning, and any portent."""
    facing = " reversed" if orientation == "reversed" else ""
    lines = [f"For {client_name} you draw {card_name}{facing}: {meaning}."]
    if foretold:
        lines.append(FORESHADOW_LINE)
    return " ".join(lines)


class ReadTarotHandler:
    """Read a tarot card for a reachable client with a held tarot tool."""

    command_type = "read-tarot"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        reader_id, reader, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        tool_id, tool, rejection = require_entity(
            ctx,
            command.payload.get("tool_id"),
            invalid_reason="invalid tool id",
            missing_reason="tool does not exist",
        )
        if rejection is not None:
            return rejection
        holder = holder_of(ctx.world, tool_id)
        if holder is None or holder.id != reader_id:
            return rejected("you are not holding that tool")
        if not tool.has_component(FortuneToolComponent):
            return rejected("that is not a fortune-telling tool")

        client_id, client, rejection = require_reachable_entity(
            ctx,
            reader,
            command.payload.get("client_id"),
            invalid_reason="invalid client id",
            missing_reason="client does not exist",
            unreachable_reason="the client is not here",
        )
        if rejection is not None:
            return rejection
        if not client.has_component(CharacterComponent):
            return rejected("you can only read a fortune for a character")

        # Advance the draw counter — the controlled-randomness seed.
        diviner = (
            reader.get_component(DivinerComponent)
            if reader.has_component(DivinerComponent)
            else DivinerComponent()
        )
        draws = diviner.draws + 1
        if reader.has_component(DivinerComponent):
            replace_component(reader, replace(diviner, draws=draws))
        else:
            reader.add_component(DivinerComponent(draws=draws))

        card = draw_card(str(reader_id), draws, ctx.epoch)
        orientation = draw_orientation(str(reader_id), draws, ctx.epoch)
        key, name, _up, _rev, tone = card
        meaning = card_meaning(card, orientation)
        foretold = incident_imminent(ctx.world, ctx.epoch)
        band = luck_band(effective_luck(client))
        reading = compose_tarot_reading(entity_name(client), name, orientation, meaning, foretold)

        room = room_of(ctx.world, reader_id)
        event = TarotReadEvent(
            **ctx.event_base(
                visibility=EventVisibility.ROOM,
                actor_id=str(reader_id),
                room_id=str(room.id) if room is not None else None,
                target_ids=(str(client_id), str(tool_id)),
                reader_id=str(reader_id),
                client_id=str(client_id),
                card=key,
                orientation=orientation,
                meaning=meaning,
                reading=reading,
                band=band,
                foretold=foretold,
            )
        )

        # Record the reading as a typed teller -> client edge.
        reader.add_relationship(
            Reading(
                epoch=ctx.epoch,
                card=key,
                orientation=orientation,
                meaning=meaning,
                band=band,
                foretold=foretold,
            ),
            client_id,
        )
        # Rapport routes through the core SocialBond typed edge (both directions).
        adjust_bond(ctx.world, reader_id, client_id, {"familiarity": 0.05, "affinity": 0.03})
        adjust_bond(ctx.world, client_id, reader_id, {"familiarity": 0.05, "trust": 0.02})
        # The card's tone reads through as a real mood via the core affect flow.
        mood = card_mood(tone, orientation)
        if mood is not None:
            remember_tarot(ctx.world, client, mood, ctx.epoch, source_event_id=event.event_id)
        return ok(event)


def readings_of(world: World, teller: Entity) -> list[tuple[Reading, str]]:
    """Every reading a teller has given, as ``(edge, client_id)`` pairs."""
    return [(edge, str(target)) for edge, target in teller.get_relationships(Reading)]


def tarot_fragments(world: World, character: Entity) -> list[str]:
    """First-person diviner line for a character's own prompt."""
    if character is None or not character.has_component(DivinerComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, character)
    return list(character.get_component(DivinerComponent).prompt_fragments(ctx))


READ_TAROT_DEF = ActionDefinition(
    command_type="read-tarot",
    title="Read tarot",
    description="Read a tarot card for someone with a tarot deck you are holding.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "tool_id": ActionArgument(
            title="Tarot tool",
            description="The tarot deck you are holding.",
            kind="entity",
            required=True,
        ),
        "client_id": ActionArgument(
            title="Client",
            description="The character whose fortune you are reading.",
            kind="entity",
            required=True,
        ),
    },
)

TAROT_ACTION_DEFINITIONS = (READ_TAROT_DEF,)
TAROT_ACTION_HANDLERS = (ReadTarotHandler,)


__all__ = [
    "AUSPICIOUS",
    "FORESHADOW_LINE",
    "FORESHADOW_WINDOW",
    "NEUTRAL",
    "OMINOUS",
    "READ_TAROT_DEF",
    "TAROT_ACTION_DEFINITIONS",
    "TAROT_ACTION_HANDLERS",
    "TAROT_DECK",
    "TAROT_MOOD_TTL",
    "DivinerComponent",
    "ReadTarotHandler",
    "TarotReadEvent",
    "card_meaning",
    "card_mood",
    "compose_tarot_reading",
    "draw_card",
    "draw_orientation",
    "incident_imminent",
    "readings_of",
    "remember_tarot",
    "tarot_fragments",
]
