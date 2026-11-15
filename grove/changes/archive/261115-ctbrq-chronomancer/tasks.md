## T-01 — Replay faults

Result: rewinds succeed any number of times in a fight and across shield breaks; a rejected Echo Cast keeps the player's turn.

Files:
- `src/core/temporal.py`
- `src/core/combat.py`
- `tests/integration/test_rewind_lineage.py`

Constraints: no stored event changes shape; no new event type.

Acceptance:
- The scenarios under "Rewind follows the live lineage", "Rewind rebuilds shield breaks and recovery" and "Rejected Echo Cast keeps the turn" have passing tests that fail on `728d66b`.

## T-02 — Chronomancer archetype and enemy temporal actions

Result: an enemy with archetype `chronomancer` rewinds, echoes and counters by the agreed rules.

Files:
- `src/core/ai.py`
- `src/core/combat.py`
- `src/core/temporal.py`
- `tests/unit/test_chronomancer.py`
- `tests/integration/test_chronomancer_scenarios.py`
- `tests/unit/test_counter_stop.py`
- `.github/workflows/ci.yml`

Interfaces: `ChronomancerAI`, `AIArchetype.CHRONOMANCER`, `EnemyAI.wants_counter_stop`, `CombatState.total_turns`, `CombatState.rewind_counts`, `CombatState.history_lengths`, `CombatState.enemy_echo_active`, `CombatContext.ai_state`, `CombatContext.temporal_rewind_count`, `ArchetypeCounterPolicy`. Driver contract: after `execute_enemy_turn`, a phase of `AWAITING_PLAYER_INPUT` means the enemy rewound and `advance_turn` must not be called.

Constraints: the four existing archetypes behave as before; `DesignatedCounterPolicy` is removed.

Acceptance:
- The scenarios under "Enemy rewind as a turn action", "Chronomancer rules", "Counter decisions belong to each enemy", "Deterministic under all three abilities" and combat's "Enemy archetypes" have passing tests.
- Every test that passed on `728d66b` passes, apart from those of the removed policy.

## T-03 — Eval category

Result: `just eval` scores Chronomancer decision fixtures without constructing a narrator or provider.

Files:
- `scripts/eval_runner.py`
- `eval/scorer.go`
- `eval/scorer_test.go`
- `eval/fixtures.go`
- `eval/fixtures/chronomancer.yaml`
- `tests/unit/test_eval_runner.py`

Interfaces: fixture category `chronomancer`; expect fields `decision_equals`, `echo_turns_equals`, `wants_counter`, `share_min`, `share_max`.

Acceptance:
- `just eval` passes with at least ten chronomancer fixtures covering each rule at its boundary.
- `go test` covers a pass and a fail for each new expect field.

## T-04 — The gate

Result: the gate's boss is a Chronomancer and the terminal game plays her rewinds.

Files:
- `src/content/encounters.py`
- `src/play.py`
- `src/states/combat_cli.py`
- `tests/unit/test_encounters.py`
- `tests/unit/test_combat_cli.py`
- `tests/integration/test_play.py`
- `STATUS.md`

Acceptance:
- The scenario under "Enemy rewinds are shown and honoured" has a passing test.
- `just play gate` can be played to an outcome with rewinds on both sides.
