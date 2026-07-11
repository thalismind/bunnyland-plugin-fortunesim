from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins

from bunnyland_fortunesim import (
    CharmComponent,
    DivinerComponent,
    FortuneGenerationEnricher,
    FortuneToolComponent,
    JinxComponent,
    LuckComponent,
    OmenComponent,
    Reading,
    charm_fragments,
    jinx_fragments,
    luck_fragments,
    omen_fragments,
    tarot_fragments,
)
from bunnyland_fortunesim.plugin import PLUGIN_ID
from bunnyland_fortunesim.plugin import bunnyland_plugins as _plugins


def test_plugin_loads_with_dotted_id():
    # A plugin id containing "." is not module-qualified by the loader, so it stays verbatim.
    plugins = _plugins()
    assert [p.id for p in plugins] == ["bunnyland.fortunesim"]
    assert PLUGIN_ID == "bunnyland.fortunesim"


def test_plugin_declares_its_components():
    plugin = _plugins()[0]
    for component in (
        LuckComponent,
        CharmComponent,
        OmenComponent,
        FortuneToolComponent,
        DivinerComponent,
        JinxComponent,
    ):
        assert component in plugin.ecs.components


def test_plugin_declares_reading_edge():
    plugin = _plugins()[0]
    assert Reading in plugin.ecs.edges


def test_plugin_declares_fragments_and_hook():
    plugin = _plugins()[0]
    assert FortuneGenerationEnricher in [type(item) for item in plugin.content.generation_enrichers]
    for provider in (
        luck_fragments,
        charm_fragments,
        omen_fragments,
        tarot_fragments,
        jinx_fragments,
    ):
        assert provider in plugin.content.prompt_fragments


def test_plugin_version():
    plugin = _plugins()[0]
    assert plugin.version == "0.2.0"


def test_plugin_recommends_synergy_partners():
    plugin = _plugins()[0]
    # Synergy partners are recommended (soft), never required — the pack runs standalone.
    assert plugin.dependencies.requires == ()
    assert set(plugin.dependencies.recommends) == {"bunnyland.storyteller", "bunnyland.social"}


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(_plugins(), actor)
    assert applied[0].id == "bunnyland.fortunesim"
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"read-fortune", "ward-luck", "read-tarot", "lay-jinx", "break-jinx"} <= command_types
