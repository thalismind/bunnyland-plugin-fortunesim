"""Narrative jinxes: an escalating, storyteller-paced run of in-world mishaps.

The v2 rework of curses. A jinx is **not** a stat debuff — it is a *run of mishaps* that grow
worse over time and read as real events the LLM narrates: a stubbed toe today, a ruined coat
tomorrow, a genuine accident by the end.

- **Laid** with a held cursed token via ``lay-jinx``; **broken** with a held lucky charm via
  ``break-jinx``.
- **Paced by the storyteller** (roadmap core mandate): :class:`JinxConsequence` advances a mishap
  on the world storyteller's own cadence, and while jinxes are active it feeds
  Foundation Storyteller threat-point pressure onto the storyteller so
  a bad-luck streak tightens world pressure. With no storyteller loaded the feature stays dormant
  on those points and simply paces mishaps on a default cadence.
- Each mishap colours the victim's mood through the core affect flow (a decaying
  ``ThoughtComponent``), never by touching :class:`~bunnyland_fortunesim.components.LuckComponent`.

Validation order (both verbs): invalid caster -> missing caster -> invalid target ->
missing/unreachable target -> wrong-kind/state -> apply.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import CharacterComponent, spawn_entity
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.components import AffectDelta, ThoughtComponent
from bunnyland.core.ecs import contents, replace_component
from bunnyland.core.edges import HasThought
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_reachable_entity,
)
from bunnyland.foundation.storyteller.mechanics import StorytellerComponent, ThreatPointsComponent
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .bands import digest_unit
from .charms import held_charm_bonus
from .components import CharmComponent

#: Mishap cadence (game seconds) when no storyteller sets the pace.
DEFAULT_MISHAP_INTERVAL = 6 * 3600

#: How long a mishap's sting lingers before it decays (game seconds).
MISHAP_MOOD_TTL = 2 * 3600

#: Threat points each active jinx stage lends the storyteller (a bad-luck streak = pressure).
PRESSURE_PER_STAGE = 1.5

#: Escalating mishap tables, one per stage; each ``(key, text)`` sorted for stable indexing.
MISHAP_STAGES: tuple[tuple[tuple[str, str], ...], ...] = (
    tuple(
        sorted(
            (
                ("stubbed-toe", "You stub your toe hard on a doorframe."),
                ("spilled-drink", "Your drink tips over and soaks your sleeve."),
                ("dropped-coin", "A coin slips your fingers and rolls into a drain."),
            )
        )
    ),
    tuple(
        sorted(
            (
                ("torn-coat", "A nail catches your coat and tears a long rent in it."),
                ("lost-key", "You reach for your key and find the pocket empty."),
                ("soured-milk", "The food you saved has turned and must be thrown out."),
            )
        )
    ),
    tuple(
        sorted(
            (
                ("shattered-heirloom", "Something you treasured slips and shatters on the floor."),
                ("missed-chance", "You arrive a breath too late and the chance is gone."),
                ("ruined-work", "A whole afternoon's work is spoiled beyond saving."),
            )
        )
    ),
    tuple(
        sorted(
            (
                ("bad-fall", "The stair gives and you take a hard, jarring fall."),
                ("fire-scare", "A forgotten flame nearly sets the room alight."),
                ("lost-purse", "Your whole purse vanishes in the crush of a crowd."),
            )
        )
    ),
)

#: The worst stage; a mishap here is the jinx running its course.
MAX_STAGE = len(MISHAP_STAGES) - 1

#: Worsening mood per stage.
_STAGE_DELTA: tuple[AffectDelta, ...] = (
    AffectDelta(valence=-3, stress=1),
    AffectDelta(valence=-5, stress=2),
    AffectDelta(valence=-7, stress=3, sadness=2),
    AffectDelta(valence=-9, stress=4, fear=3),
)


@dataclass(frozen=True)
class JinxComponent(Component):
    """An active (or spent) narrative jinx on a character.

    ``stage`` is how far the run has escalated (0 = petty, :data:`MAX_STAGE` = dire);
    ``next_mishap_epoch`` is when the next mishap is due; ``active`` falls to ``False`` once the
    jinx is broken or runs its course.
    """

    active: bool = True
    stage: int = 0
    started_at_epoch: int = 0
    next_mishap_epoch: int = 0
    cause: str = "laid"

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person or not self.active:
            return ()
        return ("A jinx clings to you; small things keep going wrong.",)


class JinxLaidEvent(DomainEvent):
    """A jinx was laid on a character."""

    victim_id: str


class JinxMishapEvent(DomainEvent):
    """A jinxed character suffered a mishap."""

    victim_id: str
    stage: int
    mishap: str
    text: str
    final: bool


class JinxLiftedEvent(DomainEvent):
    """A jinx was broken or ran its course."""

    victim_id: str
    cause: str


def held_cursed_token(world: World, character: Entity) -> Entity | None:
    """Return a cursed charm the character is holding, if any (used to lay a jinx)."""
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if item.has_component(CharmComponent) and item.get_component(CharmComponent).cursed:
            return item
    return None


def _remember_mishap(
    world: World, victim: Entity, stage: int, text: str, epoch: int, *, source_event_id: str
) -> None:
    """Attach a decaying mishap-mood thought (reuses the core affect flow)."""
    thought = spawn_entity(
        world,
        [
            ThoughtComponent(
                label="jinxed",
                text=text,
                affect_delta=_STAGE_DELTA[stage],
                created_at_epoch=epoch,
                expires_at_epoch=epoch + MISHAP_MOOD_TTL,
                source_event_id=source_event_id,
            )
        ],
    )
    victim.add_relationship(HasThought(), thought.id)


def pick_mishap(victim_id: str, stage: int, epoch: int) -> tuple[str, str]:
    """The ``(key, text)`` mishap drawn for a stage (deterministic, hash-derived)."""
    table = MISHAP_STAGES[stage]
    return table[int(digest_unit(victim_id, stage, epoch) * len(table))]


def storyteller_interval(world: World) -> int:
    """The world storyteller's incident cadence, or :data:`DEFAULT_MISHAP_INTERVAL` if none."""
    for entity in world.query().with_all([StorytellerComponent]).execute_entities():
        return entity.get_component(StorytellerComponent).interval_seconds
    return DEFAULT_MISHAP_INTERVAL


