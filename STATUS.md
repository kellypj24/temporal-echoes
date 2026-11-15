# Status

Current state only; history is in git and the PRs. Update this file in the same PR as the
work it describes.

_Updated 2026-11-15._

## Now

- Playable: `just play` runs three authored fights in the terminal, wounds carried;
  `just play <id>` plays one. Spec: `grove/specs/terminal-game/`.
- Not yet a game: attacking every turn wins all three fights.
- Grove adopted: maintained specs in `grove/specs/`; `just check` ends with `grove check`.
  Old phase plans are in `docs/archive/assignments/`.

## Next

1. `chronomancer`: the Step 7 plan (`03de1c4` on `phase/3-step-7-chronomancer`) as a Grove
   change, then built. Replaces `DesignatedCounterPolicy` at the gate.
2. `encounter-balance`: tune the three encounters so plain attacks lose the gate fight.
   Inputs are in the archived `playable-terminal-game` change's `implementation.md`: a
   rewind's unit is one combatant's turn, and a rewind often refunds its own charge.

## Open decisions

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
