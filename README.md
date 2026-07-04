# Bunnyland Fortunesim

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin about **luck,
charms, and omens** — an expansion-pack-sized themed bundle that gently nudges outcomes and
rewards ritual behavior. It pairs wickedly with a haunting pack (bad omens near the dead) and a
fishing pack (a lucky charm for the big catch).

> **Luck is a stat. Superstition is a strategy.**

The bundle ships five cooperating mechanics:

- **Luck stat** — an open `LuckComponent` on characters. Its materialised `value` (base +
  charms + active rituals) is maintained every tick by `LuckConsequence`, so any pack that opts
  in can read one field to bias its own probabilistic outcomes. Luck shifts the *weighting*; it
  never rolls dice.
- **Charms & talismans** — carried `CharmComponent` items (a rabbit's foot, a four-leaf clover)
  that raise luck while held; cursed trinkets lower it.
- **Omens** — `OmenConsequence` reads the world and casts a room foreboding or auspicious,
  surfacing a deterministic omen line ("A crow watches you from the rafters.") into prompts.
- **Fortune-telling** — a `read-fortune` verb over a held tarot / tea-leaves tool that assembles
  a deterministic reading from the seeker, their luck, and the current room omen.
- **Superstitions** — a `ward-luck` verb (knock on wood, toss salt, cross fingers) that buys a
  temporary luck boost — fun busy-work with a real payoff.

**Determinism:** every luck-biased outcome and fortune reading is derived from a `hashlib`
digest of stable ids plus the world `epoch`, reduced over sorted tables. There is no `random`
and no wall-clock time anywhere in the package, so the same world state always yields the same
result regardless of `PYTHONHASHSEED`.

This repo intentionally keeps all of the fortune work outside the main `bunnyland-server` repo.

## Layout

- `server/` — Python Bunnyland plugin package with the luck/charm/omen components, the luck and
  omen consequences, the two verbs, prompt fragments, a worldgen enrichment hook, spawn
  factories, and tests.

## Server Plugin

The plugin exposes `bunnyland_fortunesim.bunnyland_plugins()` and contributes:

- `LuckComponent`, `CharmComponent`, `OmenComponent`, `FortuneToolComponent`.
- `LuckConsequence` — materialises each character's total luck from held charms and active
  rituals every tick, emitting `LuckChangedEvent` on band crossings.
- `OmenConsequence` — adds, updates, and clears dynamic room omens driven by loose charms,
  leaving sticky worldgen omens alone; emits `OmenSightedEvent` / `OmenClearedEvent`.
- `luck_fragments`, `charm_fragments`, `omen_fragments` — render luck band, held charms, and
  room omens into both human and AI prompts.
- `FortuneWorldgenHook` — turns generated charm/trinket objects into `CharmComponent`s and casts
  ominous or auspicious generated rooms with a sticky `OmenComponent`.
- `read-fortune` and `ward-luck` — verbs for the seeker (human or AI), emitting `FortuneReadEvent`
  and `WardLuckEvent`.
- `spawn_charm`, `spawn_talisman`, `spawn_cursed_trinket`, `spawn_fortune_tool` — spawn factories.
- Good and bad fortune colour a character's mood by reusing the core affect system
  (`remember_fortune` attaches a decaying `AffectDelta` thought).

## Running

This package builds no containers. It is loaded into the stock server via `--module`:

```bash
bunnyland serve --module bunnyland_fortunesim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported. The
`bunnyland_fortunesim` package must be importable by the server (installed into the server's
environment, or on `PYTHONPATH`).

## Development

Run server tests against a sibling `bunnyland-server` checkout (no install required —
`server/tests/conftest.py` puts both packages on `sys.path`). From `server/`:

```bash
uv run --project ../../bunnyland-server -m pytest
uv run --project ../../bunnyland-server ruff check src tests
```

See [`server/README.md`](server/README.md) for more detail.

## Contributing & Conduct

This plugin follows the Bunnyland project's
[contribution guidelines](CONTRIBUTING.md) and [code of conduct](CODE_OF_CONDUCT.md),
which point back to the `bunnyland-server` repository.

## License

Licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
