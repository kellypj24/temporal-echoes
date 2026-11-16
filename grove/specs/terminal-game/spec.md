# Terminal game

## Purpose

The game as it is played: a text front end that drives the combat and timeline engines from a terminal, one authored encounter at a time or all of them in sequence.

## Boundaries

Covers `src/play.py`, `src/states/combat_cli.py`, `src/ui/console.py` and `src/content/`. The rules of a fight are in `combat` and `timeline-mechanics`. Balance is agreed as measures of scripted players in `tests/fixtures/autopilot.py`, not as stat values. Saving a game, graphics and LLM narration are not agreed here.

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

## History

- [261115-jk63e](../../changes/archive/261115-jk63e-playable-terminal-game/) Playable terminal game
- [261115-ctbrq](../../changes/archive/261115-ctbrq-chronomancer/) Chronomancer
- [261116-p8fgv](../../changes/archive/261116-p8fgv-encounter-balance/) Encounter balance
