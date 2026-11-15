# Changes to combat

Changes to [combat](../../../../specs/combat/spec.md) as it stands at `728d66b`.

## MODIFIED Requirements

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
