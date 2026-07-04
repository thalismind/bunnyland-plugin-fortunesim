from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_fortunesim import (
    CharmComponent,
    FortuneToolComponent,
    FortuneWorldgenHook,
    LuckComponent,
    OmenComponent,
    charm_fragments,
    luck_fragments,
    omen_fragments,
)
from bunnyland_fortunesim.plugin import PLUGIN_ID


def test_plugin_loads_with_dotted_id():
    # A plugin id containing "." is not module-qualified by the loader, so it stays verbatim.
    plugins = load_modules(["bunnyland_fortunesim"])
    assert [p.id for p in plugins] == ["bunnyland.fortunesim"]
    assert PLUGIN_ID == "bunnyland.fortunesim"


def test_plugin_declares_its_components():
    plugin = load_modules(["bunnyland_fortunesim"])[0]
    for component in (LuckComponent, CharmComponent, OmenComponent, FortuneToolComponent):
        assert component in plugin.ecs.components


def test_plugin_declares_fragments_and_hook():
    plugin = load_modules(["bunnyland_fortunesim"])[0]
    assert FortuneWorldgenHook in plugin.content.worldgen_hooks
    for provider in (luck_fragments, charm_fragments, omen_fragments):
        assert provider in plugin.content.prompt_fragments


def test_plugin_version():
    plugin = load_modules(["bunnyland_fortunesim"])[0]
    assert plugin.version == "0.1.0"


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_fortunesim"]), actor)
    assert applied[0].id == "bunnyland.fortunesim"
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"read-fortune", "ward-luck"} <= command_types
