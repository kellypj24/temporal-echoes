# Status

Current state only; history is in git and the PRs. Update this file in the same PR as the
work it describes.

_Updated 2026-11-15._

## Now

- Active again. Goal: a terminal game that is fun without AI.
- Grove adopted: maintained specs `combat` and `timeline-mechanics` in `grove/specs/`;
  `just check` ends with `grove check`. Old phase plans are in `docs/archive/assignments/`.
- Phase 3 Steps 1–6 are on main: rewind, echo cast and counter-stop, deterministic.

## Next

1. `playable-cli`: the terminal combat front end on `feature/playable-combat-cli`, with
   tests and `just play`.
2. `chronomancer`: the Step 7 plan (`03de1c4` on `phase/3-step-7-chronomancer`) as a Grove
   change, then built.
3. `encounter-balance`: tune the three encounters so plain attacks lose the gate fight.

## Open decisions

- `PROJECT_SUMMARY.md`, `SETUP_GUIDE.md` and `.cursor/rules/` still describe the
  `assignments/` workflow: rewrite or delete.

## Decided

- Step 8 (visual pass) moves to Phase 5 (2026-11-15).
- Phase 4 (LangGraph AI Dungeon Master) waits until the terminal game is fun without AI
  (2026-11-15).

## Blocked on

Nothing.
