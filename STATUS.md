# Status

Current state only; history is in git and the PRs. Update this file in the same PR as the
work it describes.

_Updated 2026-11-15._

## Now

- Playable: `just play` runs three authored fights in the terminal, wounds carried;
  `just play <id>` plays one. Spec: `grove/specs/terminal-game/`.
- The gate's boss is a Chronomancer: rewinds when hurt (twice at most), echoes when alone,
  counters every cast she can. Rules: `grove/specs/timeline-mechanics/`.
- Rewinds now work repeatedly and across shield breaks; 600 random-input games ran with no
  replay error.
- Not yet a game: attacking every turn still wins all three fights in most seeds.

## Next

1. `encounter-balance`: tune so plain attacks lose the gate fight. Inputs, all recorded in
   the archived `chronomancer` change's `implementation.md`:
   - a rewind refunds its own charge, for both sides;
   - a rewind's unit is one combatant's turn, not a round;
   - damage on a broken enemy is multiplied by 1.5 twice;
   - defend changes no state, though the help text says it halves damage;
   - the Chronomancer almost never meets her Echo condition.

## Open decisions

- Whether the player is offered a Counter-Stop against the Chronomancer's casts.
- Whether `just run` should start the game instead of the Phase 1 demo loop.
- Whether an escaped fight should let the sequence continue; today it ends it.
- `PROJECT_SUMMARY.md`, `SETUP_GUIDE.md` and `.cursor/rules/` still describe the
  `assignments/` workflow: rewrite or delete.

## Decided

- Step 8 (visual pass) moves to Phase 5 (2026-11-15).
- Phase 4 (LangGraph AI Dungeon Master) waits until the terminal game is fun without AI
  (2026-11-15).

## Blocked on

Nothing.
