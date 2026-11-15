# Chronomancer

## Problem

No enemy uses the temporal abilities. `grove/specs/timeline-mechanics/spec.md` at `728d66b` puts "an enemy that chooses to use these abilities" outside what is agreed, and the gate encounter fakes one: `DesignatedCounterPolicy` (`src/core/temporal.py` at `728d66b`) counters every cast and does nothing else. The Phase 3 design note (`docs/archive/assignments/active/phase-3-timeline-mechanics/DESIGN.md`) names symmetry as a pillar: enemy Chronomancers wield the same primitives as the player.

The plan this change converts is `STEP-7-PLAN.md`, commit `03de1c4` on branch `phase/3-step-7-chronomancer`. That branch is not merged, so what the change needs from the plan is restated here and in the change specs.

Two faults in replay surfaced while building this, both present at `728d66b` and both made common by an enemy that rewinds:

- A second rewind after play on a new branch fails with a determinism error. `_replay_events` takes every event of every earlier branch up to the target turn, including the abandoned tail of a branch that a previous rewind replaced.
- A rewind across a shield break fails. The live path stores SHIELD_BROKEN before the ACTION_EXECUTED that causes it and replay asserts the enemy is already broken; break recovery is applied by `advance_turn` and is not an event, so replay never applies it. Every authored enemy is weak to physical attacks, so this is reachable in any fight.

A third fault is in the player's turn: an Echo Cast rejected for lack of charge leaves combat in the executing phase with the turn counted (`CombatContext.submit_player_action` at `728d66b`).

## Intended outcome

The gate's boss is a Chronomancer: it rewinds the player's last action when badly hurt, at most twice a fight; casts Echo when it is the last enemy standing; holds its charge to Counter-Stop when the player threatens temporal play; and counters every cast it can. Its rules are deterministic and readable, so the player can bait the counter with a cheap cast and then rewind freely. Rewinds work any number of times in a fight, across shield breaks.

## Scope

### In scope

- `ChronomancerAI`, a fifth archetype, and an `EnemyAI.wants_counter_stop` hook.
- Enemy rewind and Echo Cast through `execute_enemy_turn`, with the rule that lets the current enemy rewind before its turn resolves.
- `ArchetypeCounterPolicy` as the default counter policy.
- Removing `DesignatedCounterPolicy` and the `counters` flag on encounter enemies; the gate boss becomes a `chronomancer`.
- The three faults under Problem.
- A `chronomancer` category in the Go eval harness, with fixtures.
- The terminal game honouring an enemy rewind.

### Out of scope

- Asking the player whether to counter an enemy cast. The player side never counters; change `encounter-balance` or a later one may add the prompt.
- Tuning thresholds and encounter stats; change `encounter-balance`.
- Deeper enemy rewinds and boss variants.
- LLM taunts; Phase 4. Cast animations; Phase 5.

## Decisions

1. Rewind is the Chronomancer's turn action, taken at the top of its turn before anything resolves. STEP-7-PLAN §2.1, "decided 2026-07-15 with PJ". Time snaps back with the player acting.
2. Temporal abilities fire on deterministic rules over the weighted-random base mix; counter decisions draw no random number. STEP-7-PLAN §2.2, same date. The player can read and bait the rules.
3. At most 2 rewinds per combat, counted from persistent TEMPORAL_REWIND events. STEP-7-PLAN §2.3, same date. A rewind's own charge spend sits past the fork on the abandoned branch, so charge cannot bound rewinds; the event log is the AI's replay-safe memory.
4. Evaluation is a Go harness category plus pytest. STEP-7-PLAN §2.4, same date.
5. The Step 7 plan becomes this Grove change, built after the terminal game and before balance. PJ, 2026-11-15: "go with all your recommendations".

## Open questions

None blocking. Can wait:

- Whether a rewind should keep refunding its own cost. Today the charge spent on a rewind is restored by the rewind, for the player and the Chronomancer alike; only the cap bounds the Chronomancer. For `encounter-balance`.
- Whether the player should be offered a Counter-Stop against the Chronomancer's casts.

## Related documents

- Requirements: [specs/timeline-mechanics/spec.md](specs/timeline-mechanics/spec.md), [specs/combat/spec.md](specs/combat/spec.md), [specs/terminal-game/spec.md](specs/terminal-game/spec.md)
- Tasks: [tasks.md](tasks.md)
