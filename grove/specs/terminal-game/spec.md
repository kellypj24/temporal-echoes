# Terminal game

## Purpose

The game as it is played: a text front end that drives the combat and timeline engines from a terminal, one authored encounter at a time or all of them in sequence.

## Boundaries

Covers `src/play.py`, `src/states/combat_cli.py`, `src/ui/console.py` and `src/content/`. The rules of a fight are in `combat` and `timeline-mechanics`. Encounter tuning, saving a game, graphics and LLM narration are not agreed here.

## Requirements

### Requirement: Play one encounter

When the game is started with an encounter id, the system shall play that encounter in the terminal until victory, defeat, escape or quit, showing each line the engine logs and, before each player turn, the HP, Boost Points, temporal charge and shields of every combatant.

#### Scenario: Scripted victory

- GIVEN the `sundial` encounter and a script that attacks every turn
- WHEN the game runs with input and output injected
- THEN the outcome is victory and the output ends with the victory banner (`tests/integration/test_play.py`)

#### Scenario: Unknown encounter

- GIVEN an id that names no encounter
- WHEN the game is started with it
- THEN it prints the known ids to stderr and exits with status 2

### Requirement: Every engine action is reachable

While it is the player's turn, the system shall accept attack on a numbered enemy, boosted attack, defend, flee, Echo Cast and rewind, and shall reject malformed input with a message and ask again without spending the turn.

#### Scenario: Rewind keeps the turn

- GIVEN a player holding 1 charge after one full round
- WHEN the player enters rewind, 1 turn
- THEN the board shows the earlier state and the player is asked for a command again (`tests/unit/test_combat_cli.py`)

#### Scenario: Defeated target

- GIVEN enemy 1 defeated and enemy 2 alive
- WHEN the player enters `1`
- THEN an error names the defeated enemy and no turn is spent

#### Scenario: Stable numbering

- GIVEN enemy 1 defeated
- WHEN the board is drawn
- THEN enemy 2 is still numbered 2

### Requirement: Play the sequence

When the game is started with no encounter id, the system shall play every encounter in authored order, start each later fight with the player's HP reduced by the HP missing at the end of the previous one, to no less than 1, and stop at the first outcome that is not victory.

#### Scenario: Wounds carry

- GIVEN a first fight won with 100 HP missing
- WHEN the second fight starts
- THEN the player's HP is the second encounter's maximum minus 100 (`tests/integration/test_play.py`)

#### Scenario: Defeat ends the game

- GIVEN a defeat in the second fight
- WHEN the fight ends
- THEN the third fight is not started

### Requirement: Replayable game

The same encounter, seed and input script shall produce the same output, line for line.

#### Scenario: Two runs

- GIVEN the `gate` encounter, one seed and one script that includes a rewind and an Echo Cast
- WHEN the game is run twice
- THEN the two outputs are equal (`tests/integration/test_play.py`)

### Requirement: Rendering holds no rules

The renderer shall format state it is given and decide nothing; the controller shall translate input into engine calls and compute no damage, cost or outcome.

#### Scenario: Import boundary

- GIVEN `src/ui/console.py`
- WHEN its imports are read
- THEN it imports nothing from `src/core` except types (`tests/unit/test_console.py`)

### Requirement: Enemy rewinds are shown and honoured

When an enemy rewinds, the game shall say so, draw the earlier board, and ask the player for a command without advancing the turn.

#### Scenario: The gate

- GIVEN the `gate` encounter and a script that attacks the Chronomancer every turn
- WHEN she drops below 40 percent HP holding charge
- THEN the output says she rewinds time and the fight still ends (`tests/integration/test_play.py`)

## History

- [261115-jk63e](../../changes/archive/261115-jk63e-playable-terminal-game/) Playable terminal game
- [261115-ctbrq](../../changes/archive/261115-ctbrq-chronomancer/) Chronomancer
