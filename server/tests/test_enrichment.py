import asyncio

from bunnyland.core import WorldActor
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import ObjectSpec, RoomSpec, WorldProposal, instantiate

from bunnyland_fortunesim import AUSPICIOUS, FOREBODING, CharmComponent, OmenComponent
from bunnyland_fortunesim.plugin import bunnyland_plugins as _plugins


def _world(*, room=None, object_=None):
    actor = WorldActor()
    apply_plugins(_plugins(), actor)
    proposal = WorldProposal(
        seed="seed",
        rooms=[room or RoomSpec(key="room", title="Room")],
        objects=[object_] if object_ else [],
    )
    result = asyncio.run(instantiate(actor, proposal))
    return actor, result


def test_lucky_and_cursed_objects_become_charms():
    actor, result = _world(object_=ObjectSpec(key="clover", name="Clover", room_key="room"))
    assert not actor.world.get_entity(result.objects["clover"]).get_component(CharmComponent).cursed
    actor, result = _world(object_=ObjectSpec(key="doll", name="Cursed charm", room_key="room"))
    assert actor.world.get_entity(result.objects["doll"]).get_component(CharmComponent).cursed


def test_plain_object_is_ignored():
    actor, result = _world(object_=ObjectSpec(key="stone", name="Stone", room_key="room"))
    assert not actor.world.get_entity(result.objects["stone"]).has_component(CharmComponent)


def test_ominous_and_auspicious_rooms_get_omens():
    actor, result = _world(room=RoomSpec(key="crypt", title="Eerie Crypt"))
    assert (
        actor.world.get_entity(result.rooms["crypt"]).get_component(OmenComponent).kind
        == FOREBODING
    )
    actor, result = _world(room=RoomSpec(key="shrine", title="Sunlit Shrine"))
    assert (
        actor.world.get_entity(result.rooms["shrine"]).get_component(OmenComponent).kind
        == AUSPICIOUS
    )
