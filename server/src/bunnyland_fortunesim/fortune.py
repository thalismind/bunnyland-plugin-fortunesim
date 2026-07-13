"""Fortune-telling: the ``read-fortune`` verb over a held tarot / tea-leaves tool.

A reading is assembled deterministically. The core line is drawn from a sorted table via
:func:`~bunnyland_fortunesim.bands.biased_index`, so a luckier seeker lands nearer the
auspicious end of the table without any runtime dice; the current room omen, when present, is
woven in as a second line. Reading the same seeker in the same world state always yields the
same words, regardless of ``PYTHONHASHSEED``.

Validation order follows the project convention: invalid character -> missing character ->
invalid tool id -> missing tool -> not held -> wrong kind -> apply.
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
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.edges import HasThought
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    planned,
    rejected,
    require_character,
    require_entity,
)
from bunnyland.core.mutations import AddEdge, AddEntity, EntityReference, MutationPlan
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .bands import biased_index, luck_band
from .components import OmenComponent
from .luck import effective_luck, fortune_thought_component
from .spatial import holder_of, room_of

#: Readings sorted from grimmest (index 0) to brightest (last); luck biases the pick upward.
READINGS: tuple[str, ...] = (
    "The cards fall grim: hardship shadows the road ahead.",
    "The leaves settle uneasily — step carefully in the days to come.",
    "The reading is muddled; the future keeps its own counsel for now.",
    "The signs are kindly: small good turns are gathering around you.",
    "The cards blaze bright — fortune is about to smile broadly on you.",
)


@dataclass(frozen=True)
class FortuneToolComponent(Component):
    """A held fortune-telling tool (a tarot deck, a cup of tea leaves)."""

    method: str = "tarot"

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person:
            return ()
        return (f"You hold a {self.method} set, ready to read a fortune.",)


class FortuneReadEvent(DomainEvent):
    """A seeker read their fortune."""

    seeker_id: str
    reading: str
    band: str


def compose_reading(seeker_id: str, epoch: int, luck: float, omen: OmenComponent | None) -> str:
    """Assemble a deterministic reading from the seeker, epoch, luck, and room omen."""
    index = biased_index(len(READINGS), luck, "reading", seeker_id, epoch)
    lines = [READINGS[index]]
    if omen is not None:
        lines.append(f"You sense it echoed here: {omen.text}")
    return " ".join(lines)


class ReadFortuneHandler:
    """Read a fortune with a held tarot/tea-leaves tool."""

    command_type = "read-fortune"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, _character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        tool_id, tool, rejection = require_entity(
            ctx,
            command.payload.get("tool_id"),
            invalid_reason="invalid tool id",
            missing_reason="tool does not exist",
        )
        if rejection is not None:
            return rejection
        holder = holder_of(ctx.world, tool_id)
        if holder is None or holder.id != character_id:
            return rejected("you are not holding that tool")
        if not tool.has_component(FortuneToolComponent):
            return rejected("that is not a fortune-telling tool")

        character = ctx.entity(character_id)
        luck = effective_luck(character)
        room = room_of(ctx.world, character_id)
        omen = (
            room.get_component(OmenComponent)
            if room is not None and room.has_component(OmenComponent)
            else None
        )
        reading = compose_reading(str(character_id), ctx.epoch, luck, omen)
        band = luck_band(luck)
        event = FortuneReadEvent(
            **ctx.event_base(
                visibility=EventVisibility.PRIVATE,
                actor_id=str(character_id),
                room_id=str(room.id) if room is not None else None,
                target_ids=(str(tool_id),),
                seeker_id=str(character_id),
                reading=reading,
                band=band,
            )
        )
        operations = []
        thought = fortune_thought_component(band, ctx.epoch, source_event_id=event.event_id)
        if thought is not None:
            thought_ref = EntityReference()
            operations.extend(
                (
                    AddEntity((thought,), reference=thought_ref),
                    AddEdge(character_id, thought_ref, HasThought()),
                )
            )
        return planned(MutationPlan(tuple(operations)), event)


def spawn_fortune_tool(
    world: World, *, room_id=None, method: str = "tarot", name: str = "tarot deck"
) -> Entity:
    """Spawn a holdable fortune-telling tool, optionally placed in ``room_id``."""
    item = spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="item", tags=("fortunesim", "divination")),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            FortuneToolComponent(method=method),
        ],
    )
    if room_id is not None and world.has_entity(room_id):
        world.get_entity(room_id).add_relationship(
            Contains(mode=ContainmentMode.ROOM_CONTENT), item.id
        )
    return item


READ_FORTUNE_DEF = ActionDefinition(
    command_type="read-fortune",
    title="Read fortune",
    description="Read a fortune with a tarot deck or tea leaves you are holding.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "tool_id": ActionArgument(
            title="Fortune tool",
            description="The tarot/tea-leaves tool you are holding.",
            kind="entity",
            required=True,
        ),
    },
)

FORTUNE_ACTION_DEFINITIONS = (READ_FORTUNE_DEF,)
FORTUNE_ACTION_HANDLERS = (ReadFortuneHandler,)


__all__ = [
    "FORTUNE_ACTION_DEFINITIONS",
    "FORTUNE_ACTION_HANDLERS",
    "READINGS",
    "READ_FORTUNE_DEF",
    "FortuneReadEvent",
    "FortuneToolComponent",
    "ReadFortuneHandler",
    "compose_reading",
    "spawn_fortune_tool",
]
