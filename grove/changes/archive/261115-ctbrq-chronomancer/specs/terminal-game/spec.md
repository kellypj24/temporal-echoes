# Changes to terminal-game

Changes to [terminal-game](../../../../specs/terminal-game/spec.md) as it stands at `728d66b`.

## ADDED Requirements

### Requirement: Enemy rewinds are shown and honoured

When an enemy rewinds, the game shall say so, draw the earlier board, and ask the player for a command without advancing the turn.

#### Scenario: The gate

- GIVEN the `gate` encounter and a script that attacks the Chronomancer every turn
- WHEN she drops below 40 percent HP holding charge
- THEN the output says she rewinds time and the fight still ends (`tests/integration/test_play.py`)

## REMOVED Requirements

### Requirement: Designated counterers

Replaced by "Counter decisions belong to each enemy" in `timeline-mechanics`: the gate's boss counters because she is a Chronomancer, not because the encounter flags her.
