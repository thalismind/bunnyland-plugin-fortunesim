from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.edges import HasThought
from bunnyland.core.handlers import HandlerContext
from bunnyland.mechanics.storyteller import StorytellerComponent, ThreatPointsComponent
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective

from bunnyland_fortunesim import (
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
    spawn_charm,
    spawn_cursed_trinket,
    storyteller_interval,
)
from bunnyland_fortunesim.jinx import (
    DEFAULT_MISHAP_INTERVAL,
    MAX_STAGE,
    MISHAP_STAGES,
    PRESSURE_PER_STAGE,
)

EPOCH = 1000


def _world():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Back Room")])
    caster = spawn_entity(
        actor.world,
        [IdentityComponent(name="Hex", kind="character"), CharacterComponent()],
    )
    target = spawn_entity(
        actor.world,
        [IdentityComponent(name="Nell", kind="character"), CharacterComponent()],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), caster.id)
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), target.id)
    return actor, room, caster, target


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _cmd(character_id, command_type, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor, epoch=EPOCH):
    return HandlerContext(world=actor.world, epoch=epoch)


def _lay(actor, caster, target, room=None):
    payload = {"target_id": str(target.id)}
    if room is not None:
        payload["room_id"] = str(room.id)
    return LayJinxHandler().execute(_ctx(actor), _cmd(caster.id, "lay-jinx", payload))


# -- helpers: held_cursed_token / pick_mishap / storyteller_interval --------------------


def test_held_cursed_token_finds_a_cursed_charm():
    actor, room, caster, _target = _world()
    trinket = spawn_cursed_trinket(actor.world)
    _hold(caster, trinket)
    found = held_cursed_token(actor.world, caster)
    assert found is not None and found.id == trinket.id


def test_held_cursed_token_ignores_a_lucky_charm_and_empty_hands():
    actor, room, caster, _target = _world()
    assert held_cursed_token(actor.world, caster) is None
    _hold(caster, spawn_charm(actor.world))  # lucky, not cursed
    assert held_cursed_token(actor.world, caster) is None


def test_pick_mishap_is_deterministic_and_in_table():
    for stage in range(len(MISHAP_STAGES)):
        entry = pick_mishap("entity_3", stage, EPOCH)
        assert entry in MISHAP_STAGES[stage]
        assert pick_mishap("entity_3", stage, EPOCH) == entry


def test_storyteller_interval_uses_storyteller_then_default():
    actor, *_ = _world()
    assert storyteller_interval(actor.world) == DEFAULT_MISHAP_INTERVAL
    spawn_entity(actor.world, [StorytellerComponent(interval_seconds=7200)])
    assert storyteller_interval(actor.world) == 7200


# -- lay-jinx: happy + re-lay -----------------------------------------------------------


def test_lay_jinx_emits_event_and_marks_target():
    actor, room, caster, target = _world()
    _hold(caster, spawn_cursed_trinket(actor.world))
    result = _lay(actor, caster, target, room)
    assert result.ok
    event = result.events[0]
    assert isinstance(event, JinxLaidEvent)
    assert event.victim_id == str(target.id)
    jinx = target.get_component(JinxComponent)
    assert jinx.active and jinx.stage == 0 and jinx.cause == "laid"


def test_lay_jinx_relays_a_spent_jinx():
    actor, room, caster, target = _world()
    _hold(caster, spawn_cursed_trinket(actor.world))
    # A previously spent (inactive) jinx already sits on the target.
    target.add_component(JinxComponent(active=False, stage=2, cause="broken"))
    result = _lay(actor, caster, target)
    assert result.ok
    jinx = target.get_component(JinxComponent)
    assert jinx.active and jinx.stage == 0


# -- lay-jinx: rejections ---------------------------------------------------------------


def test_lay_rejects_invalid_caster():
    actor, *_ = _world()
    result = LayJinxHandler().execute(
        _ctx(actor), _cmd("???", "lay-jinx", {"target_id": "entity_1"})
    )
    assert result.reason == "invalid character id"


def test_lay_rejects_missing_caster():
    actor, *_ = _world()
    result = LayJinxHandler().execute(
        _ctx(actor), _cmd("entity_9999", "lay-jinx", {"target_id": "entity_1"})
    )
    assert result.reason == "character does not exist"


