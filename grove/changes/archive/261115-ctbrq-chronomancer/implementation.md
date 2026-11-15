# Implementation: Chronomancer

## Tasks

### T-01 — Replay faults

Status: done

Evidence: `TemporalSystem._replay_events` now computes, per earlier branch, the last turn still in history (the minimum `to_turn` of every later fork) and replays only events at or before it; it sets `_total_turns` to the target turn when done, because the turn a player takes straight after a rewind has no TURN_STARTED. `_apply_event` no longer asserts on SHIELD_BROKEN (the live path stores it before the action that causes it) and applies break recovery when an enemy's TURN_STARTED is replayed. `CombatContext.submit_player_action` restores phase and turn count when an Echo Cast is rejected. `tests/integration/test_rewind_lineage.py` (5): four fail on `728d66b`; `test_rewinding_past_an_earlier_fork_lands_on_the_original_line` passes there too, so it guards the case without having shown a fault. This is short of the task's acceptance, which asked for every scenario's test to fail on the base.

Found by playing 600 full games with random input before and after. With the lineage fix alone: 28 shield-break replay errors across 300 games. After both fixes: none in 600 games, and no exception.

### T-02 — Chronomancer archetype and enemy temporal actions

Status: done

Evidence: `ChronomancerAI`, `EnemyAI.wants_counter_stop`, the four new `CombatState` fields, `CombatContext.ai_state` and `temporal_rewind_count`, `ArchetypeCounterPolicy` as the default, the enemy-turn clause in `rewind`'s phase check, and `execute_enemy_turn` selecting before the turn is counted. `tests/unit/test_chronomancer.py` (38), `tests/integration/test_chronomancer_scenarios.py` (7). The 672 tests that passed on `728d66b` still pass, apart from the 3 of the removed `DesignatedCounterPolicy` and expectations in `tests/unit/test_encounters.py` and `tests/integration/test_play.py` rewritten for the new boss.

Deviations from STEP-7-PLAN:
- `CombatState` gained `total_turns`, `history_lengths` and `enemy_echo_active` besides `rewind_counts`. The plan's rules read "a turn to rewind into" and "own action history" but named no field for them, and without the echo flag the AI would choose a cast the engine rejects.
- An enemy Echo Cast or rewind the engine rejects falls back to a defend instead of raising.
- CI: a change to `src/core/combat.py`, `temporal.py` or `ai.py` now runs the full suite on a pull request. The per-file mapping ran `tests/unit/test_temporal.py` alone for a change to replay.

Also changed: `.github/workflows/ci.yml` (above).

### T-03 — Eval category

Status: done

Evidence: `scripts/eval_runner.py` `run_chronomancer`; `eval/scorer.go` and `eval/fixtures.go` expect fields; `eval/fixtures/chronomancer.yaml` (16 fixtures); `eval/scorer_test.go` (4 new tests); `tests/unit/test_eval_runner.py` `TestChronomancerCategory` (6), including a run with an unknown provider name to show none is constructed. `just eval`: 21/21 fixtures pass.

### T-04 — The gate

Status: done

Evidence: the gate boss's archetype is `chronomancer`; `EnemySpec.counters`, `Encounter.countering_enemy_ids` and the policy wiring in `src/play.py` are gone; `CombatCLI.run` skips `advance_turn` when an enemy turn ends awaiting player input. `tests/integration/test_play.py::test_the_gate_boss_rewinds_and_the_fight_still_ends`. `just check`: ruff, mypy, 726 tests, Go tests, `grove check` clean.

Observed, for `encounter-balance`:
- Attacking every turn still wins the gate in most seeds; her two rewinds cost the player HP but not the fight.
- She cast Echo in 5 of 600 random games: she is rarely the last enemy alive with 2 charge while the player holds under 2.
- A rewind refunds its own charge for both sides (proposal, open questions).
- An attack on a broken enemy is multiplied by 1.5 twice, once in `DamageCalculator.calculate` and once in `Enemy.take_damage`.
- Defend emits an event and changes no state; the terminal help says it halves incoming damage.

## Scenarios

- timeline-mechanics "Second rewind after play on a new branch": tests/integration/test_rewind_lineage.py test_second_rewind_ignores_the_abandoned_tail_of_the_first_branch, passed
- timeline-mechanics "Rewinding past an earlier fork": tests/integration/test_rewind_lineage.py test_rewinding_past_an_earlier_fork_lands_on_the_original_line, passed
- timeline-mechanics "Across a break": tests/integration/test_rewind_lineage.py test_rewind_across_a_shield_break_rebuilds_the_break, passed
- timeline-mechanics "After a recovery": tests/integration/test_rewind_lineage.py test_rewind_after_break_recovery_rebuilds_the_recovery, passed
- timeline-mechanics "Undo the player's hit": tests/integration/test_chronomancer_scenarios.py test_chronomancer_rewinds_after_a_big_hit, passed
- timeline-mechanics "Not its turn": tests/unit/test_chronomancer.py TestEnemyRewindGate, passed
- timeline-mechanics "Countered": tests/integration/test_chronomancer_scenarios.py test_countered_enemy_rewind_passes_the_turn_as_a_defend, passed
- timeline-mechanics "Threshold": tests/unit/test_chronomancer.py TestRewindRule; eval fixtures chrono_rewind_when_hurt, chrono_no_rewind_at_threshold, passed
- timeline-mechanics "Cap survives the rewinds it counts": tests/integration/test_chronomancer_scenarios.py test_combat_resumes_after_an_enemy_rewind_and_the_cap_ends_the_loop, passed
- timeline-mechanics "Charge held for a counter": tests/unit/test_chronomancer.py TestEchoRule test_hoard_guard, passed
- timeline-mechanics "Survival before hoarding": tests/unit/test_chronomancer.py test_hoard_guard_does_not_suppress_rewind, passed
- timeline-mechanics "Bait the counter": tests/integration/test_chronomancer_scenarios.py test_bait_the_counter_then_rewind_freely, passed
- timeline-mechanics "No Chronomancer present": tests/unit/test_chronomancer.py test_without_a_chronomancer_nobody_counters, passed
- timeline-mechanics "No charge": tests/integration/test_rewind_lineage.py test_rejected_echo_cast_leaves_the_turn_with_the_player, passed
- timeline-mechanics "Chess clock": tests/integration/test_counter_stop_scenarios.py TestChessClockScenario, passed
- timeline-mechanics "Mirror match": tests/integration/test_chronomancer_scenarios.py test_mirror_match_is_deterministic, passed
- combat "Replay": tests/unit/test_ai.py, passed
- combat "No state of its own": tests/unit/test_chronomancer.py test_holds_no_state_of_its_own, passed
- terminal-game "The gate": tests/integration/test_play.py test_the_gate_boss_rewinds_and_the_fight_still_ends, passed

## Reconciliation

- timeline-mechanics: applied to specs/timeline-mechanics/spec.md
- combat: applied to specs/combat/spec.md
- terminal-game: applied to specs/terminal-game/spec.md
