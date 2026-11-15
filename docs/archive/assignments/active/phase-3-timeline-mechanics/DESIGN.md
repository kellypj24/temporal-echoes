# Phase 3 — Timeline Mechanics (Design Note)

**Status**: Draft, pre-implementation. Lightweight by intent (~200 lines), per roadmap pivot 2026-05-11.

## Vision

Time is a combat resource. The player is a Temporal Echo — a being aware they've lived this fight before — and some enemies (Chronomancers) share the same gift. The best combats become a chess-match of rewinds, echoes, and counters where both sides watch each other's temporal meter as closely as their HP bars. Out of combat, time runs forward. No save-scumming, no overworld rewind. The mechanic is special *because* it's scoped.

## Pillars (locked-in)

1. **Combat-bounded.** Time abilities only exist inside `CombatContext`. The overworld is linear.
2. **Symmetric.** Enemy Chronomancers wield the same primitives the player does. Mirror-match is the aspiration.
3. **Resource-gated.** All temporal abilities draw from a `TemporalCharge` resource that regenerates slowly. Forces real decisions, not infinite undo.
4. **Event-replay-native.** Phase 1's immutable event log *is* the rewind primitive. No parallel snapshot system to keep in sync.
5. **M1-realistic.** Bounded rewind window. No exotic visuals. Single echo per side. Replays measured in turns, not in seconds.

## Player-facing Mechanics (proposed — review before code)

### Rewind
- Cost: 1 Charge per turn rewound. Cap: 3 turns / 3 Charges.
- Effect: Replay events `[N..current]` are unwound; player re-acts from turn N. The unwind itself is an event (see below) — nothing is deleted.
- Tells: screen ripple + ghost-echo of past-self acting before the player regains control.

### Echo Cast
- Cost: 2 Charges.
- Effect: Player's past-self from N turns ago acts alongside them for the next N turns, deterministically replaying its prior actions. Damage scaled (proposal: 50%).
- Creates 2v1 / 2v2 scenarios. Encourages setting up a strong past turn *before* casting.

### Counter-Stop
- Cost: 3 Charges. Reactive — usable in the response window on opponent's turn.
- **Interrupt model**: time abilities are *announced* (declared but unresolved) before they take effect. The acting side commits to the cast; the opposing side gets a response window to Counter-Stop. If countered, the ability fizzles and its Charge cost is still spent.
- Rationale (decision 2026-05-13): considered a true-counter model where rewinds resolve and can be undone afterward, but rejected — too prone to feeling like an unfair "computer cheats" moment, and adds a partial-resolution state the eval harness would have to model.
- The chess-clock tension: both sides eye the other's meter. Spending all your Charge attacking leaves you defenseless to a rewind; hoarding for counters means less offense.

## Charge Economy (decided 2026-05-13)

- **Per-combat.** Each combat starts with a fresh Charge pool; nothing carries between fights. Simpler to balance, and supports random enemies with similar abilities without cascading run-economy effects.
- Regeneration cadence and starting/cap values TBD during implementation tuning.

## Cross-Timeline Persistence (decided 2026-05-13)

- **Rewinds do not roll back the economy.** Items grabbed, XP earned, and story flags set in branch 0 persist into branch 1 even after a rewind.
- Architectural framing: rewinds operate on **combat-local state** only (HP, Boost, Break, Charge, turn position, combatant placement). They do not touch **persistent character state** (inventory, XP, quest flags, story progression). This aligns with constitution principle 4 (separation of concerns).
- Naive event replay would un-grant loot; the implementation must distinguish event types that are "combat-local and rewindable" vs. "persistent and sticky." Loot/XP/quest events stay applied regardless of branch.
- Player intuition: *"I'm walking between timelines and I keep what I find."*

### Event-type partitioning (decided 2026-05-13)

| Event type | Behavior | Notes |
|---|---|---|
| `damage_dealt`, `boost_gained`, `break_triggered`, `turn_ended` | **Combat-local** | Rewinds undo them. Replay rebuilds them on the new branch. |
| `charge_spent`, `charge_regenerated`, `echo_spawned`, `echo_acted` | **Combat-local** | Temporal abilities are themselves rewindable. |
| `temporal_rewind`, `counter_stop_triggered` | **Persistent** | The act of rewinding is a historical fact; it lives at the *new* turn position and is never itself undone. |
| `combat_started`, `combat_ended` | **Persistent** | The fight happened. Outcome resolves once at combat end against the active branch. |
| `loot_dropped`, `loot_grabbed`, `xp_awarded` | **Persistent / sticky** | Cross-timeline carry. Walking between timelines preserves inventory. |
| `enemy_killed` | **Persistent for meta-state, combat-local for in-fight presence** | The kill counts toward quests/XP and is not retracted. On rewind within the same combat, the enemy *re-appears* in its earlier state — quirky but consistent with the "walk between timelines" framing. The quest counter does not double-increment when the rewound enemy is killed again on the new branch (idempotency by `enemy_instance_id`). |

Implementation note: this partition is enforced at the event-store boundary. The rewind engine queries `is_rewindable(event_type) → bool`; persistent events are simply excluded from the replay set. The `enemy_killed` row is the only one with split behavior and needs explicit testing.

## Enemy Time-Mages