def test_lay_rejects_invalid_target():
    actor, room, caster, _target = _world()
    _hold(caster, spawn_cursed_trinket(actor.world))
    result = LayJinxHandler().execute(
        _ctx(actor), _cmd(caster.id, "lay-jinx", {"target_id": "???"})
    )
    assert result.reason == "invalid target id"


def test_lay_rejects_missing_target():
    actor, room, caster, _target = _world()
    _hold(caster, spawn_cursed_trinket(actor.world))
    result = LayJinxHandler().execute(
        _ctx(actor), _cmd(caster.id, "lay-jinx", {"target_id": "entity_9999"})
    )
    assert result.reason == "target does not exist"


def test_lay_rejects_unreachable_target():
    actor, room, caster, target = _world()
    _hold(caster, spawn_cursed_trinket(actor.world))
    room.remove_relationship(Contains, target.id)
    far = spawn_entity(actor.world, [RoomComponent(title="Elsewhere")])
    far.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), target.id)
    result = _lay(actor, caster, target)
    assert result.reason == "the target is not here"


def test_lay_rejects_non_character_target():
    actor, room, caster, _target = _world()
    _hold(caster, spawn_cursed_trinket(actor.world))
    item = spawn_charm(actor.world, room_id=room.id)
    result = LayJinxHandler().execute(
        _ctx(actor), _cmd(caster.id, "lay-jinx", {"target_id": str(item.id)})
    )
    assert result.reason == "you can only jinx a character"


def test_lay_rejects_without_a_cursed_token():
    actor, room, caster, target = _world()
    _hold(caster, spawn_charm(actor.world))  # lucky, not cursed
    result = _lay(actor, caster, target)
    assert result.reason == "you need a cursed token to lay a jinx"


def test_lay_rejects_already_jinxed():
    actor, room, caster, target = _world()
    _hold(caster, spawn_cursed_trinket(actor.world))
    assert _lay(actor, caster, target).ok
    result = _lay(actor, caster, target)
    assert result.reason == "that character is already jinxed"


# -- break-jinx: happy + rejections -----------------------------------------------------


def test_break_jinx_lifts_the_jinx():
    actor, room, caster, target = _world()
    target.add_component(JinxComponent(active=True, stage=1))
    _hold(caster, spawn_charm(actor.world))  # lucky charm
    result = BreakJinxHandler().execute(
        _ctx(actor), _cmd(caster.id, "break-jinx", {"target_id": str(target.id)})
    )
    assert result.ok
    event = result.events[0]
    assert isinstance(event, JinxLiftedEvent)
    assert event.cause == "broken"
    jinx = target.get_component(JinxComponent)
    assert not jinx.active and jinx.cause == "broken"


def test_break_rejects_invalid_caster():
    actor, *_ = _world()
    result = BreakJinxHandler().execute(
        _ctx(actor), _cmd("???", "break-jinx", {"target_id": "entity_1"})
    )
    assert result.reason == "invalid character id"


def test_break_rejects_unreachable_target():
    actor, room, caster, target = _world()
    room.remove_relationship(Contains, target.id)
    far = spawn_entity(actor.world, [RoomComponent(title="Elsewhere")])
    far.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), target.id)
    result = BreakJinxHandler().execute(
        _ctx(actor), _cmd(caster.id, "break-jinx", {"target_id": str(target.id)})
    )
    assert result.reason == "the target is not here"


def test_break_rejects_not_jinxed():
    actor, room, caster, target = _world()
    _hold(caster, spawn_charm(actor.world))
    result = BreakJinxHandler().execute(
        _ctx(actor), _cmd(caster.id, "break-jinx", {"target_id": str(target.id)})
    )
    assert result.reason == "that character is not jinxed"


def test_break_rejects_inactive_jinx_as_not_jinxed():
    actor, room, caster, target = _world()
    target.add_component(JinxComponent(active=False))
    _hold(caster, spawn_charm(actor.world))
    result = BreakJinxHandler().execute(
        _ctx(actor), _cmd(caster.id, "break-jinx", {"target_id": str(target.id)})
    )
    assert result.reason == "that character is not jinxed"


