# Playable terminal game

## Problem

The combat and timeline engines have no way to be played. `src/main.py` at `2adbf92` is the Phase 1 demo loop: it ticks a state machine and logs. `just run` starts that demo. Rewind, Echo Cast and Counter-Stop are reachable only from tests.

Uncommitted work from 2026-08-13 on `feature/playable-combat-cli` holds a text renderer, a combat controller and three authored encounters with no entry point and no tests.

## Intended outcome

`just play` starts a terminal game: three authored fights in sequence, wounds carried from one to the next. `just play <id>` plays one fight. Every engine action is reachable from the prompt, the same seed and inputs replay the same game, and a whole game can be driven by a script in a test.

## Scope

### In scope

- A text renderer (`src/ui/console.py`) and a combat controller (`src/states/combat_cli.py`), input and output injected.
- Three encounters as frozen specs (`src/content/`): `sundial`, `crossroads`, `gate`.
- An entry point (`src/play.py`): one encounter, or all three in order.
- `DesignatedCounterPolicy`: named enemies Counter-Stop whenever eligible. A stand-in for the Chronomancer AI behind the existing `CounterStopPolicy` seam.
- `just play`.

### Out of scope

- Balance. At this change's base, plain attacks win all three fights; change `encounter-balance` owns tuning.
- Chronomancer decision-making; change `chronomancer`.
- Pygame or any graphical front end; the Step 8 visual pass is Phase 5.
- Saving and resuming a game.
- LLM narration; Phase 4.

## Decisions

1. "Playable" means the terminal game: "three encounters played in sequence with HP carried over". PJ, 2026-11-15: "go with all your recommendations". A Pygame front end has no existing code and is a much larger build.
2. This change commits the August work with tests and a `just play` recipe; balance and the Chronomancer are separate changes, in that order after this one. Same answer.
3. The narrator stays on the mock provider and the AI Dungeon Master stays out until the terminal game is fun without AI. Same answer.

## Open questions

None blocking. Can wait: whether an escaped fight should let the sequence continue. This change ends the sequence on any outcome other than victory.

## Related documents

- Requirements: [specs/terminal-game/spec.md](specs/terminal-game/spec.md)
- Tasks: [tasks.md](tasks.md)
