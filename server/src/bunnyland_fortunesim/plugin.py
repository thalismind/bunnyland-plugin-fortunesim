"""Bunnyland plugin entrypoint for the out-of-tree fortunesim pack."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    DependencyContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .charms import charm_fragments
from .components import CharmComponent, LuckComponent, OmenComponent
from .edges import Reading
from .enrichment import FortuneGenerationEnricher
from .fortune import (
    FORTUNE_ACTION_DEFINITIONS,
    FORTUNE_ACTION_HANDLERS,
    FortuneReadEvent,
    FortuneToolComponent,
)
from .install import (
    install_fortunesim,
    install_fortunesim_jinx,
    install_fortunesim_omens,
)
from .jinx import (
    JINX_ACTION_DEFINITIONS,
    JINX_ACTION_HANDLERS,
    JinxComponent,
    JinxLaidEvent,
    JinxLiftedEvent,
    JinxMishapEvent,
    jinx_fragments,
)
from .luck import LuckChangedEvent, luck_fragments
from .omens import OmenClearedEvent, OmenSightedEvent, omen_fragments
from .superstition import (
    SUPERSTITION_ACTION_DEFINITIONS,
    SUPERSTITION_ACTION_HANDLERS,
    WardLuckEvent,
)
from .tarot import (
    TAROT_ACTION_DEFINITIONS,
    TAROT_ACTION_HANDLERS,
    DivinerComponent,
    TarotReadEvent,
    tarot_fragments,
)

PLUGIN_ID = "bunnyland.fortunesim"

#: Core plugins this pack reuses for its optional synergies (storyteller pacing/foreshadowing,
#: social rapport). Both are recommended, not required: fortunesim runs standalone, with those
#: synergies simply dormant when absent. Affect moods route through core_verbs, always present.
STORYTELLER = "bunnyland.storyteller"
SOCIAL = "bunnyland.social"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Fortunesim",
        version="0.2.0",
        default_enabled=True,
        dependencies=DependencyContribution(
            recommends=(STORYTELLER, SOCIAL),
        ),
        ecs=EcsContribution(
            components=(
                LuckComponent,
                CharmComponent,
                OmenComponent,
                FortuneToolComponent,
                DivinerComponent,
                JinxComponent,
            ),
            edges=(Reading,),
        ),
        commands=CommandContribution(
            action_handlers=(
                FORTUNE_ACTION_HANDLERS
                + SUPERSTITION_ACTION_HANDLERS
                + TAROT_ACTION_HANDLERS
                + JINX_ACTION_HANDLERS
            ),
            action_definitions=(
                FORTUNE_ACTION_DEFINITIONS
                + SUPERSTITION_ACTION_DEFINITIONS
                + TAROT_ACTION_DEFINITIONS
                + JINX_ACTION_DEFINITIONS
            ),
            typed_events=(
                LuckChangedEvent,
                OmenSightedEvent,
                OmenClearedEvent,
                FortuneReadEvent,
                WardLuckEvent,
                TarotReadEvent,
                JinxLaidEvent,
                JinxMishapEvent,
                JinxLiftedEvent,
            ),
        ),
        runtime=RuntimeContribution(
            service_factories=(
                install_fortunesim,
                install_fortunesim_omens,
                install_fortunesim_jinx,
            ),
        ),
        content=ContentContribution(
            prompt_fragments=(
                luck_fragments,
                charm_fragments,
                omen_fragments,
                tarot_fragments,
                jinx_fragments,
            ),
            generation_enrichers=(FortuneGenerationEnricher(),),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
