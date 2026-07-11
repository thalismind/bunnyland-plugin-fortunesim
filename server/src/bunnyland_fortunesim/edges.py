"""Typed relationship edges for the fortune pack's v2 mechanics.

Relationships are modelled as their own :class:`~relics.Edge` subclasses — one index per edge
type — rather than lists on a component:

- :class:`Reading` is the directed *fortune-teller -> client* link recording a tarot reading
  that was given. Every reading a diviner performs adds one such edge, so a teller's whole
  history with a querent is just the ``Reading`` edges between them.

Rapport between a teller and a client is **not** a new edge here: affective bonds route through
the core :class:`~bunnyland.foundation.social.mechanics.SocialBond` typed edge (see :mod:`.tarot`).
"""

from __future__ import annotations

from pydantic.dataclasses import dataclass
from relics import Edge

from .bands import EVEN


@dataclass(frozen=True)
class Reading(Edge):
    """fortune-teller -> client: a single tarot reading that was given (directed).

    ``card``/``orientation``/``meaning`` capture what was drawn, ``band`` the client's luck at
    the time, and ``foretold`` records whether the reading foreshadowed a gathering storyteller
    incident.
    """

    epoch: int = 0
    card: str = ""
    orientation: str = "upright"
    meaning: str = ""
    band: str = EVEN
    foretold: bool = False


__all__ = ["Reading"]
