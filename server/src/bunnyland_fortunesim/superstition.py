"""Superstitions: the ``ward-luck`` verb — small rituals that buy a real luck boost.

Knocking on wood, tossing salt, or crossing your fingers grants a temporary bump to the
character's luck that expires on its own epoch (the luck consequence clears it). It is cheap,
deterministic busy-work with a genuine payoff, and it also colours the character's mood via the
shared fortune-mood reuse.

Validation order: invalid character -> missing character -> not in a room -> unknown ritual ->
apply. Any character can be superstitious, so a :class:`LuckComponent` is granted on the fly if
they lack one.
"""

from __future__ import annotations

from dataclasses import replace

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
)
from bunnyland.core.mutations import AddEdge, AddEntity, EntityReference, MutationPlan, SetComponent

from .bands import luck_band
from .charms import held_charm_bonus
from .components import LuckComponent
from .luck import fortune_thought_component
from .spatial import room_of

#: How long (game seconds) a warded-luck boost lasts before the luck consequence clears it.
WARD_DURATION = 1800

#: Known rituals and the luck bump each grants. Sorted keys keep listings stable.
RITUALS: dict[str, float] = {
    "cross-fingers": 0.5,
    "knock-on-wood": 1.0,
    "toss-salt": 1.0,
}

#: The ritual used when the player names none.
DEFAULT_RITUAL = "knock-on-wood"


class WardLuckEvent(DomainEvent):
    """A character performed a luck-warding ritual."""

    ritual: str
    boost: float
    until_epoch: int


class WardLuckHandler:
    """Perform a small superstition to boost luck for a while."""

    command_type = "ward-luck"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")

        ritual = command.payload.get("ritual") or DEFAULT_RITUAL
        if ritual not in RITUALS:
            return rejected("unknown ritual")
        boost = RITUALS[ritual]
        until_epoch = ctx.epoch + WARD_DURATION

        if character.has_component(LuckComponent):
            component = character.get_component(LuckComponent)
        else:
            component = LuckComponent()
        charm_bonus = held_charm_bonus(ctx.world, character)
        value = component.base + charm_bonus + boost
        updated = replace(
            component,
            charm_bonus=charm_bonus,
            ritual_bonus=boost,
            ritual_until_epoch=until_epoch,
            value=value,
        )

        event = WardLuckEvent(
            **ctx.event_base(
                visibility=EventVisibility.ROOM,
                actor_id=str(character_id),
                room_id=str(room.id),
                target_ids=(str(character_id),),
                ritual=ritual,
                boost=boost,
                until_epoch=until_epoch,
            )
        )
        operations = [SetComponent(character_id, updated)]
        thought = fortune_thought_component(
            luck_band(value), ctx.epoch, source_event_id=event.event_id
        )
        if thought is not None:
            thought_ref = EntityReference()
            operations.extend(
                (
                    AddEntity((thought,), reference=thought_ref),
                    AddEdge(character_id, thought_ref, HasThought()),
                )
            )
        return planned(MutationPlan(tuple(operations)), event)


WARD_LUCK_DEF = ActionDefinition(
    command_type="ward-luck",
    title="Ward luck",
    description="Perform a small superstition (knock on wood, toss salt) to boost your luck.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "ritual": ActionArgument(
            title="Ritual",
            description="Which ritual to perform: knock-on-wood, toss-salt, or cross-fingers.",
            kind="string",
        ),
    },
)

SUPERSTITION_ACTION_DEFINITIONS = (WARD_LUCK_DEF,)
SUPERSTITION_ACTION_HANDLERS = (WardLuckHandler,)


__all__ = [
    "DEFAULT_RITUAL",
    "RITUALS",
    "SUPERSTITION_ACTION_DEFINITIONS",
    "SUPERSTITION_ACTION_HANDLERS",
    "WARD_DURATION",
    "WARD_LUCK_DEF",
    "WardLuckEvent",
    "WardLuckHandler",
]
