"""Luck banding and the deterministic weighting hook.

Two responsibilities, kept free of any component imports so both ``components.py`` and the
mechanic modules can depend on them without a cycle:

1. **Bands** — map a numeric luck value to a coarse, stable label (``blessed`` .. ``cursed``)
   so prompts and events do not flicker under tiny numeric changes.
2. **Determinism** — the luck-biased selection hook. Every "luck-biased outcome" and every
   fortune reading in this pack is derived from a :mod:`hashlib` digest of stable ids plus the
   world ``epoch``, reduced over a **sorted** table. There is deliberately no ``random`` and no
   wall-clock time anywhere in this package, so the same world state always yields the same
   result regardless of ``PYTHONHASHSEED``.
"""

from __future__ import annotations

import hashlib
import math

# --------------------------------------------------------------------------------------
# Luck bands (a higher value is luckier)
# --------------------------------------------------------------------------------------

CURSED = "cursed"
UNLUCKY = "unlucky"
EVEN = "even"
LUCKY = "lucky"
BLESSED = "blessed"

#: Bands in ascending fortune; the index is a stable rank.
BAND_ORDER = (CURSED, UNLUCKY, EVEN, LUCKY, BLESSED)

#: Lower edges (inclusive) for each non-cursed band, in descending order.
BLESSED_AT = 2.0
LUCKY_AT = 0.5
EVEN_AT = -0.5
UNLUCKY_AT = -2.0


def luck_band(value: float) -> str:
    """Map a luck value to its coarse band (``even`` is neutral)."""
    if value >= BLESSED_AT:
        return BLESSED
    if value >= LUCKY_AT:
        return LUCKY
    if value >= EVEN_AT:
        return EVEN
    if value >= UNLUCKY_AT:
        return UNLUCKY
    return CURSED


def band_rank(band: str) -> int:
    """Ascending rank of a band (``cursed`` is ``0``)."""
    return BAND_ORDER.index(band)


# --------------------------------------------------------------------------------------
# Determinism: hash of stable ids + epoch, reduced over sorted tables
# --------------------------------------------------------------------------------------


def digest_unit(*parts: object) -> float:
    """Return a stable float in ``[0.0, 1.0)`` derived from ``parts``.

    ``parts`` are stringified and joined, so any mix of stable ids, epoch, and table keys
    produces the same value on every machine and every interpreter run.
    """
    key = "|".join(str(part) for part in parts)
    raw = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(raw[:8], "big") / float(1 << 64)


def luck_bias(luck: float) -> float:
    """Map a luck value to a selection bias in ``(-0.4, 0.4)`` (lucky biases upward)."""
    return math.tanh(luck * 0.25) * 0.4


def biased_index(count: int, luck: float, *parts: object) -> int:
    """Pick an index in ``range(count)`` from a sorted table, biased upward by ``luck``.

    Index ``0`` is the least fortunate entry and ``count - 1`` the most, so positive luck
    nudges the deterministic pick toward the auspicious end of the table without ever
    rolling dice at runtime. Raises ``ValueError`` for an empty table.
    """
    if count <= 0:
        raise ValueError("biased_index requires a non-empty table")
    position = digest_unit(*parts) + luck_bias(luck)
    clamped = min(0.999999, max(0.0, position))
    return int(clamped * count)


def luck_multiplier(luck: float) -> float:
    """Weighting multiplier an opt-in pack can apply to a favourable outcome's odds.

    Returns ``1.0`` at neutral luck, rising above ``1.0`` when lucky and falling toward (but
    never reaching) ``0.0`` when cursed. This is the *weighting* hook the concept calls for:
    luck shifts how heavily an outcome is weighted; it never performs the roll itself.
    """
    return math.exp(luck * 0.2)


__all__ = [
    "BAND_ORDER",
    "BLESSED",
    "CURSED",
    "EVEN",
    "LUCKY",
    "UNLUCKY",
    "band_rank",
    "biased_index",
    "digest_unit",
    "luck_band",
    "luck_bias",
    "luck_multiplier",
]
