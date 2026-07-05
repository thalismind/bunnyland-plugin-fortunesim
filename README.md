# Bunnyland Fortunesim

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin about **luck,
charms, and omens** — an expansion-pack-sized themed bundle that gently nudges outcomes and
rewards ritual behavior. It pairs wickedly with a haunting pack (bad omens near the dead) and a
fishing pack (a lucky charm for the big catch).

> **Luck is a stat. Superstition is a strategy.**

The bundle ships seven cooperating mechanics:

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
- **Tarot readings** *(v2 headline)* — a `read-tarot` verb: a diviner reads a **client** in reach
  from a held deck, drawing an upright/reversed arcana whose tone leaves a real mood, growing
  rapport through the core `SocialBond` edge, recording the draw as a typed `Reading` edge, and
  **foreshadowing** a gathering storyteller incident. Each draw is unpredictable to the player yet
  fully reproducible (see determinism below).
- **Narrative jinxes** *(v2 headline)* — reworked curses. `lay-jinx` (with a held cursed token)
  starts an **escalating run of in-world mishaps** the LLM narrates — a stubbed toe today, a
  ruined coat tomorrow, a real accident by the end — paced on the storyteller's own cadence and
  feeding it pressure while active; `break-jinx` (with a held lucky charm) lifts it. Not a stat
  debuff — a story.

**Determinism:** every luck-biased outcome and fortune reading is derived from a `hashlib`
digest of stable ids plus the world `epoch`, reduced over sorted tables. There is no `random`
and no wall-clock time anywhere in the package, so the same world state always yields the same
result regardless of `PYTHONHASHSEED`. Tarot divination stays unpredictable-to-the-player without
breaking that rule: each diviner carries a **draw counter** advanced on every reading and hashed
with the world `epoch`, so a fixed `(counter, epoch)` always draws the same card while successive
draws move on — reproducible in tests, effectively unguessable in play.

This repo intentionally keeps all of the fortune work outside the main `bunnyland-server` repo.

## Layout

- `server/` — Python Bunnyland plugin package with the luck/charm/omen/diviner/jinx components and
  the `Reading` edge, the luck/omen/jinx consequences, the five verbs, prompt fragments, a
  worldgen enrichment hook, spawn factories, and tests.

## Server Plugin

The plugin exposes `bunnyland_fortunesim.bunnyland_plugins()` and contributes:

- `LuckComponent`, `CharmComponent`, `OmenComponent`, `FortuneToolComponent`, `DivinerComponent`,
  `JinxComponent`, and the typed `Reading` edge.
- `LuckConsequence` — materialises each character's total luck from held charms and active
  rituals every tick, emitting `LuckChangedEvent` on band crossings.
- `OmenConsequence` — adds, updates, and clears dynamic room omens driven by loose charms,
  leaving sticky worldgen omens alone; emits `OmenSightedEvent` / `OmenClearedEvent`.
- `JinxConsequence` — advances jinx mishaps on the storyteller's cadence and feeds it pressure
  while jinxes are active; emits `JinxMishapEvent` and lifts a jinx that runs its course.
- `luck_fragments`, `charm_fragments`, `omen_fragments`, `tarot_fragments`, `jinx_fragments` —
  render luck band, held charms, room omens, the diviner's knack, and an active jinx into both
  human and AI prompts.
- `FortuneWorldgenHook` — turns generated charm/trinket objects into `CharmComponent`s and casts
  ominous or auspicious generated rooms with a sticky `OmenComponent`.

### Verbs

- `read-fortune` — read your own fortune from a held tarot/tea-leaves tool (`FortuneReadEvent`).
- `ward-luck` — perform a superstition ritual for a temporary luck boost (`WardLuckEvent`).
- `read-tarot` — read a tarot card for a reachable client from a held deck (`TarotReadEvent`).
- `lay-jinx` — start a narrative jinx on a character, using a held cursed token (`JinxLaidEvent`).
- `break-jinx` — lift a jinx from a character, using a held lucky charm (`JinxLiftedEvent`).

Spawn factories: `spawn_charm`, `spawn_talisman`, `spawn_cursed_trinket`, `spawn_fortune_tool`.
Good and bad fortune, tarot tones, and jinx mishaps all colour a character's mood by reusing the
core affect system (a decaying `AffectDelta` thought) rather than any bespoke mood machinery.

### Synergy (optional, standalone-first)

Storyteller and social are **recommended, not required**: fortunesim runs fully standalone with
those synergies simply dormant. When a storyteller is present, tarot readings foreshadow imminent
incidents and active jinxes feed world pressure; rapport from a reading routes through the core
`SocialBond` edge. Other packs consume this pack's published `Luck` surface via
`from bunnyland_fortunesim import effective_luck`.

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
