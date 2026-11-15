# Implementation: Playable terminal game

## Tasks

### T-01 — Renderer, controller and encounters

Status: done

Evidence: `src/ui/console.py`, `src/states/combat_cli.py`, `src/content/` and `DesignatedCounterPolicy` in `src/core/temporal.py` are the 2026-08-13 work, with one fix: the enemy-turn branch of `CombatCLI.run` now narrows to `Enemy` (mypy `arg-type`). `PlayerSpec.build` and `Encounter.build` gained a starting-HP argument for T-02. Tests: `tests/unit/test_console.py` (6), `tests/unit/test_combat_cli.py` (14), `tests/unit/test_encounters.py` (10), and `TestDesignatedCounterPolicy` in `tests/unit/test_counter_stop.py` (3). Coverage: `console.py` 97%, `combat_cli.py` 96%, `encounters.py` 100%.

Also changed: `tests/fixtures/script_fixtures.py` (scripted input and captured output shared by the unit and integration tests).

### T-02 — Entry point and sequence

Status: done

Evidence: `src/play.py` (`play`, `play_sequence`, `main`), `just play`, `tests/integration/test_play.py` (11). `just play --list` prints `sundial`, `crossroads`, `gate`. Coverage of `play.py` 96%. `just check`: ruff, mypy, 672 tests, 93.28% total coverage, Go eval tests, `grove check` clean.

Deviations:
- `just run` still starts the Phase 1 demo loop; its comment now says so. The proposal did not say whether to repoint it.
- `tests/integration/test_game_loop.py::test_game_loop_maintains_tick_rate` failed once in four full runs and passed on rerun. It asserts on wall-clock tick rate and predates this change.

Observed while testing, for `encounter-balance`:
- Attacking every turn wins all three fights in sequence, ending the gate at 461/700 HP.
- A rewind's unit is one combatant's turn, not a round. Rewinding 1 at the start of the player's turn undoes only the last enemy's action.
- A rewind restores the caster's charge to its value at the earlier turn, so the cost is often refunded (`tests/unit/test_combat_cli.py::test_rewind_shows_the_earlier_board_and_keeps_the_turn`: 2 charge, rewind 1, ends with 1 because that was the round-1 value).

## Scenarios

- terminal-game "Scripted victory": tests/integration/test_play.py test_scripted_attacks_win_one_encounter, passed
- terminal-game "Unknown encounter": tests/integration/test_play.py test_unknown_encounter_exits_with_usage_status, passed
- terminal-game "Rewind keeps the turn": tests/unit/test_combat_cli.py test_rewind_shows_the_earlier_board_and_keeps_the_turn, passed
- terminal-game "Defeated target": tests/unit/test_combat_cli.py test_defeated_target_is_refused_and_numbering_is_stable, passed
- terminal-game "Stable numbering": tests/unit/test_console.py test_defeated_enemy_keeps_its_number, passed
- terminal-game "Wounds carry": tests/integration/test_play.py test_wounds_carry_into_the_next_fight, passed
- terminal-game "Defeat ends the game": tests/integration/test_play.py test_a_defeat_ends_the_sequence, passed
- terminal-game "Two runs": tests/integration/test_play.py test_same_seed_and_script_give_the_same_output, passed
- terminal-game "Countered at the gate": tests/unit/test_combat_cli.py test_designated_enemy_counters_an_echo_at_the_gate, passed
- terminal-game "Import boundary": tests/unit/test_console.py test_renderer_imports_no_game_rules, passed

## Reconciliation

- terminal-game: applied to specs/terminal-game/spec.md
