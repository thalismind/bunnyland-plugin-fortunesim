"""Charms & talismans: carried items that raise (or, when cursed, lower) luck.

A charm only counts while it is *held* — carried in a character's inventory. The luck
consequence sums :func:`held_charm_bonus` into each character's materialised luck every tick,
so picking up a rabbit's foot makes you luckier and dropping it undoes that on the next tick.

Spawn helpers create holdable charm items; :func:`charm_fragments` renders the first-person
"you carry a lucky …" line for whatever a character is holding.
"""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    spawn_entity,
)
from bunnyland.core.ecs import contents
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective
from relics import Entity, World

from .components import CharmComponent


def held_charm_bonus(world: World, character: Entity) -> float:
    """Total luck contributed by the charms ``character`` is currently holding."""
    bonus = 0.0
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if item.has_component(CharmComponent):
            bonus += item.get_component(CharmComponent).luck
    return bonus


def charm_fragments(world: World, character: Entity) -> list[str]:
    """First-person lines for every charm a character is holding."""
    if character is None:
        return []
    lines: list[str] = []
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if not item.has_component(CharmComponent):
            continue
        ctx = ComponentPromptContext.for_entity(
            world, item, perspective=PromptPerspective(viewer=item)
        )
        lines.extend(item.get_component(CharmComponent).prompt_fragments(ctx))
    return sorted(dict.fromkeys(lines))


def _link_into_room(world: World, item: Entity, room_id) -> None:
    if room_id is None or not world.has_entity(room_id):
        return
    world.get_entity(room_id).add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), item.id)


def spawn_charm(
    world: World,
    *,
    room_id=None,
    luck: float = 1.0,
    label: str = "charm",
    name: str = "lucky charm",
) -> Entity:
    """Spawn a holdable charm item, optionally placed in ``room_id``.

    Pass a negative ``luck`` for a cursed trinket. ``label`` is the noun used in prompt text
    (e.g. "rabbit's foot"), ``name`` the item's identity name.
    """
    item = spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="item", tags=("fortunesim", "charm")),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            CharmComponent(luck=luck, label=label),
        ],
    )
    _link_into_room(world, item, room_id)
    return item


def spawn_talisman(world: World, *, room_id=None, luck: float = 2.0, label: str = "talisman",
                   name: str = "protective talisman") -> Entity:
    """Spawn a stronger lucky charm (a talisman)."""
    return spawn_charm(world, room_id=room_id, luck=luck, label=label, name=name)


def spawn_cursed_trinket(world: World, *, room_id=None, luck: float = -1.5,
                         label: str = "trinket", name: str = "cursed trinket") -> Entity:
    """Spawn a cursed trinket that drags its holder's luck down."""
    return spawn_charm(world, room_id=room_id, luck=luck, label=label, name=name)


__all__ = [
    "charm_fragments",
    "held_charm_bonus",
    "spawn_charm",
    "spawn_cursed_trinket",
    "spawn_talisman",
]
