# Status

Current state only; history is in git and the PRs. Update this file in the same PR as the
work it describes.

_Updated 2026-11-16._

## Now

- Playable and tuned: `just play` runs three authored fights in the terminal, wounds
  carried. Attack-only loses the gate; the time abilities decide it.
- Balance is held by scripted players (`tests/fixtures/autopilot.py`,
  `tests/integration/test_balance.py`); `just balance` prints their win rates. At 100
  seeds: attack-only clears 0, good play without time abilities 36, with them 76.
- Nobody has played the tuned sequence by hand yet. The measures are of scripts.
- Specs: `grove/specs/` (`combat`, `timeline-mechanics`, `terminal-game`).

## Next

1. Play it. `just play`, then note what feels wrong; the scripts cannot tell.
2. Decide the two open questions the tuning raised (below).

## Open decisions

- Echo damage went from half to full so that time abilities decide the gate. Keep, or
  find the difference elsewhere.
- Rewind as an undo is not worth its charge to a scripted player; rewinds are almost all
  the 1-charge bait. Leave, or make the undo stronger.
- Whether `just run` should start the game instead of the Phase 1 demo loop.
- Whether an escaped fight should let the sequence continue; today it ends it.

## Decided

- Step 8 (visual pass) moves to Phase 5 (2026-11-15).
- Phase 4 (LangGraph AI Dungeon Master) waits until the terminal game is fun without AI
  (2026-11-15).

## Blocked on

Nothing.
