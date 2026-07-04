"""The three public components of the fortune pack.

Everything here is a frozen pydantic dataclass subclassing :class:`relics.Component`, updated
elsewhere with ``replace_component(entity, replace(component, ...))``.

- :class:`LuckComponent` is a deliberately **open** stat other packs can read. Its ``value``
  field is the materialised total luck (base + charms + active rituals) maintained by
  :class:`~bunnyland_fortunesim.luck.LuckConsequence`, so a reader only needs ``value``.
- :class:`CharmComponent` sits on a carried item and shifts its holder's luck while held.
- :class:`OmenComponent` sits on a room and colours the scene foreboding or auspicious.
"""

from __future__ import annotations

from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component

from .bands import BLESSED, CURSED, LUCKY, UNLUCKY, luck_band

# --------------------------------------------------------------------------------------
# Luck — an open stat other packs may read
# --------------------------------------------------------------------------------------

#: First-person prompt line per luck band (``even`` is silent — nothing worth mentioning).
_LUCK_LINES: dict[str, str] = {
    BLESSED: "Fortune beams on you today — everything seems to break your way.",
    LUCKY: "Fortune favors you today.",
    UNLUCKY: "You feel snakebit; nothing is quite going your way.",
    CURSED: "A black cloud hangs over you — luck has abandoned you utterly.",
}


@dataclass(frozen=True)
class LuckComponent(Component):
    """A character's luck. ``value`` is the materialised total any pack may read.

    ``base`` is intrinsic luck; ``charm_bonus`` is recomputed each tick from held charms;
    ``ritual_bonus`` is a temporary superstition boost that expires at ``ritual_until_epoch``.
    ``value`` is the sum of the currently active parts, kept up to date by the luck
    consequence so other systems never have to recompute it.
    """

    base: float = 0.0
    charm_bonus: float = 0.0
    ritual_bonus: float = 0.0
    ritual_until_epoch: int = 0
    value: float = 0.0

    @property
    def band(self) -> str:
        return luck_band(self.value)

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        # Only the character themselves senses their own luck.
        if not ctx.is_first_person:
            return ()
        line = _LUCK_LINES.get(self.band)
        return (line,) if line is not None else ()


# --------------------------------------------------------------------------------------
# Charms & talismans — carried luck modifiers
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CharmComponent(Component):
    """A carried charm or talisman. ``luck`` is added to its holder while held.

    A positive ``luck`` is a lucky charm (rabbit's foot, four-leaf clover); a negative
    ``luck`` is a cursed trinket that drags its holder down.
    """

    luck: float = 1.0
    label: str = "charm"

    @property
    def cursed(self) -> bool:
        return self.luck < 0.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person:
            return ()
        if self.cursed:
            return (f"You carry a cursed {self.label}; it feels wrong in your hand.",)
        return (f"You carry a lucky {self.label}.",)


# --------------------------------------------------------------------------------------
# Omens — a room's foreboding or auspicious cast
# --------------------------------------------------------------------------------------

FOREBODING = "foreboding"
AUSPICIOUS = "auspicious"


@dataclass(frozen=True)
class OmenComponent(Component):
    """An omen colouring a room. ``kind`` is ``foreboding`` or ``auspicious``.

    ``source`` records who placed it: ``worldgen`` omens are sticky scene-setting, while
    ``dynamic`` omens are managed (added and cleared) by the omen consequence as charms come
    and go.
    """

    kind: str = FOREBODING
    omen: str = "a stray black cat"
    text: str = "A black cat crosses your path."
    source: str = "dynamic"

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        return (self.text,)


__all__ = [
    "AUSPICIOUS",
    "FOREBODING",
    "CharmComponent",
    "LuckComponent",
    "OmenComponent",
]
