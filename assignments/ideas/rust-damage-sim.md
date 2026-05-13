# Idea: Rust extension for damage batch simulation

**Status**: Idea / not scheduled
**First raised**: 2026-05-11
**Recommended timing**: After Phase 3 design is settled, before Phase 4 balance tuning starts.

## What

Port the hot path of `src/core/damage.py` (`DamageCalculator.calculate`) to a
Rust crate exposed via PyO3 + maturin. The Python `DamageCalculator` API stays
identical; the inner numeric work moves to Rust.

```
temporal-echoes/
├── src/core/damage.py        # unchanged surface, delegates to _rust
└── rust/damage_sim/
    ├── Cargo.toml
    ├── pyproject.toml        # maturin build config
    └── src/lib.rs            # #[pymodule] exposing calculate_batch()
```

## Why

Balance testing needs a batch simulator: "run 50,000 Player-vs-Boss combats
with these stats; plot win rate by build." Pure Python today runs that in
tens of seconds and gets worse as combat depth grows. Rust gets it into
milliseconds with no algorithm changes.

Secondary win: it's the textbook "first Rust extension" exercise, so the
toolchain stays warm for the higher-value but bigger commitment of an
event-store replay engine later (see *Future* below).

## Success criteria

- Same numerical results as the Python implementation across the existing
  damage property tests (`tests/unit/test_damage_properties.py`)
- ≥ 50× speedup on a 50k-combat batch benchmark
- `uv sync` builds and installs the Rust extension transparently on macOS + Linux
- CI gets a Rust toolchain step that's cached
- Python fallback path retained — if the Rust extension fails to load, the
  pure-Python implementation still works (so the game never breaks on a
  broken build)

## Out of scope

- Replacing the live-combat single-roll path. That's already fast enough;
  the win is only on batch sims.
- Any Pygame, dbt, or LLM-adjacent code. FFI overhead would dominate at
  per-frame call rates and there's no Rust ecosystem advantage there.

## Why not now

Phase 3 (Timeline Mechanics) is the next priority. Adding a Rust toolchain
mid-Phase-3 would split focus; better to land Phase 3 design first, then take
this on as a self-contained ~weekend project that delivers a tool Phase 4
balance work will actually use.

## Future (separate idea, not this one)

The higher-value Rust target is an **event store replay engine** — mmap'd
binary event log + zero-copy deserialization + deterministic replay. That's
load-bearing for timeline branching at scale but a much bigger architectural
commitment. The damage simulator is the right project to learn the
PyO3/maturin pattern on first; replay engine becomes feasible after.
