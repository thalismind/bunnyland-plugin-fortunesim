"""Bunnyland plugin entrypoint for the out-of-tree fortunesim pack."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .charms import charm_fragments
from .components import CharmComponent, LuckComponent, OmenComponent
from .enrichment import FortuneWorldgenHook
from .fortune import (
    FORTUNE_ACTION_DEFINITIONS,
    FORTUNE_ACTION_HANDLERS,
    FortuneReadEvent,
    FortuneToolComponent,
)
from .install import install_fortunesim, install_fortunesim_omens
from .luck import LuckChangedEvent, luck_fragments
from .omens import OmenClearedEvent, OmenSightedEvent, omen_fragments
from .superstition import (
    SUPERSTITION_ACTION_DEFINITIONS,
    SUPERSTITION_ACTION_HANDLERS,
    WardLuckEvent,
)

PLUGIN_ID = "bunnyland.fortunesim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Fortunesim",
        version="0.1.0",
        default_enabled=True,
        ecs=EcsContribution(
            components=(
                LuckComponent,
                CharmComponent,
                OmenComponent,
                FortuneToolComponent,
            ),
        ),
        commands=CommandContribution(
            action_handlers=FORTUNE_ACTION_HANDLERS + SUPERSTITION_ACTION_HANDLERS,
            action_definitions=FORTUNE_ACTION_DEFINITIONS + SUPERSTITION_ACTION_DEFINITIONS,
            typed_events=(
                LuckChangedEvent,
                OmenSightedEvent,
                OmenClearedEvent,
                FortuneReadEvent,
                WardLuckEvent,
            ),
        ),
        runtime=RuntimeContribution(
            service_factories=(install_fortunesim, install_fortunesim_omens),
        ),
        content=ContentContribution(
            prompt_fragments=(luck_fragments, charm_fragments, omen_fragments),
            worldgen_hooks=(FortuneWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
