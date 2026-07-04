"""Omens: read the world and cast a room foreboding or auspicious.

:class:`OmenConsequence` manages **dynamic** omens each tick. It looks for charms lying loose
in a room: a cursed trinket on the floor throws the room foreboding, a lucky charm left out
casts it auspicious, and clearing the charms lifts the omen again. The omen's *text* is chosen
deterministically from a sorted table via a digest of the room id and a coarse epoch bucket —
no randomness, so the same scene always narrates the same way.

**Worldgen** omens (``source="worldgen"``) are sticky scene-setting the consequence never
touches, so an ominous locale stays ominous. :func:`omen_fragments` renders whichever omen a
character's room carries into prompts, turning the LLM into a spooky (or hopeful) narrator.
"""

from __future__ import annotations

from bunnyland.core import RoomComponent
from bunnyland.core.ecs import contents, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.prompts.context import ComponentPromptContext
from relics import Entity, World

from .bands import digest_unit
from .components import AUSPICIOUS, FOREBODING, CharmComponent, OmenComponent
from .spatial import room_of

#: The omen text is stable within a window this many epochs wide, then may rotate.
OMEN_PERIOD = 3600

#: Sorted foreboding omens: ``(key, text)`` ascending by key for stable indexing.
FOREBODING_OMENS: tuple[tuple[str, str], ...] = tuple(
    sorted(
        (
            ("black-cat", "A black cat crosses your path."),
            ("crow", "A crow watches you, unblinking, from the rafters."),
            ("guttering-candle", "A candle gutters though there is no draft."),
            ("shattered-mirror", "A shattered mirror throws your face back in pieces."),
            ("spilled-salt", "Spilled salt glitters in a broken line across the floor."),
        )
    )
)

#: Sorted auspicious omens.
AUSPICIOUS_OMENS: tuple[tuple[str, str], ...] = tuple(
    sorted(
        (
            ("horseshoe", "A horseshoe hangs bright and open-mouthed above the door."),
            ("morning-sun", "Warm morning light pools invitingly across the floor."),
            ("robin", "A robin sings clear and close at the windowsill."),
            ("shooting-star", "A shooting star streaks past the window."),
        )
    )
)

_OMENS_BY_KIND: dict[str, tuple[tuple[str, str], ...]] = {
    FOREBODING: FOREBODING_OMENS,
    AUSPICIOUS: AUSPICIOUS_OMENS,
}


class OmenSightedEvent(DomainEvent):
    """A dynamic omen appeared (or changed) in a room."""

    kind: str
    omen: str
    text: str


class OmenClearedEvent(DomainEvent):
    """A dynamic omen lifted from a room."""


def _pick_omen(kind: str, room_id: str, epoch: int) -> tuple[str, str]:
    table = _OMENS_BY_KIND[kind]
    bucket = epoch // OMEN_PERIOD
    index = int(digest_unit(room_id, bucket, kind) * len(table))
    return table[index]


def _desired_kind(world: World, room: Entity) -> str | None:
    """Foreboding if a cursed charm lies loose here, auspicious for a lucky one, else none."""
    has_cursed = False
    has_lucky = False
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if not entity.has_component(CharmComponent):
            continue
        if entity.get_component(CharmComponent).cursed:
            has_cursed = True
        else:
            has_lucky = True
    if has_cursed:
        return FOREBODING
    if has_lucky:
        return AUSPICIOUS
    return None


class OmenConsequence:
    """Add, update, and clear dynamic room omens from the charms lying around each tick."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for room in list(world.query().with_all([RoomComponent]).execute_entities()):
            event = self._update_room(world, epoch, room)
            if event is not None:
                events.append(event)
        return events

    def _update_room(self, world: World, epoch: int, room: Entity):
        existing = room.get_component(OmenComponent) if room.has_component(OmenComponent) else None
        # Worldgen omens are sticky scene-setting; never manage them dynamically.
        if existing is not None and existing.source == "worldgen":
            return None

        desired = _desired_kind(world, room)
        if desired is None:
            if existing is None:
                return None
            room.remove_component(OmenComponent)
            return OmenClearedEvent(
                **event_base(
                    epoch,
                    default_visibility=EventVisibility.ROOM,
                    room_id=str(room.id),
                    target_ids=(str(room.id),),
                )
            )

        omen_key, text = _pick_omen(desired, str(room.id), epoch)
        if existing is not None and existing.kind == desired and existing.omen == omen_key:
            return None
        replace_component(
            room, OmenComponent(kind=desired, omen=omen_key, text=text, source="dynamic")
        )
        return OmenSightedEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.ROOM,
                room_id=str(room.id),
                target_ids=(str(room.id),),
                kind=desired,
                omen=omen_key,
                text=text,
            )
        )


def omen_fragments(world: World, character: Entity) -> list[str]:
    """Render the omen colouring the character's current room, if any."""
    if character is None:
        return []
    room = room_of(world, character.id)
    if room is None or not room.has_component(OmenComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, room, room=room)
    return list(room.get_component(OmenComponent).prompt_fragments(ctx))


__all__ = [
    "AUSPICIOUS_OMENS",
    "FOREBODING_OMENS",
    "OMEN_PERIOD",
    "OmenClearedEvent",
    "OmenConsequence",
    "OmenSightedEvent",
    "omen_fragments",
]
