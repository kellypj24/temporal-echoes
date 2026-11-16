# Changes to timeline-mechanics

Changes to [timeline-mechanics](../../../../specs/timeline-mechanics/spec.md) as it stands at `6bb1db9`.

## ADDED Requirements

### Requirement: Rewind in the player's own turns

When the player rewinds N of their own turns, the system shall return the fight to the start of the Nth most recent turn the player took, at a cost of N charge whatever happened in between; an Echo Cast counts as a turn taken.

#### Scenario: Three enemies between turns

- GIVEN a player who has taken one turn, followed by three enemy turns
- WHEN the player rewinds 1 of their turns
- THEN the fight is at turn 0 and 1 charge is spent (`tests/integration/test_balance_rules.py`)

#### Scenario: More turns than taken

- GIVEN a player who has taken one turn
- WHEN the player rewinds 2 of their turns
- THEN the cast is rejected and nothing is stored

### Requirement: A round is not restarted by a rewind

When a rewind lands between a round's start and its first turn, the system shall keep that round's number, so that playing on reaches the next round once.

#### Scenario: Rewind to the first turn of a round

- GIVEN a player who acts first, rewound to the start of their turn in round 2
- WHEN the round is played out
- THEN the next round is 3 and the player has gained 1 Boost Point, not 2 (`tests/integration/test_balance_rules.py`)

## MODIFIED Requirements

### Requirement: Rewind

When a combatant rewinds to an earlier turn at a cost of 1 to 3 charge, by default 1 per combatant turn rewound, the system shall rebuild combat-local state as it stood at that turn by reseeding and replaying the rewindable events, continue on a new branch, and leave the player to act; the caster's charge shall then be its value at that turn less the cost, never below 0, and that deduction shall hold through any later rewind that passes through the same point. A rewind shall not consume the caster's turn.

#### Scenario: One turn back

- GIVEN a fight in round 4 and a player holding 3 charge
- WHEN the player rewinds 1 turn
- THEN HP, Boost Points, shields and turn position equal their values one turn earlier, the branch id is 1, the player is awaiting input, and the player holds 2 charge (`tests/unit/test_temporal.py`, `tests/integration/test_rewind_scenarios.py`, `tests/integration/test_balance_rules.py`)

#### Scenario: Not enough charge

- GIVEN a player holding 1 charge
- WHEN the player rewinds 2 turns
- THEN the cast is rejected and no event is stored

#### Scenario: Paid again on replay

- GIVEN a player who rewound once and played on
- WHEN the player rewinds to a turn after the first rewind's target
- THEN the charge rebuilt for that turn already has the first rewind's cost taken from it

### Requirement: Echo Cast

When a combatant casts Echo for N turns (1 to 3) at a flat cost of 2 charge, the cast shall consume its turn, and on each of its next N turns an echo shall repeat one of its last N executed actions in order, dealing the recorded damage, at least 1, with no new random draw and unchanged by the target's broken or defending state.

#### Scenario: Echo of an attack

- GIVEN a player whose last action dealt 300 damage
- WHEN the player casts Echo for 1 turn and then takes a turn
- THEN the echo deals 300 damage on that later turn and none on the cast turn (`tests/unit/test_echo.py`, `tests/integration/test_echo_scenarios.py`)

#### Scenario: Original target is dead

- GIVEN an echo whose recorded target has been defeated
- WHEN the echo acts
- THEN it hits the first living enemy in roster order, or fizzles if there is none

#### Scenario: Broken, defending target

- GIVEN an echo and a target that is both broken and defending
- WHEN the echo acts
- THEN it deals exactly the recorded damage (`tests/integration/test_balance_rules.py`)

### Requirement: Counter decisions belong to each enemy

Unless a combat is given another policy, the system shall offer a player's announced cast to each eligible enemy in roster order and the first whose archetype wants to counter shall Counter-Stop it; a Chronomancer always wants to, other archetypes never do. An enemy's announced cast shall be offered to the player only where a front end supplies a way to ask, and countered only if the player says yes.

#### Scenario: Bait the counter

- GIVEN a Chronomancer holding 3 charge and a player holding 3
- WHEN the player casts a 1-turn Echo and, a round later, rewinds
- THEN the Echo is countered and the rewind succeeds (`tests/integration/test_chronomancer_scenarios.py`)

#### Scenario: No Chronomancer present

- GIVEN enemies of the other four archetypes holding 3 charge
- WHEN the player rewinds
- THEN nobody counters (`tests/unit/test_chronomancer.py`)

#### Scenario: Nobody to ask

- GIVEN a combat with no way to ask the player, and a player holding 3 charge
- WHEN an enemy rewinds
- THEN the rewind is not countered (`tests/unit/test_chronomancer.py`)
