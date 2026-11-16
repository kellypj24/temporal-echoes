# Changes to terminal-game

Changes to [terminal-game](../../../../specs/terminal-game/spec.md) as it stands at `6bb1db9`.

## ADDED Requirements

### Requirement: Rewind by own turns

When the player chooses rewind, the game shall ask how many of their own turns to undo, up to the lesser of their charge and the turns they have taken, and shall refuse with a message when either is 0.

#### Scenario: Back to the start of the last turn

- GIVEN the `gate` encounter, a defend in round 1 and the player's turn in round 2
- WHEN the player rewinds 1
- THEN the board shows round 1 before the defend, the player holds 0 charge, and the player is asked for a command (`tests/unit/test_combat_cli.py`)

#### Scenario: No turn taken yet

- GIVEN the player's first turn of a fight
- WHEN the player chooses rewind
- THEN the game says there is nothing to rewind

### Requirement: Counter prompt

When an enemy announces a rewind or an Echo Cast and the player holds 3 charge, the game shall say what the enemy is doing and ask whether to Counter-Stop it; any answer but yes lets the cast through.

#### Scenario: Counter her rewind

- GIVEN a hurt Chronomancer holding 1 charge and a player holding 3
- WHEN her turn comes and the player answers yes
- THEN she does not rewind and the fight stays on its branch (`tests/unit/test_combat_cli.py`)

#### Scenario: Decline

- GIVEN the same fight
- WHEN the player presses enter
- THEN she rewinds

### Requirement: The board shows what decisions need

Before each player turn the board shall show each living enemy's temporal charge and mark every combatant that is defending.

#### Scenario: Charge and defend markers

- GIVEN an enemy holding 2 charge that defended
- WHEN the board is drawn
- THEN its line shows two of three charge pips and a DEF marker (`tests/unit/test_console.py`)

### Requirement: Balance of the authored sequence

Played by the scripted players in `tests/fixtures/autopilot.py` over fixed seeds, the authored sequence shall meet these measures: a player who attacks the first living enemy every turn wins the first two fights and clears the sequence in at most 10 percent of seeds; a player who targets well and boosts but uses no time ability clears it in at most 50 percent; a player who also uses Echo Cast, rewind and Counter-Stop clears it in at least 70 percent, at least 25 points more than without them, in a gate fight that averages 8 to 12 rounds.

#### Scenario: Forty seeds

- GIVEN the three scripted players and seeds 0 to 39
- WHEN each plays the sequence with wounds carried
- THEN every measure above holds (`tests/integration/test_balance.py`)

#### Scenario: Report

- GIVEN the repository
- WHEN `just balance` is run
- THEN it prints each scripted player's wins, HP left and rounds per encounter
