## T-01 — Renderer, controller and encounters

Result: one authored encounter can be driven to an outcome through injected input and output.

Files:
- `src/ui/console.py`
- `src/states/combat_cli.py`
- `src/content/`
- `src/core/temporal.py`
- `tests/unit/test_console.py`
- `tests/unit/test_combat_cli.py`
- `tests/unit/test_encounters.py`
- `tests/unit/test_counter_stop.py`

Interfaces: `ConsoleRenderer`, `CombatCLI.run`, `Encounter`, `get_encounter`, `list_encounters`, `DesignatedCounterPolicy`.

Constraints: no rules in the renderer or controller; no new random draw.

Acceptance:
- Each scenario under "Every engine action is reachable", "Designated counterers" and "Rendering holds no rules" has a passing test.
- Coverage of the new modules is at least 80 percent.

## T-02 — Entry point and sequence

Result: `just play` plays the three encounters in order with wounds carried; `just play <id>` plays one.

Files:
- `src/play.py`
- `justfile`
- `tests/integration/test_play.py`
- `README.md`
- `STATUS.md`

Interfaces: `play`, `play_sequence`, `main`; the `just play` recipe.

Acceptance:
- Each scenario under "Play one encounter", "Play the sequence" and "Replayable game" has a passing test.
- `just play --list` prints the three ids.
- README says how to start the game.
