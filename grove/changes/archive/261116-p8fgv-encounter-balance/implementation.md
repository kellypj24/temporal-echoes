# Implementation: Encounter balance

## Tasks

### T-01 — Combat rules: Break once, defend

Status: done

Evidence: `Enemy.take_damage` no longer multiplies by the Break bonus; `DamageCalculator` remains the one place it is applied. `Combatant.is_defending` is set by a defend, cleared when the combatant's next turn begins, and halves attack damage in `CombatContext._execute_attack`. Replay rebuilds the flag and applies the same halving before its determinism check; the failed-rewind snapshot carries it. `tests/integration/test_balance_rules.py` `TestBreakBonusAppliedOnce` (2) and `TestDefend` (4).

Deviation: echoes ignore both the Break bonus and a defend. An echo applies recorded damage with no calculation, and keeping it that way keeps echo replay free of state. Written into the Echo Cast requirement.

### T-02 — Rewind: paid, in own turns, round kept

Status: done

Evidence: `TemporalSystem.rewind` takes `cost`; after replay it deducts `min(cost, charge)` and stores it as a CHARGE_SPENT on the new branch at the target turn with `carried: true`, so later replays apply it. `CombatContext` keeps the turn count at the start of each player turn (rebuilt on replay from the player's ACTION_EXECUTED and Echo Cast CHARGE_SPENT events) and `rewind_player_turns` uses it. BOOST_POINT_GAINED, stored once per round start, now carries `round_number`, and replay takes the round from it. `TestRewindIsPaidFor` (4), `TestRewindOwnTurns` (5).

Without the round fix, own-turn rewinds would have been an exploit: rewinding to the first turn of a round replayed that round's start, granting its Boost Point and charge again.

Tests changed for the new cost: two in `tests/integration/test_counter_stop_scenarios.py`, two in `tests/integration/test_chronomancer_scenarios.py`.

### T-03 — Counter prompt and board

Status: done

Evidence: `ArchetypeCounterPolicy(ask_player=)`; `CombatCLI.ask_counter`; `src/play.py` wires the two. The rewind prompt counts the player's own turns. Enemy lines show charge pips; defending combatants show `DEF`. `tests/unit/test_combat_cli.py` (4 new or rewritten), `tests/unit/test_console.py` (1 new).

### T-04 — Tuning and its measures

Status: done

Evidence: `tests/fixtures/autopilot.py` (`masher`, `fighter`, `tactician`), `scripts/balance.py`, `just balance`, `tests/integration/test_balance.py` (6, seeds 0 to 39). `just check`: ruff, mypy, 751 tests, Go tests, `grove check` clean.

Values chosen:

| What | Before | After |
|---|---|---|
| Echo damage scale | 0.5 | 1.0 |
| Clockwork Sentry HP | 340 | 680 |
| Raiders HP (each) | 260 | 520 |
| Chronomancer HP / attack | 380 / 30 | 3750 / 27 |
| Gate Acolytes HP / attack (each) | 150 / 22 | 500 / 28 |

`just balance 100`, sequence with wounds carried (wins of fights started; mean rounds):

| Player | Sundial | Crossroads | Gate | Gate rounds |
|---|---|---|---|---|
| masher | 100/100 | 100/100 | 0/100 | 4.0 |
| fighter | 100/100 | 100/100 | 36/100 | 11.4 |
| tactician | 100/100 | 100/100 | 76/100 | 10.6 |

How the values were reached, over 40 to 100 seeds per trial:
- Scaling all gate enemies' HP and attack together never separated the players: attack-only won 10 to 60 percent wherever the full script won 60 to 90.
- Making the acolytes hit harder than the boss and die faster did: attack-only hits the first living enemy, the boss, and is killed by the acolytes.
- At echo scale 0.5 the script with no time abilities beat the one with them. Removing one tool at a time on a hard gate (wins of 40): none 18, Echo 30 at scale 1.0 and 23 at 0.5, Counter-Stop 25, Echo with Counter-Stop 35, rewind-as-undo 16 to 19.
- Rewinding after a costly round and then defending lowered the win rate, and without the defend it was neutral alone and harmful beside Echo, which needs the same charge. The script now rewinds as an undo only after losing a quarter of max HP in a round, which is rare; its rewinds are almost all baits.

Limits of the evidence:
- The measures are of three scripts, not of people. No one has played the tuned sequence by hand.
- The scripts read `enemy.archetype` to know who counters; a player infers it from the name.
- 400 full games with random input after the change: no replay error, no exception, 0 sequences cleared.

## Scenarios

- combat "Halved hit": tests/integration/test_balance_rules.py TestDefend test_defending_halves_the_next_hit, passed
- combat "Ends with the next turn": tests/integration/test_balance_rules.py test_defend_ends_when_the_defenders_next_turn_begins, passed
- combat "Breaking hit": tests/unit/test_entities.py, passed
- combat "Hit on a broken enemy": tests/integration/test_balance_rules.py TestBreakBonusAppliedOnce, passed
- timeline-mechanics "Three enemies between turns": tests/integration/test_balance_rules.py test_two_enemies_between_turns_still_cost_one_charge (three enemies; the name undercounts), passed
- timeline-mechanics "More turns than taken": tests/integration/test_balance_rules.py test_more_turns_than_taken_or_than_charge_is_refused, passed
- timeline-mechanics "Rewind to the first turn of a round": tests/integration/test_balance_rules.py test_round_does_not_restart_after_rewinding_to_its_first_turn, passed
- timeline-mechanics "One turn back": tests/integration/test_balance_rules.py test_the_cost_stays_spent_on_the_new_branch, passed
- timeline-mechanics "Not enough charge": tests/unit/test_temporal.py, passed
- timeline-mechanics "Paid again on replay": tests/integration/test_balance_rules.py test_a_later_rewind_through_that_point_still_charges_for_it, passed
- timeline-mechanics "Echo of an attack": tests/unit/test_echo.py test_echo_attack_deals_the_recorded_damage_scaled, passed
- timeline-mechanics "Original target is dead": tests/unit/test_echo.py, passed
- timeline-mechanics "Broken, defending target": tests/integration/test_balance_rules.py test_echo_ignores_break_and_defend, passed
- timeline-mechanics "Bait the counter": tests/integration/test_chronomancer_scenarios.py test_bait_the_counter_then_rewind_freely, passed
- timeline-mechanics "No Chronomancer present": tests/unit/test_chronomancer.py test_without_a_chronomancer_nobody_counters, passed
- timeline-mechanics "Nobody to ask": tests/unit/test_chronomancer.py test_player_side_never_counters, passed
- terminal-game "Back to the start of the last turn": tests/unit/test_combat_cli.py test_rewind_returns_to_the_start_of_the_players_last_turn_and_keeps_the_turn, passed
- terminal-game "No turn taken yet": tests/unit/test_combat_cli.py test_rewind_without_charge_or_a_turn_to_undo_is_refused, passed
- terminal-game "Counter her rewind": tests/unit/test_combat_cli.py test_player_is_offered_a_counter_and_can_take_it, passed
- terminal-game "Decline": tests/unit/test_combat_cli.py test_declining_the_counter_lets_the_cast_through, passed
- terminal-game "Charge and defend markers": tests/unit/test_console.py test_board_shows_enemy_charge_and_who_is_defending, passed
- terminal-game "Forty seeds": tests/integration/test_balance.py, passed
- terminal-game "Report": `just balance 100` run by hand, output above; no automated test

## Reconciliation

- combat: applied to specs/combat/spec.md
- timeline-mechanics: applied to specs/timeline-mechanics/spec.md
- terminal-game: applied to specs/terminal-game/spec.md
