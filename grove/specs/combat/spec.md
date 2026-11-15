# Combat

## Purpose

Turn-based combat between one player and one or more enemies: turn order, damage, Boost Points, shields and Break, enemy action selection, flee, and the event log every fight leaves behind.

## Boundaries

Covers `src/core/combat.py`, `src/core/damage.py`, `src/core/ai.py`, `src/core/combat_events.py` and `src/entities/`. Temporal charge and the three temporal abilities are in `timeline-mechanics`. Rendering, input and authored encounters are not covered here. Folded from the Phase 2 plan and decisions, now in `docs/archive/assignments/active/phase-2-combat-system/`.

## Requirements

### Requirement: Seeded determinism

The same seed, combatants and sequence of player actions shall produce the same fight: the same damage, enemy actions, outcome and event sequence.

#### Scenario: Two runs

- GIVEN two combats built from the same seed and combatants
- WHEN the same player actions are submitted to each
- THEN their transcripts and event payloads are equal (`tests/integration/test_combat_scenarios.py`)

### Requirement: Damage formula

An attack shall deal `ATK × Power / (DEF × 0.5 + 10)`, times a random factor in [0.85, 1.00], times the boost, weakness (2.0), critical (1.5, 5% base chance) and Break (1.5) multipliers, clamped to [1, 9999].

#### Scenario: Floor

- GIVEN an attacker far weaker than the defender
- WHEN the attack resolves
- THEN it deals 1 damage (`tests/unit/test_damage.py`, `tests/unit/test_damage_properties.py`)

### Requirement: Boost Points

The player shall gain 1 Boost Point at the start of each round, hold at most 5, and may spend 1, 2 or 3 on an attack for a 1.5, 2.0 or 2.5 damage multiplier.

#### Scenario: Overspend

- GIVEN a player holding 1 Boost Point
- WHEN an attack spending 2 is submitted
- THEN the action is rejected and no Boost Points are spent (`tests/unit/test_entities.py`)

### Requirement: Shields and Break

When an attack hits an enemy's weakness while it is not broken, the enemy shall lose 1 shield point; when its shield reaches 0 it shall become broken, skip its next turn, and take 1.5 times damage until it recovers. The hit that breaks the shield deals normal damage.

#### Scenario: Breaking hit

- GIVEN an enemy with 1 shield point and a physical weakness
- WHEN it is hit by a physical attack
- THEN the hit deals unmultiplied damage, the enemy is broken, and its next turn is skipped (`tests/unit/test_entities.py`, `tests/integration/test_combat.py`)

### Requirement: Enemy archetypes

Each enemy shall choose its action by a seeded weighted draw whose weights depend on its archetype (aggressive, defensive, tactical, berserker, chronomancer) and the state of the fight, and the choice shall carry no state between turns. A chronomancer's temporal rules, in `timeline-mechanics`, are applied before the draw.

#### Scenario: Replay

- GIVEN an enemy AI and a combat state
- WHEN the AI is reseeded and asked again
- THEN it returns the same action (`tests/unit/test_ai.py`)

#### Scenario: No state of its own

- GIVEN a Chronomancer's AI
- WHEN its attributes are listed
- THEN they are the enemy, the random generator and the base weights (`tests/unit/test_chronomancer.py`)

### Requirement: Flee

When the player flees, the attempt shall succeed with probability `50 + (player speed − mean living enemy speed)` percent, clamped to [10, 90], and a success shall end combat with the outcome fled.

#### Scenario: Slow player

- GIVEN a player 80 speed slower than the enemies
- WHEN the player flees
- THEN the chance used is 10 percent (`tests/integration/test_combat.py`)

### Requirement: Outcome

Combat shall end in victory when no enemy is alive and in defeat when the player's HP is 0, and shall accept no action afterwards.

#### Scenario: Last enemy falls

- GIVEN one enemy left at 1 HP
- WHEN the player's attack lands
- THEN the outcome is victory and a combat-ended event is stored (`tests/integration/test_combat_scenarios.py`)

### Requirement: Events are appended, never changed

Every state change in combat shall be stored as an event in `game_events`, and no stored event shall be updated or deleted.

#### Scenario: A full fight

- GIVEN a completed combat
- WHEN its events are read back in order
- THEN they begin with combat-started, end with combat-ended, and account for every action taken (`tests/unit/test_combat_events.py`, `tests/unit/test_event_store.py`)

## History

- [261115-ctbrq](../../changes/archive/261115-ctbrq-chronomancer/) Chronomancer
