"""World-generation enrichment: scatter charms and cursed trinkets, tag ominous locales.

Generated entities expose semantic ``tags``/``wants``/``needs`` and an intent
``description``. This hook scans that text and, without the core generator knowing this plugin
exists:

- turns a generated object that reads as a lucky charm into a :class:`CharmComponent` (or a
  cursed trinket into a negative one), and
- casts a generated room that reads as ominous or auspicious with a sticky worldgen
  :class:`OmenComponent`.
"""

from __future__ import annotations

from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import (
    GeneratedEntityEvent,
    ObjectGeneratedEvent,
    RoomGeneratedEvent,
)
from bunnyland.core.world_actor import WorldActor

from .components import AUSPICIOUS, FOREBODING, CharmComponent, OmenComponent

#: Words marking a generated object as a cursed trinket (checked before lucky terms).
CURSED_TERMS = (
    "cursed",
    "hexed",
    "jinxed",
    "ill-omened",
    "haunted trinket",
    "broken mirror",
    "malefic",
)

#: Words marking a generated object as a lucky charm.
LUCKY_CHARM_TERMS = (
    "charm",
    "talisman",
    "amulet",
    "clover",
    "rabbit's foot",
    "rabbits foot",
    "horseshoe",
    "wishbone",
    "lucky",
    "four-leaf",
)

#: Words marking a generated room as an ominous locale.
OMINOUS_TERMS = (
    "ominous",
    "haunted",
    "cursed",
    "graveyard",
    "crypt",
    "tomb",
    "forsaken",
    "eerie",
    "dreadful",
    "gloomy",
    "abandoned",
    "sinister",
)

#: Words marking a generated room as an auspicious locale.
AUSPICIOUS_TERMS = (
    "blessed",
    "hallowed",
    "sacred",
    "shrine",
    "sunlit",
    "serene",
    "auspicious",
    "hopeful",
)


def _text(event: GeneratedEntityEvent) -> str:
    generation = event.generation
    return " ".join(
        (
            event.entity_kind,
            generation.description,
            *generation.tags,
            *generation.wants,
            *generation.needs,
        )
    ).casefold()


def _mentions(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


class FortuneWorldgenHook:
    """Tag generated charms/trinkets and cast ominous or auspicious rooms."""

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(ObjectGeneratedEvent, self._on_object)
        actor.bus.subscribe(RoomGeneratedEvent, self._on_room)

    def _entity(self, entity_id: str):
        parsed = parse_entity_id(entity_id)
        if parsed is None or not self._actor.world.has_entity(parsed):
            return None
        return self._actor.world.get_entity(parsed)

    def _on_object(self, event: ObjectGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None or entity.has_component(CharmComponent):
            return
        text = _text(event)
        if _mentions(text, CURSED_TERMS):
            replace_component(entity, CharmComponent(luck=-1.5, label="trinket"))
        elif _mentions(text, LUCKY_CHARM_TERMS):
            replace_component(entity, CharmComponent(luck=1.0, label="charm"))

    def _on_room(self, event: RoomGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None or entity.has_component(OmenComponent):
            return
        text = _text(event)
        if _mentions(text, OMINOUS_TERMS):
            replace_component(
                entity,
                OmenComponent(
                    kind=FOREBODING,
                    omen="ominous-locale",
                    text="An oppressive dread hangs over this place.",
                    source="worldgen",
                ),
            )
        elif _mentions(text, AUSPICIOUS_TERMS):
            replace_component(
                entity,
                OmenComponent(
                    kind=AUSPICIOUS,
                    omen="blessed-locale",
                    text="A gentle, blessed calm suffuses this place.",
                    source="worldgen",
                ),
            )


__all__ = [
    "AUSPICIOUS_TERMS",
    "CURSED_TERMS",
    "LUCKY_CHARM_TERMS",
    "OMINOUS_TERMS",
    "FortuneWorldgenHook",
]