def test_break_rejects_without_a_lucky_charm():
    actor, room, caster, target = _world()
    target.add_component(JinxComponent(active=True))
    result = BreakJinxHandler().execute(
        _ctx(actor), _cmd(caster.id, "break-jinx", {"target_id": str(target.id)})
    )
    assert result.reason == "you need a lucky charm to break a jinx"


# -- consequence: pacing, escalation, pressure ------------------------------------------


def test_consequence_advances_a_mishap_and_escalates():
    actor, room, caster, target = _world()
    target.add_component(
        JinxComponent(active=True, stage=0, started_at_epoch=EPOCH, next_mishap_epoch=EPOCH)
    )
    events = JinxConsequence().process(actor.world, EPOCH)
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, JinxMishapEvent)
    assert event.stage == 0 and not event.final
    jinx = target.get_component(JinxComponent)
    assert jinx.stage == 1
    assert jinx.next_mishap_epoch == EPOCH + DEFAULT_MISHAP_INTERVAL
    # The mishap colours the victim's mood via a core thought.
    assert list(target.get_relationships(HasThought))


def test_consequence_not_due_yet_emits_nothing_but_still_pressures():
    actor, room, caster, target = _world()
    target.add_component(
        JinxComponent(active=True, stage=0, next_mishap_epoch=EPOCH + 10_000)
    )
    storyteller = spawn_entity(actor.world, [StorytellerComponent()])
    events = JinxConsequence().process(actor.world, EPOCH)
    assert events == []
    # stage 0 active jinx contributes (0 + 1) * PRESSURE_PER_STAGE
    assert storyteller.get_component(ThreatPointsComponent).points == PRESSURE_PER_STAGE


def test_consequence_skips_inactive_jinxes():
    actor, room, caster, target = _world()
    target.add_component(JinxComponent(active=False, stage=1, next_mishap_epoch=EPOCH))
    events = JinxConsequence().process(actor.world, EPOCH)
    assert events == []


def test_consequence_final_stage_runs_its_course():
    actor, room, caster, target = _world()
    target.add_component(
        JinxComponent(active=True, stage=MAX_STAGE, next_mishap_epoch=EPOCH)
    )
    events = JinxConsequence().process(actor.world, EPOCH)
    assert len(events) == 1
    assert events[0].final is True
    jinx = target.get_component(JinxComponent)
    assert not jinx.active and jinx.cause == "ran-its-course"


def test_consequence_feeds_storyteller_pressure_from_active_load():
    actor, room, caster, target = _world()
    target.add_component(
        JinxComponent(active=True, stage=1, next_mishap_epoch=EPOCH + 10_000)
    )
    storyteller = spawn_entity(actor.world, [StorytellerComponent(interval_seconds=3600)])
    JinxConsequence().process(actor.world, EPOCH)
    # A stage-1 jinx lends (1 + 1) * PRESSURE_PER_STAGE.
    assert storyteller.get_component(ThreatPointsComponent).points == 2 * PRESSURE_PER_STAGE


def test_consequence_is_dormant_without_a_storyteller():
    actor, room, caster, target = _world()
    target.add_component(JinxComponent(active=True, stage=0, next_mishap_epoch=EPOCH + 10_000))
    # No storyteller entity -> no pressure fed, no error.
    assert JinxConsequence().process(actor.world, EPOCH) == []


# -- prompt fragments -------------------------------------------------------------------


def test_jinx_fragment_for_an_actively_jinxed_character():
    actor, room, caster, target = _world()
    target.add_component(JinxComponent(active=True))
    lines = jinx_fragments(actor.world, target)
    assert any("jinx" in line.lower() for line in lines)


def test_jinx_fragment_absent_when_inactive_or_missing():
    actor, room, caster, target = _world()
    target.add_component(JinxComponent(active=False))
    assert jinx_fragments(actor.world, target) == []
    assert jinx_fragments(actor.world, caster) == []  # no jinx component
    assert jinx_fragments(actor.world, None) == []


def test_jinx_fragment_silent_to_a_bystander():
    actor, room, caster, target = _world()
    jinx = JinxComponent(active=True)
    ctx = ComponentPromptContext.for_entity(
        actor.world, target, perspective=PromptPerspective(viewer=caster)
    )
    assert jinx.prompt_fragments(ctx) == ()
