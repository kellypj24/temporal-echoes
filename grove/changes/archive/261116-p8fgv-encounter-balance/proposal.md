# Encounter balance

## Problem

The terminal game can be won by attacking every turn. Measured at `6bb1db9` over 200 seeds of the full sequence, a script that only attacks cleared all three fights 200 times out of 200, in 2 to 3 rounds each; a script using boosts, Echo and rewind did no better. Fights end before temporal charge accumulates.

Five rules stood in the way of tuning, recorded in the archived `chronomancer` change's `implementation.md`:

- A hit on a broken enemy was multiplied by 1.5 twice, in `DamageCalculator.calculate` and again in `Enemy.take_damage`; `grove/specs/combat/spec.md` says 1.5.
- Defend stored an event and changed nothing, while the terminal help said it halves incoming damage.
- A rewind restored the charge it had cost, so it was usually free.
- A rewind was measured in combatant turns: rewinding 1 at the start of the player's turn undid only the last enemy's action.
- The player was never offered a Counter-Stop against an enemy's cast.

## Intended outcome

Attacking every turn still wins the first two fights and loses the gate. A player who targets well and boosts but uses no time ability clears the sequence less than half the time; one who also uses Echo Cast, the rewind bait and Counter-Stop clears it at least 70 percent of the time, in a gate fight of 8 to 12 rounds. The five rules above do what a player would expect.

## Scope

### In scope

- The Break bonus applied once.
- Defend halves the damage of attacks until the defender's next turn.
- A rewind's cost stays spent.
- The terminal game's rewind is measured in the player's own turns, 1 charge each.
- The player is asked whether to Counter-Stop an enemy's cast.
- The board shows each enemy's temporal charge and who is defending.
- Echo damage scale and encounter stats, tuned against scripted players.
- The scripted players, a `just balance` report, and tests holding the targets.

### Out of scope

- New abilities, items, levelling, or more encounters.
- The enemy AI's rules. The Chronomancer's thresholds are unchanged.
- Rebalancing for a human's experience beyond the scripted measures; that needs play.

## Decisions

PJ, 2026-11-16, to seven numbered recommendations: "go with all your recommendations".

1. Break multiplier fixed to 1.5, applied once. The spec already said so.
2. Defend halves incoming damage until your next turn. Matches the help text.
3. A rewind's cost stays spent after the rewind. Otherwise rewinds are free.
4. The terminal game rewinds to the start of your previous turn, at 1 charge each. A unit the player can reason about.
5. Stats tuned so the gate lasts 8 to 12 rounds for a competent player.
6. Targets: attack-only loses the gate in at least 90 percent of seeds; a scripted player using boost, defend, echo and rewind wins at least 70 percent.
7. The player is prompted to Counter-Stop the Chronomancer's casts.

PJ, 2026-11-15, on what playable means: the three encounters "tuned so rewind and echo are needed to win". This is why the change adds a third scripted player with no time abilities and a target for the gap between it and the full one.

## Open questions

None blocking. Can wait:

- Echo damage went from half to full to make time abilities decide the gate. Whether full-damage echoes feel right in play.
- The scripted player found no profitable use for rewinding as an undo; its rewinds are almost all the 1-charge bait that empties the Chronomancer's pool. Whether rewind needs to be stronger as an undo.

## Related documents

- Requirements: [specs/combat/spec.md](specs/combat/spec.md), [specs/timeline-mechanics/spec.md](specs/timeline-mechanics/spec.md), [specs/terminal-game/spec.md](specs/terminal-game/spec.md)
- Tasks: [tasks.md](tasks.md)