- New archetype `Chronomancer`, joins existing four (`Aggressive`, `Defensive`, `Tactical`, `Berserker`) in `src/core/ai.py`.
- Decision weights: spends Charge to rewind when below HP threshold; spends on echo when player is alone; hoards for Counter-Stop when player's Charge meter is high.
- Phase 3 keeps the AI rule-based (deterministic, eval-testable). LLM-driven temporal taunts/banter are deferred to Phase 4.
- Visual identity: each ability has a distinct cast animation so the player can read intent and bait counters.

## Architecture Fit

### Event log as the rewind primitive
- `CombatContext` already orchestrates event-emitting turn flow.
- A rewind to turn N becomes: re-instantiate `CombatContext` from genesis, replay events `0..N`, then resume from N+1 with new player input.
- **Critical**: the rewind action itself emits an event. Going from turn 7 → turn 5 emits `temporal_rewind(from=7, to=5)` at the *new* turn 5'. Constitution principle 1 (event sourcing is sacred) holds — nothing in `game_events` is ever deleted.

### New event types (proposed — expect refinement)
- `charge_spent(actor, amount, ability)`
- `charge_regenerated(actor, amount)`
- `temporal_rewind(actor, from_turn, to_turn, branch_id)`
- `echo_spawned(actor, source_turn, duration, branch_id)`
- `echo_acted(echo_id, action)` — echoes emit events too
- `counter_stop_triggered(actor, target_ability)`

### Branching, not overwriting
- Each rewind spawns a new `branch_id` (monotonic int, scoped to a `CombatContext`). Branch 0 is the original line; branch 1 starts at first rewind; etc.
- Events carry their `branch_id`. The player only ever *experiences* the current branch; older branches stay queryable for replay, debug, and dbt analytics.
- Replay-from-genesis still reaches the current player-facing state by following the branch chain.

### Schema evolution
- Per your input: expect to refine event payloads as we consume them in Phase 3. Don't freeze the schema now.
- `game_events` needs `branch_id` (column or sidecar). Migration scoped as Phase 3 Step 1.
- Plan for at least one mid-phase migration as the rewind/echo interactions surface real needs.

### Combat loop integration
- New `TemporalSystem` injected into `CombatContext` via DI (per constitution principle 2).
- Player turn flow: `input → temporal ability? → divert through TemporalSystem → resume damage/AI flow`.
- `TemporalCharge` lives on `Combatant` base class (alongside HP, Boost, Break) so both Player and Enemy carry it uniformly.

## M1 Constraints

- **Hot rewind window**: keep last 5 turns' replay state in memory; deeper rewinds rebuild from event log on demand (off the 60 FPS path).
- **Echo cap**: max 1 active echo per side at once. Avoids combinatorial explosion of replay threads.
- **No GPU shaders.** Time visuals are 2D sprite tricks (alpha ghosting, palette shift) affordable on integrated GPU.
- **Eval harness in Phase 3**: extend the mock provider to handle Chronomancer fixtures. AI archetype runs on rules; no LLM hit in eval.

## What's NOT in Phase 3

- Overworld time travel or save-scumming.
- Player-facing branch UI (branches are an internal mechanic).
- Persistent timelines across runs.
- Multiplayer / networked time fights.
- LLM-driven temporal narration (Phase 4).

## Open Questions (tuning, not blocking)

1. **Echo damage scaling**: flat 50%, or scaled by Charges spent? Or by how recent the echo source is? — tune during implementation.
2. **dbt impact**: branches as a `branch_id` dimension on the fact, or separate fact rows per branch? Affects every Phase 2 model that joins `game_events`. Resolve before Step 1 finalizes the migration shape.

## Decided

- Combat-bounded scope; no overworld rewind.
- Enemy Chronomancers symmetric with player (5th AI archetype).
- Charge economy is **per-combat**, not per-run.
- Rewinds do **not** roll back loot/XP/quests — cross-timeline persistence is a feature ("walk between timelines, keep what you find").
- Counter-Stop uses the **interrupt model** (announce → response window → resolve), not the true-counter model.
- Event-type partition (rewindable vs. persistent) is locked — see table above. `enemy_killed` has split behavior and needs explicit tests.

## Success Criteria

- A combat featuring 1 rewind, 1 echo cast, and 1 counter-stop completes deterministically and replays bit-identical from the event log.
- Chronomancer archetype produces recognizably distinct tactical behavior across eval fixtures.
- Frame time stays <16ms with `TemporalSystem` active in combat (60 FPS target, constitution principle 14).
- Event log remains append-only; genesis-replay reaches current state across any branch sequence.
- ≥80% test coverage on `src/core/temporal.py` and new combat event types.

## Sequence (rough — refined as decisions land)

1. Schema migration: `branch_id` on `game_events`. dbt staging models updated.
2. `TemporalCharge` resource on `Combatant`; `TemporalSystem` skeleton with DI wiring.
3. Rewind (single-turn) end-to-end + event types + tests.
4. Multi-turn rewind + branch tracking.
5. Echo Cast.
6. Counter-Stop.
7. `Chronomancer` archetype + eval fixtures.
8. Visual feedback pass (may defer to Phase 5 if scope creeps).

---

**Next action after this note is reviewed**: answer the five Open Questions, then start Step 1 (schema migration).
