"""Runtime wiring: register the per-tick consequences on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .jinx import JinxConsequence
from .luck import LuckConsequence
from .omens import OmenConsequence


def install_fortunesim(actor: WorldActor) -> None:
    """Register the luck consequence (a ``service_factories`` entry)."""
    actor.register_consequence(LuckConsequence())


def install_fortunesim_omens(actor: WorldActor) -> None:
    """Register the omen consequence (a ``service_factories`` entry)."""
    actor.register_consequence(OmenConsequence())


def install_fortunesim_jinx(actor: WorldActor) -> None:
    """Register the jinx consequence: paces mishaps and feeds storyteller pressure."""
    actor.register_consequence(JinxConsequence())


__all__ = ["install_fortunesim", "install_fortunesim_jinx", "install_fortunesim_omens"]