def _feed_storyteller_pressure(world: World, pressure: float) -> None:
    """Set the storyteller's threat pressure from the active jinx load (dormant if none)."""
    for entity in world.query().with_all([StorytellerComponent]).execute_entities():
        replace_component(entity, ThreatPointsComponent(points=pressure))


class LayJinxHandler:
    """Lay a narrative jinx on a reachable character, using a held cursed token."""

    command_type = "lay-jinx"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        caster_id, caster, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        target_id, target, rejection = require_reachable_entity(
            ctx,
            caster,
            command.payload.get("target_id"),
            invalid_reason="invalid target id",
            missing_reason="target does not exist",
            unreachable_reason="the target is not here",
        )
        if rejection is not None:
            return rejection
        if not target.has_component(CharacterComponent):
            return rejected("you can only jinx a character")
        if held_cursed_token(ctx.world, caster) is None:
            return rejected("you need a cursed token to lay a jinx")
        if target.has_component(JinxComponent) and target.get_component(JinxComponent).active:
            return rejected("that character is already jinxed")

        jinx = JinxComponent(
            active=True,
            stage=0,
            started_at_epoch=ctx.epoch,
            next_mishap_epoch=ctx.epoch,
            cause="laid",
        )
        if target.has_component(JinxComponent):
            replace_component(target, jinx)
        else:
            target.add_component(jinx)

        room_id = command.payload.get("room_id")
        return ok(
            JinxLaidEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(caster_id),
                    room_id=str(room_id) if room_id is not None else None,
                    target_ids=(str(target_id),),
                    victim_id=str(target_id),
                )
            )
        )


