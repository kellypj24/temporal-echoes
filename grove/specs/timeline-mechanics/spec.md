# Timeline mechanics

## Purpose

Time as a combat resource. Any combatant holds temporal charge and can spend it to rewind the fight, to have a past self repeat earlier actions, or to cancel an opponent's temporal cast. The event log is the only rewind primitive: nothing is snapshotted and nothing is deleted.

## Boundaries

Covers `src/core/temporal.py`, the temporal paths of `src/core/combat.py`, the rewindable partition in `src/core/events.py`, and temporal charge on `src/entities/combatant.py`. Temporal abilities exist only inside a combat; the overworld is linear. An enemy that chooses to use these abilities, player-facing branch display, and visual effects are not agreed here. Folded from the Phase 3 design note and the Step 3, 5 and 6 plans, now in `docs/archive/assignments/active/phase-3-timeline-mechanics/`.

## Requirements

### Requirement: Charge economy

Each combatant shall start a combat with 0 temporal charge, gain 1 at the start of each round while alive, and hold at most 3; charge shall not carry between combats.

#### Scenario: Cap

- GIVEN a combatant holding 3 charge
- WHEN a round starts
- THEN it still holds 3 and no charge-regenerated event is stored (`tests/unit/test_combatant_charge.py`, `tests/unit/test_temporal_system.py`)

### Requirement: Rewind

When a combatant rewinds N turns (1 to 3) at a cost of N charge, the system shall rebuild combat-local state as it stood N turns earlier by reseeding and replaying the rewindable events, continue on a new branch, and leave the player to act; a rewind shall not consume the caster's turn.

#### Scenario: One turn back

- GIVEN a fight three turns in and a player holding 1 charge
- WHEN the player rewinds 1 turn
- THEN HP, Boost Points, shields, charge and turn position equal their values one turn earlier, the branch id is 1, and the player is awaiting input (`tests/unit/test_temporal.py`, `tests/integration/test_rewind_scenarios.py`)

#### Scenario: Not enough charge

- GIVEN a player holding 1 charge
- WHEN the player rewinds 2 turns
- THEN the cast is rejected and no event is stored

### Requirement: Rewinds are history

A rewind shall store a temporal-rewind event on the new branch and shall delete or alter no earlier event; events carry the branch they were emitted on.

#### Scenario: Log after a rewind

- GIVEN a fight that has been rewound once
- WHEN its events are read
- THEN every event from before the rewind is still present on branch 0 and later events are on branch 1 (`tests/integration/test_rewind_scenarios.py`)

### Requirement: Rewindable and persistent events

A rewind shall undo the effects of turn-started, action-executed, shield-broken, boost-point-gained, charge-spent, charge-regenerated, echo-spawned and echo-acted events, and shall leave every other event type applied.

#### Scenario: A counter survives a rewind

- GIVEN a Counter-Stop two turns ago
- WHEN the fight is rewound three turns
- THEN the counter-stop-triggered event still counts as having happened (`tests/integration/test_counter_stop_scenarios.py`)

### Requirement: Failed rewind restores state

If a rewind fails after its charge-spent event is stored, the system shall restore in-memory combat state, including the caster's charge and every RNG, to its value before the cast, keep the stored event, and raise a replay error.

#### Scenario: Replay raises

- GIVEN a rewind whose replay raises partway
- WHEN the error surfaces
- THEN combat state equals its pre-cast state and the charge-spent event remains (`tests/unit/test_temporal.py`)

### Requirement: Echo Cast

When a combatant casts Echo for N turns (1 to 3) at a flat cost of 2 charge, the cast shall consume its turn, and on each of its next N turns an echo shall repeat one of its last N executed actions in order, dealing half the recorded damage rounded down, at least 1, with no new random draw.

#### Scenario: Echo of an attack

- GIVEN a player whose last action dealt 300 damage
- WHEN the player casts Echo for 1 turn and then takes a turn
- THEN the echo deals 150 damage on that later turn and none on the cast turn (`tests/unit/test_echo.py`, `tests/integration/test_echo_scenarios.py`)

#### Scenario: Original target is dead

- GIVEN an echo whose recorded target has been defeated
- WHEN the echo acts
- THEN it hits the first living enemy in roster order, or fizzles if there is none

### Requirement: Echo limits

An echo shall be untargetable and outside the turn order; a side shall have at most one active echo; a recorded defend shall replay as no effect and a recorded flee as a fizzle; an echo shall act while its owner is stunned and not after its owner is dead.

#### Scenario: Second cast

- GIVEN a player with an active echo
- WHEN the player casts Echo again
- THEN the cast is rejected and no charge is spent (`tests/unit/test_echo.py`)

### Requirement: Counter-Stop

When a rewind or Echo Cast is announced, the system shall first spend the caster's charge, then offer one response to living opponents holding 3 charge, in roster order, through the counter policy; if one responds it shall spend 3 charge, the cast shall have no effect, and the caster's charge shall stay spent. A Counter-Stop cannot itself be countered and draws no random number.

#### Scenario: Countered rewind

- GIVEN a player holding 1 charge and an enemy holding 3 whose policy counters
- WHEN the player rewinds 1 turn
- THEN the fight stays on its branch, the player holds 0 charge, the enemy holds 0, and a counter-stop-triggered event is stored (`tests/unit/test_counter_stop.py`)

#### Scenario: Nobody can respond

- GIVEN no opponent holding 3 charge
- WHEN a cast is announced
- THEN the policy is not consulted and the cast resolves

### Requirement: Invalid casts announce nothing

If a cast is invalid (insufficient charge, turns out of range, no history to rewind into or to echo), the system shall reject it before storing any event or consulting the counter policy.

#### Scenario: Bait with an unaffordable cast

- GIVEN a player holding 0 charge and an enemy holding 3
- WHEN the player rewinds
- THEN the cast is rejected and the enemy still holds 3 (`tests/unit/test_counter_stop.py`)

### Requirement: Deterministic under all three abilities

A fight containing a rewind, an Echo Cast and a Counter-Stop shall, from the same seed and inputs, produce an identical event log.

#### Scenario: Chess clock

- GIVEN the chess-clock scenario run twice
- WHEN the hashes of the two event logs are compared
- THEN they are equal (`tests/integration/test_counter_stop_scenarios.py`)
