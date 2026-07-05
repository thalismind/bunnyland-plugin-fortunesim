# bunnyland-fortunesim (server plugin)

The out-of-tree Bunnyland plugin package `bunnyland_fortunesim` (plugin id
`bunnyland.fortunesim`).

## Development

Tests run against a sibling `bunnyland-server` checkout without installing anything —
`tests/conftest.py` puts both this package's `src/` and `../bunnyland-server/src` on
`sys.path`. From this `server/` directory:

```bash
# uses the sibling bunnyland-server's virtualenv/deps
uv run --project ../../bunnyland-server -m pytest
# or, if bunnyland + relics are already importable:
python -m pytest
```

Lint:

```bash
uv run --project ../../bunnyland-server ruff check src tests
```

## Loading into the server

```bash
bunnyland serve --module bunnyland_fortunesim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported.

## What it contributes

- **Components** — `LuckComponent` (an open stat other packs can read), `CharmComponent`,
  `OmenComponent`, `FortuneToolComponent`, `DivinerComponent`, `JinxComponent`, and the typed
  `Reading` edge.
- **Luck** — `LuckConsequence` recomputes each character's materialised luck `value` every
  tick from `base` luck, the sum of held charms, and any active `ward-luck` ritual bonus (which
  expires on its own epoch), emitting `LuckChangedEvent` on band crossings. `luck_fragments`
  render the first-person luck-band line ("Fortune favors you today.").
- **Charms & talismans** — a held `CharmComponent` shifts its holder's luck; a negative one is a
  cursed trinket. `charm_fragments` render the first-person "you carry a lucky …" line, and
  `spawn_charm` / `spawn_talisman` / `spawn_cursed_trinket` make the items.
- **Omens** — `OmenConsequence` casts a room foreboding (a cursed charm loose on the floor) or
  auspicious (a lucky one), picking the omen line deterministically and clearing it when the
  charms leave. Sticky worldgen omens are left untouched. `omen_fragments` render the room's
  omen; `OmenSightedEvent` / `OmenClearedEvent` fire on change.
- **Fortune-telling** — the `read-fortune` verb over a held tarot/tea-leaves tool assembles a
  deterministic reading (biased upward by the seeker's luck and weaving in the room omen) and
  emits a private `FortuneReadEvent`. `spawn_fortune_tool` makes the tool.
- **Superstitions** — the `ward-luck` verb (knock-on-wood, toss-salt, cross-fingers) grants a
  temporary luck boost, granting a `LuckComponent` on the fly if the character lacks one, and
  emits `WardLuckEvent`.
- **Tarot readings** (v2 headline) — the `read-tarot` verb: a diviner reads a reachable client
  from a held deck. The drawn card uses **controlled randomness** — a per-diviner `DivinerComponent`
  draw counter advanced each reading and hashed with the `epoch` over the sorted `TAROT_DECK`, so
  a fixed `(counter, epoch)` always draws the same upright/reversed card while successive draws
  move on. A toned card leaves a mood, rapport grows through the core `SocialBond` edge, the draw
  is recorded as a typed `Reading` edge, and an imminent storyteller incident is foreshadowed.
  Emits `TarotReadEvent`.
- **Narrative jinxes** (v2 headline) — reworked curses, not a stat debuff. `lay-jinx` (held cursed
  token) starts an escalating `JinxComponent` run; `JinxConsequence` advances a mishap on the
  storyteller's cadence (`JinxMishapEvent`), escalating through the `MISHAP_STAGES` until it runs
  its course, and feeds `ThreatPointsComponent` pressure while active. `break-jinx` (held lucky
  charm) lifts it. Emits `JinxLaidEvent` / `JinxMishapEvent` / `JinxLiftedEvent`.
- **Mood reuse** — good/bad fortune, tarot tones, and jinx mishaps colour a character's mood by
  reusing the core affect system: a decaying `ThoughtComponent` carrying an `AffectDelta`, which
  the stock `AffectAggregation` folds into the character's `AffectComponent`.
- **Worldgen** — `FortuneWorldgenHook` tags generated charm/trinket objects with
  `CharmComponent` and casts ominous/auspicious generated rooms with a sticky `OmenComponent`.

## Determinism

Every luck-biased outcome and fortune reading comes from a `hashlib` digest of stable ids plus
the world `epoch`, reduced over sorted tables (`bands.digest_unit`, `bands.biased_index`,
`bands.luck_multiplier`). No `random`, no wall-clock time — results are stable across machines
and across `PYTHONHASHSEED`. Tarot divination is the one sanctioned exception, and it stays within
the rule: it hashes a **per-draw counter** (advanced each reading) with the `epoch`, so it is
unpredictable to the player yet reproducible in tests and hash-seed-independent.
