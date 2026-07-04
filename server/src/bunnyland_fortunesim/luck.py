"""The luck stat: materialise each character's total luck and colour their mood.

:class:`LuckConsequence` runs every tick. For each character with a :class:`LuckComponent`
it recomputes the materialised ``value`` from three parts — intrinsic ``base``, the bonus
from held charms, and a temporary ritual boost that expires on its own epoch — and emits a
:class:`LuckChangedEvent` when the coarse band crosses.

The mood reuse lives here too: :func:`remember_fortune` spawns a decaying
:class:`~bunnyland.core.components.ThoughtComponent` carrying an
:class:`~bunnyland.core.components.AffectDelta`, exactly the way the core affect reactor turns
discrete events into feelings. The stock ``AffectAggregation`` consequence folds that thought
into the character's :class:`~bunnyland.core.components.AffectComponent`, so good and bad
fortune reads through as real mood without this pack owning any mood machinery.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.components import AffectDelta, ThoughtComponent
from bunnyland.core.ecs import replace_component, spawn_entity
from bunnyland.core.edges import HasThought
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.prompts.context import ComponentPromptContext
from relics import Entity, World

from .bands import BLESSED, CURSED, LUCKY, UNLUCKY, luck_band
from .charms import held_charm_bonus
from .components import LuckComponent

#: How long a fortune mood lingers before it decays (game seconds).
FORTUNE_MOOD_TTL = 2 * 3600

#: Per-band mood: ``(label, text, delta)``. The neutral ``even`` band produces no mood.
_MOOD_BY_BAND: dict[str, tuple[str, str, AffectDelta]] = {
    BLESSED: (
        "buoyant",
        "A charmed, weightless feeling lifts you.",
        AffectDelta(valence=8, confidence=4),
    ),
    LUCKY: ("hopeful", "You feel a little lucky.", AffectDelta(valence=5)),
    UNLUCKY: (
        "uneasy",
        "A prickle of bad luck unsettles you.",
        AffectDelta(valence=-5, stress=3),
    ),
    CURSED: (
        "doomed",
        "Dread of rotten luck sits heavy on you.",
        AffectDelta(valence=-8, fear=4, stress=5),
    ),
}


class LuckChangedEvent(DomainEvent):
    """A character's luck crossed into a new band."""

    value: float
    band: str


def effective_luck(entity: Entity) -> float:
    """Return an entity's materialised luck ``value`` (``0.0`` if it has no luck)."""
    if not entity.has_component(LuckComponent):
        return 0.0
    return entity.get_component(LuckComponent).value


def fortune_mood(band: str) -> tuple[str, str, AffectDelta] | None:
    """Return the ``(label, text, delta)`` mood for a luck band, or ``None`` if neutral."""
    return _MOOD_BY_BAND.get(band)


def remember_fortune(
    world: World, character: Entity, band: str, epoch: int, *, source_event_id: str | None = None
) -> Entity | None:
    """Attach a decaying fortune-mood thought to ``character`` (reuses the affect system).

    Returns the spawned thought entity, or ``None`` for the neutral ``even`` band (which
    carries no mood worth remembering).
    """
    mood = fortune_mood(band)
    if mood is None:
        return None
    label, text, delta = mood
    thought = spawn_entity(
        world,
        [
            ThoughtComponent(
                label=label,
                text=text,
                affect_delta=delta,
                created_at_epoch=epoch,
                expires_at_epoch=epoch + FORTUNE_MOOD_TTL,
                source_event_id=source_event_id,
            )
        ],
    )
    character.add_relationship(HasThought(), thought.id)
    return thought


class LuckConsequence:
    """Recompute every character's materialised luck each tick from charms and rituals."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for character in list(world.query().with_all([LuckComponent]).execute_entities()):
            event = self._update_character(world, epoch, character)
            if event is not None:
                events.append(event)
        return events

    def _update_character(self, world: World, epoch: int, character: Entity):
        component = character.get_component(LuckComponent)
        charm_bonus = held_charm_bonus(world, character)
        if epoch < component.ritual_until_epoch:
            ritual_bonus = component.ritual_bonus
            ritual_until = component.ritual_until_epoch
        else:
            ritual_bonus = 0.0
            ritual_until = 0
        value = component.base + charm_bonus + ritual_bonus

        unchanged = (
            charm_bonus == component.charm_bonus
            and ritual_bonus == component.ritual_bonus
            and ritual_until == component.ritual_until_epoch
            and value == component.value
        )
        if unchanged:
            return None

        old_band = luck_band(component.value)
        updated = replace(
            component,
            charm_bonus=charm_bonus,
            ritual_bonus=ritual_bonus,
            ritual_until_epoch=ritual_until,
            value=value,
        )
        replace_component(character, updated)
        new_band = luck_band(value)
        if new_band == old_band:
            return None
        return LuckChangedEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.PRIVATE,
                actor_id=str(character.id),
                value=value,
                band=new_band,
            )
        )


def luck_fragments(world: World, character: Entity) -> list[str]:
    """First-person luck-band line for a character's own prompt."""
    if character is None or not character.has_component(LuckComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, character)
    return list(character.get_component(LuckComponent).prompt_fragments(ctx))


__all__ = [
    "FORTUNE_MOOD_TTL",
    "LuckChangedEvent",
    "LuckConsequence",
    "effective_luck",
    "fortune_mood",
    "luck_fragments",
    "remember_fortune",
]