class BreakJinxHandler:
    """Break a jinx on a reachable character, using a held lucky charm."""

    command_type = "break-jinx"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        caster_id, caster, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        target_id, target, rejection = require_reachable_entity(
            ctx,
            caster,
            command.payload.get("target_id"),
            invalid_reason="invalid target id",
            missing_reason="target does not exist",
            unreachable_reason="the target is not here",
        )
        if rejection is not None:
            return rejection
        if not (target.has_component(JinxComponent) and target.get_component(JinxComponent).active):
            return rejected("that character is not jinxed")
        if held_charm_bonus(ctx.world, caster) <= 0:
            return rejected("you need a lucky charm to break a jinx")

        jinx = target.get_component(JinxComponent)
        replace_component(target, replace(jinx, active=False, cause="broken"))
        return ok(
            JinxLiftedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(caster_id),
                    target_ids=(str(target_id),),
                    victim_id=str(target_id),
                    cause="broken",
                )
            )
        )


class JinxConsequence:
    """Advance jinx mishaps on the storyteller's cadence and feed it their pressure."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        interval = storyteller_interval(world)
        pressure = 0.0
        for victim in list(world.query().with_all([JinxComponent]).execute_entities()):
            jinx = victim.get_component(JinxComponent)
            if not jinx.active:
                continue
            if epoch >= jinx.next_mishap_epoch:
                events.append(self._mishap(world, epoch, victim, jinx, interval))
                jinx = victim.get_component(JinxComponent)
            if jinx.active:
                pressure += (jinx.stage + 1) * PRESSURE_PER_STAGE
        _feed_storyteller_pressure(world, pressure)
        return events

    def _mishap(
        self, world: World, epoch: int, victim: Entity, jinx: JinxComponent, interval: int
    ) -> DomainEvent:
        stage = jinx.stage
        key, text = pick_mishap(str(victim.id), stage, epoch)
        final = stage >= MAX_STAGE
        event = JinxMishapEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.ROOM,
                actor_id=str(victim.id),
                target_ids=(str(victim.id),),
                victim_id=str(victim.id),
                stage=stage,
                mishap=key,
                text=text,
                final=final,
            )
        )
        _remember_mishap(world, victim, stage, text, epoch, source_event_id=event.event_id)
        if final:
            replace_component(victim, replace(jinx, active=False, cause="ran-its-course"))
        else:
            replace_component(
                victim, replace(jinx, stage=stage + 1, next_mishap_epoch=epoch + interval)
            )
        return event


def jinx_fragments(world: World, character: Entity) -> list[str]:
    """First-person line for a character labouring under an active jinx."""
    if character is None or not character.has_component(JinxComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, character)
    return list(character.get_component(JinxComponent).prompt_fragments(ctx))


LAY_JINX_DEF = ActionDefinition(
    command_type="lay-jinx",
    title="Lay jinx",
    description="Lay a run of bad luck on someone, using a cursed token you are holding.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "target_id": ActionArgument(
            title="Target",
            description="The character to jinx.",
            kind="entity",
            required=True,
        ),
    },
)

BREAK_JINX_DEF = ActionDefinition(
    command_type="break-jinx",
    title="Break jinx",
    description="Lift a jinx from someone, using a lucky charm you are holding.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "target_id": ActionArgument(
            title="Target",
            description="The jinxed character to free.",
            kind="entity",
            required=True,
        ),
    },
)

JINX_ACTION_DEFINITIONS = (LAY_JINX_DEF, BREAK_JINX_DEF)
JINX_ACTION_HANDLERS = (LayJinxHandler, BreakJinxHandler)


__all__ = [
    "BREAK_JINX_DEF",
    "DEFAULT_MISHAP_INTERVAL",
    "JINX_ACTION_DEFINITIONS",
    "JINX_ACTION_HANDLERS",
    "LAY_JINX_DEF",
    "MAX_STAGE",
    "MISHAP_MOOD_TTL",
    "MISHAP_STAGES",
    "PRESSURE_PER_STAGE",
    "BreakJinxHandler",
    "JinxComponent",
    "JinxConsequence",
    "JinxLaidEvent",
    "JinxLiftedEvent",
    "JinxMishapEvent",
    "LayJinxHandler",
    "held_cursed_token",
    "jinx_fragments",
    "pick_mishap",
    "storyteller_interval",
]
