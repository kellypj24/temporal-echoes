## T-01 — Combat rules: Break once, defend

Result: the Break bonus is applied once and defend halves attacks until the defender's next turn, live and under replay.

Files:
- `src/entities/enemy.py`
- `src/entities/combatant.py`
- `src/core/combat.py`
- `src/core/temporal.py`
- `tests/integration/test_balance_rules.py`
- `tests/unit/test_entities.py`
- `tests/integration/test_combat_scenarios.py`

Interfaces: `Combatant.is_defending`, `DEFEND_DAMAGE_SCALE`.

Acceptance:
- The scenarios of combat's "Defend" and "Shields and Break" have passing tests.
- A rewind across a defend rebuilds who is defending.

## T-02 — Rewind: paid, in own turns, round kept

Result: a rewind's cost stays spent; the player can rewind by their own turns; a rewind does not restart a round.

Files:
- `src/core/temporal.py`
- `src/core/combat.py`
- `tests/integration/test_balance_rules.py`
- `tests/integration/test_counter_stop_scenarios.py`
- `tests/integration/test_chronomancer_scenarios.py`

Interfaces: `TemporalSystem.rewind(..., cost=)`, `CombatContext.rewind_player_turns`, `CombatContext.player_turns_taken`; CHARGE_SPENT gains `carried`; BOOST_POINT_GAINED gains `round_number`.

Constraints: no new event type; events stored before this change still replay.

Acceptance:
- The scenarios of "Rewind", "Rewind in the player's own turns" and "A round is not restarted by a rewind" have passing tests.

## T-03 — Counter prompt and board

Result: the terminal game asks the player to counter enemy casts, rewinds by the player's turns, and shows enemy charge and defend markers.

Files:
- `src/core/temporal.py`
- `src/states/combat_cli.py`
- `src/ui/console.py`
- `src/play.py`
- `tests/unit/test_combat_cli.py`
- `tests/unit/test_console.py`
- `tests/unit/test_chronomancer.py`

Interfaces: `ArchetypeCounterPolicy(ask_player=)`, `CombatCLI.ask_counter`, `build_combat(..., counter_policy=)`.

Acceptance:
- The scenarios of "Rewind by own turns", "Counter prompt", "The board shows what decisions need" and "Counter decisions belong to each enemy" have passing tests.

## T-04 — Tuning and its measures

Result: the authored sequence meets the balance measures, and they are held by tests and printable on demand.

Files:
- `src/content/encounters.py`
- `src/core/temporal.py`
- `tests/fixtures/autopilot.py`
- `tests/integration/test_balance.py`
- `tests/integration/test_play.py`
- `tests/unit/test_echo.py`
- `tests/integration/test_echo_scenarios.py`
- `scripts/balance.py`
- `justfile`
- `README.md`
- `STATUS.md`

Interfaces: `just balance [seeds]`; scripted players `masher`, `fighter`, `tactician`.

Acceptance:
- The scenarios of "Balance of the authored sequence" and "Echo Cast" have passing tests.
- `just balance 100` agrees with the tests' measures.
