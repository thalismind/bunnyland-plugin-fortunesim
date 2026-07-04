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
from .enrichment import FortuneWorldgenHook
from .fortune import (
    FortuneReadEvent,
    FortuneToolComponent,
    ReadFortuneHandler,
    compose_reading,
    spawn_fortune_tool,
)
from .install import install_fortunesim, install_fortunesim_omens
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

__all__ = [
    "AUSPICIOUS",
    "BLESSED",
    "CURSED",
    "EVEN",
    "FOREBODING",
    "LUCKY",
    "PLUGIN_ID",
    "UNLUCKY",
    "CharmComponent",
    "FortuneReadEvent",
    "FortuneToolComponent",
    "FortuneWorldgenHook",
    "LuckChangedEvent",
    "LuckComponent",
    "LuckConsequence",
    "OmenClearedEvent",
    "OmenComponent",
    "OmenConsequence",
    "OmenSightedEvent",
    "ReadFortuneHandler",
    "WardLuckEvent",
    "WardLuckHandler",
    "biased_index",
    "bunnyland_plugins",
    "charm_fragments",
    "compose_reading",
    "digest_unit",
    "effective_luck",
    "fortune_mood",
    "held_charm_bonus",
    "holder_of",
    "install_fortunesim",
    "install_fortunesim_omens",
    "luck_band",
    "luck_fragments",
    "luck_multiplier",
    "omen_fragments",
    "plugin",
    "remember_fortune",
    "room_of",
    "spawn_charm",
    "spawn_cursed_trinket",
    "spawn_fortune_tool",
    "spawn_talisman",
]
