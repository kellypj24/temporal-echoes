# Changes to combat

Changes to [combat](../../../../specs/combat/spec.md) as it stands at `6bb1db9`.

## ADDED Requirements

### Requirement: Defend

When a combatant defends, attacks against it shall deal half damage, rounded down and never less than 1, until its next turn begins.

#### Scenario: Halved hit

- GIVEN a player who defended this round
- WHEN an enemy attacks
- THEN the damage stored and the HP lost are half what the same attack deals to a player who did not defend (`tests/integration/test_balance_rules.py`)

#### Scenario: Ends with the next turn

- GIVEN a player who defended last round
- WHEN the player acts this round
- THEN the player is no longer defending

## MODIFIED Requirements

### Requirement: Shields and Break

When an attack hits an enemy's weakness while it is not broken, the enemy shall lose 1 shield point; when its shield reaches 0 it shall become broken, skip its next turn, and take 1.5 times damage from attacks, applied once, until it recovers. The hit that breaks the shield deals normal damage.

#### Scenario: Breaking hit

- GIVEN an enemy with 1 shield point and a physical weakness
- WHEN it is hit by a physical attack
- THEN the hit deals unmultiplied damage, the enemy is broken, and its next turn is skipped (`tests/unit/test_entities.py`, `tests/integration/test_combat.py`)

#### Scenario: Hit on a broken enemy

- GIVEN two fights from one seed, the enemy broken in one
- WHEN the player attacks
- THEN the broken enemy loses 1.5 times the HP, and the HP lost equals the damage stored (`tests/integration/test_balance_rules.py`)
