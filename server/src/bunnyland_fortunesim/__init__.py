"""Out-of-tree Bunnyland plugin: luck, charms, omens, fortune-telling, and superstitions.

An expansion-pack-sized themed bundle. Luck is a stat other packs can read; charms and
talismans shift it while held; omens colour rooms foreboding or auspicious; ``read-fortune``
surfaces a deterministic reading; and ``ward-luck`` rituals buy a temporary luck boost. Every
luck-biased outcome and fortune reading is derived from a hash of stable ids plus the world
epoch, so results are deterministic and never use runtime randomness.
"""

from .bands import (
    BLESSED,
    CURSED,
    EVEN,
    LUCKY,
    UNLUCKY,
    biased_index,
    digest_unit,
    luck_band,
    luck_multiplier,
)
from .charms import (
    charm_fragments,
    held_charm_bonus,
    spawn_charm,
    spawn_cursed_trinket,
    spawn_talisman,
)
from .components import (
    AUSPICIOUS,
    FOREBODING,
    CharmComponent,
    LuckComponent,
    OmenComponent,
)
from .edges import Reading
from .enrichment import FortuneGenerationEnricher
from .fortune import (
    FortuneReadEvent,
    FortuneToolComponent,
    ReadFortuneHandler,
    compose_reading,
    spawn_fortune_tool,
)
from .install import (
    install_fortunesim,
    install_fortunesim_jinx,
    install_fortunesim_omens,
)
from .jinx import (
    BreakJinxHandler,
    JinxComponent,
    JinxConsequence,
    JinxLaidEvent,
    JinxLiftedEvent,
    JinxMishapEvent,
    LayJinxHandler,
    held_cursed_token,
    jinx_fragments,
    pick_mishap,
    storyteller_interval,
)
from .luck import (
    LuckChangedEvent,
    LuckConsequence,
    effective_luck,
    fortune_mood,
    luck_fragments,
    remember_fortune,
)
from .omens import (
    OmenClearedEvent,
    OmenConsequence,
    OmenSightedEvent,
    omen_fragments,
)
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .spatial import holder_of, room_of
from .superstition import WardLuckEvent, WardLuckHandler
from .tarot import (
    DivinerComponent,
    ReadTarotHandler,
    TarotReadEvent,
    card_meaning,
    card_mood,
    compose_tarot_reading,
    draw_card,
    draw_orientation,
    incident_imminent,
    readings_of,
    tarot_fragments,
)

__all__ = [
    "AUSPICIOUS",
    "BLESSED",
    "CURSED",
    "EVEN",
    "FOREBODING",
    "LUCKY",
    "PLUGIN_ID",
    "UNLUCKY",
    "BreakJinxHandler",
    "CharmComponent",
    "DivinerComponent",
    "FortuneReadEvent",
    "FortuneToolComponent",
    "FortuneGenerationEnricher",
    "JinxComponent",
    "JinxConsequence",
    "JinxLaidEvent",
    "JinxLiftedEvent",
    "JinxMishapEvent",
    "LayJinxHandler",
    "LuckChangedEvent",
    "LuckComponent",
    "LuckConsequence",
    "OmenClearedEvent",
    "OmenComponent",
    "OmenConsequence",
    "OmenSightedEvent",
    "ReadFortuneHandler",
    "ReadTarotHandler",
    "Reading",
    "TarotReadEvent",
    "WardLuckEvent",
    "WardLuckHandler",
    "biased_index",
    "bunnyland_plugins",
    "card_meaning",
    "card_mood",
    "charm_fragments",
    "compose_reading",
    "compose_tarot_reading",
    "digest_unit",
    "draw_card",
    "draw_orientation",
    "effective_luck",
    "fortune_mood",
    "held_charm_bonus",
    "held_cursed_token",
    "holder_of",
    "incident_imminent",
    "install_fortunesim",
    "install_fortunesim_jinx",
    "install_fortunesim_omens",
    "jinx_fragments",
    "luck_band",
    "luck_fragments",
    "luck_multiplier",
    "omen_fragments",
    "pick_mishap",
    "plugin",
    "readings_of",
    "remember_fortune",
    "room_of",
    "spawn_charm",
    "spawn_cursed_trinket",
    "spawn_fortune_tool",
    "spawn_talisman",
    "storyteller_interval",
    "tarot_fragments",
]
