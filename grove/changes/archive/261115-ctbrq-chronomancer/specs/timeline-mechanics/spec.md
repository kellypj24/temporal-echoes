# Changes to timeline-mechanics

Changes to [timeline-mechanics](../../../../specs/timeline-mechanics/spec.md) as it stands at `728d66b`.

## ADDED Requirements

### Requirement: Rewind follows the live lineage

When a fight that has already been rewound is rewound again, the system shall rebuild state from only the events that are still part of its history: an event on an earlier branch counts only if its turn is at or before every later fork.

#### Scenario: Second rewind after play on a new branch

- GIVEN a fight rewound from turn 6 to turn 4 and then played to turn 8
- WHEN the player rewinds 2 turns
- THEN the rewind succeeds and state equals what it was after turn 6 on the new branch (`tests/integration/test_rewind_lineage.py`)

#### Scenario: Rewinding past an earlier fork

- GIVEN a fight rewound to turn 3 and played to turn 5
- WHEN the player rewinds 3 turns
- THEN state equals what it was after turn 2 on the original line

### Requirement: Rewind rebuilds shield breaks and recovery

A rewind shall rebuild each enemy's shield, broken state and recovery as they stood at the target turn.

#### Scenario: Across a break

- GIVEN an enemy broken on turn 1 and recovered at the end of turn 2
- WHEN the player rewinds to turn 1
- THEN the enemy is broken with 0 shield (`tests/integration/test_rewind_lineage.py`)

#### Scenario: After a recovery

- GIVEN an enemy that has been broken and has recovered several times
- WHEN the player rewinds 2 turns
- THEN its HP, shield and broken state equal their values at the target turn

### Requirement: Enemy rewind as a turn action

While it is an enemy's turn and nothing in that turn has resolved, that enemy may rewind; the fight shall then be at the earlier turn awaiting the player's input, and the enemy's turn shall not be taken. No other combatant may rewind while a turn is executing.

#### Scenario: Undo the player's hit

- GIVEN a Chronomancer the player has just hit below 40 percent HP, holding 1 charge
- WHEN its turn comes
- THEN its HP is restored, the fight is on a new branch awaiting the player, and the stored rewind names the Chronomancer as caster (`tests/integration/test_chronomancer_scenarios.py`)

#### Scenario: Not its turn

- GIVEN an enemy that is not the current combatant, holding 1 charge
- WHEN it rewinds during another enemy's turn
- THEN the cast is rejected (`tests/unit/test_chronomancer.py`)

#### Scenario: Countered

- GIVEN a Chronomancer whose rewind is Counter-Stopped
- WHEN its turn continues
- THEN no branch is created and the turn passes as a defend

### Requirement: Chronomancer rules

A Chronomancer shall choose its action by these rules, first match first, drawing no random number for them: rewind 1 turn when its HP is below 40 percent, it holds at least 1 charge, it has completed fewer than 2 rewinds in this combat and a turn exists to rewind into; cast Echo over its whole action history, up to 3 turns, when it is the only living enemy, holds at least 2 charge, has at least one action to echo, has no live echo, and the player holds fewer than 2 charge. Otherwise it shall choose as other archetypes do, from the weights attack 45, defend 35, ability 20.

#### Scenario: Threshold

- GIVEN a Chronomancer holding 1 charge
- WHEN its HP is 39 percent and when it is 40 percent
- THEN it rewinds at 39 and does not at 40 (`tests/unit/test_chronomancer.py`, `eval/fixtures/chronomancer.yaml`)

#### Scenario: Cap survives the rewinds it counts

- GIVEN a Chronomancer that has rewound twice in this combat
- WHEN it is hurt again with charge to spare
- THEN it does not rewind, and the fight ends (`tests/integration/test_chronomancer_scenarios.py`)

#### Scenario: Charge held for a counter

- GIVEN a lone Chronomancer holding 3 charge and a player holding 2
- WHEN its turn comes
- THEN it does not cast Echo

#### Scenario: Survival before hoarding

- GIVEN a hurt Chronomancer and a player holding 3 charge
- WHEN its turn comes
- THEN it rewinds

### Requirement: Counter decisions belong to each enemy

Unless a combat is given another policy, the system shall offer a player's announced cast to each eligible enemy in roster order and the first whose archetype wants to counter shall Counter-Stop it; a Chronomancer always wants to, other archetypes never do, and the player side never counters.

#### Scenario: Bait the counter

- GIVEN a Chronomancer holding 3 charge and a player holding 3
- WHEN the player casts a 1-turn Echo and, a round later, rewinds
- THEN the Echo is countered and the rewind succeeds (`tests/integration/test_chronomancer_scenarios.py`)

#### Scenario: No Chronomancer present

- GIVEN enemies of the other four archetypes holding 3 charge
- WHEN the player rewinds
- THEN nobody counters (`tests/unit/test_chronomancer.py`)

### Requirement: Rejected Echo Cast keeps the turn

If the player's Echo Cast is invalid, the system shall leave the fight awaiting the player's input with no turn counted.

#### Scenario: No charge

- GIVEN a player holding 0 charge on their turn
- WHEN they cast Echo
- THEN the cast is rejected and their next action is accepted in the same turn (`tests/integration/test_rewind_lineage.py`)

## MODIFIED Requirements

### Requirement: Deterministic under all three abilities

A fight containing rewinds by both sides, an Echo Cast and a Counter-Stop shall, from the same seed and inputs, produce an identical event log.

#### Scenario: Chess clock

- GIVEN the chess-clock scenario run twice
- WHEN the hashes of the two event logs are compared
- THEN they are equal (`tests/integration/test_counter_stop_scenarios.py`)

#### Scenario: Mirror match

- GIVEN a seeded fight in which the player and a Chronomancer both rewind
- WHEN it is run twice
- THEN the two event logs are equal, event for event (`tests/integration/test_chronomancer_scenarios.py`)
