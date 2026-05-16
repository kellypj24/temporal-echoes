# Phase 3 Step 3 — Single-turn Rewind, End-to-End

**Status**: implementation-ready (Opus-refined from Sonnet baseline)
**Prereqs**: Step 1 (branch_id schema, `is_rewindable()`) merged @ `6875a9c`. Step 2 (`TemporalCharge` on `Combatant`, `TemporalSystem` skeleton) assumed in place at hand-off — `temporal_charge`, `max_temporal_charge`, `spend_charge()`, `gain_charge()` already exist on `Combatant`.

---

## 1. Goal & Scope

Deliver the smallest end-to-end rewind that actually works: **player spends 1 Charge, time unwinds exactly 1 turn, combat resumes on a new branch**. Everything required to take that path from input to event-store-truth ships in this step.

In scope:
- `TemporalSystem.rewind(turns=1)` real implementation (replaces Step 2 stub).
- Event flow: `CHARGE_SPENT(1)` → `TEMPORAL_REWIND(from, to, branch_id)`, with a defined failure-rollback contract (Section 8a).
- Branch_id allocation + propagation on subsequent emitted events.
- Combat-local state rebuild from rewindable event stream.
- `CombatContext.rewind_to_turn()` integration point.
- Unit + integration + determinism tests; ≥80% coverage on new code.

Out of scope (later steps):
- Multi-turn rewind path (Step 4 — even though the API takes `turns`, only `turns=1` is exercised/validated here).
- Echo Cast (5), Counter-Stop (6), Chronomancer AI (7).
- Player-facing UI / animation.
- Cross-combat persistence of branches.
- `enemy_killed` cross-branch idempotency (no enemy_killed event type exists yet in Phase 3).

"End-to-end" means: a test can call `combat.rewind_to_turn(N)` from the public API, watch events land in the store, and assert combat resumes from the rebuilt state with a new `branch_id`.

---

## 2. `TemporalSystem.rewind()` API

```python
def rewind(
    self,
    combat: CombatContext,
    actor: Combatant,
    turns: int = 1,
) -> RewindResult: ...
```

`RewindResult` (new dataclass, `src/core/temporal.py`):
- `from_turn: int`
- `to_turn: int`
- `new_branch_id: int`
- `events_replayed: int`
- `charge_spent: int`

**Error cases** (raise `TemporalError` subclass of `TemporalEchoesError`):

| Condition | Exception |
|---|---|
| `actor.temporal_charge < turns` | `InsufficientChargeError` |
| `turns < 1` | `ValueError` |
| `turns > 1` (Step 3 scope guard) | `NotImplementedError("multi-turn rewind lands in Step 4")` |
| Target turn would be < 0 (i.e. `combat._total_turns - turns < 0`) | `RewindBoundaryError` |
| `combat.is_over` | `RewindUnavailableError` |
| `combat.phase == COMBAT_OVER` (redundant safety) | `RewindUnavailableError` |
| `combat.phase == EXECUTING_TURN` (mid-resolve) | `RewindUnavailableError` |
| Replay aborts mid-flight (see 8a) | `RewindReplayError` (after state restored) |

Allowed phases for rewind: `AWAITING_PLAYER_INPUT`, `ROUND_END`. Disallowed during damage resolution to keep replay deterministic. **Note**: enemy turns auto-execute via `execute_enemy_turn()` and never sit in an "awaiting" enemy-input phase — the player cannot interleave a rewind between enemy turns (covered in Section 7 edge cases).

---

## 3. Event Flow

The naive ordering (emit → mutate → replay) leaves the store and the in-memory `CombatContext` desynchronized on partial failure. The refined ordering moves all destructive mutation behind a single in-memory checkpoint and defers the persistent `TEMPORAL_REWIND` event until after replay succeeds.

**Refined order**:

1. **Validate** (charge, turn boundary, phase). Fail fast — no events, no mutation. ValidationError propagates to caller.
2. **Snapshot rollback state** in memory (Section 8a): `(actor.temporal_charge, combat._current_branch_id, combat._phase, combat._total_turns, combat._round_number, combat._turn_index, combat._turn_order, frozen copies of every `Combatant`'s rewindable fields, `combat._rng.getstate()`, `combat._damage_calc.rng.getstate()`, `{ai.enemy.id: ai.rng.getstate() for ai in _enemy_ais.values()}`)`. Pure Python objects; <1ms.
3. **Emit `CHARGE_SPENT`** at *current* (pre-rewind) `branch_id`, `turn_number = combat._total_turns`, payload `{actor_id, amount: 1, ability: "rewind"}`. Committed via the EventStore transaction. This lives in the pre-rewind branch and will *not* be in the replay set (it's at the from_turn, outside `[0..to_turn]`).
4. **Decrement charge** on actor (`actor.spend_charge(1)`).
5. **Compute** `new_branch_id = combat._current_branch_id + 1`.
6. **Bump branch** on combat: `combat._current_branch_id = new_branch_id`, `combat._event_builder.set_branch(new_branch_id)`.
7. **Replay** (Section 4) inside a `try` block. Replay is pure in-memory mutation; emits NO events. On any exception: restore the Step-2 snapshot (charge, branch_id, phase, turn counters, combatant state, all RNG states, builder branch) and re-raise as `RewindReplayError`. **Note**: the `CHARGE_SPENT` event from Step 3 stays in the store — it is an immutable historical fact (Principle 11). The store and in-memory state diverge by exactly that one event, which is the *correct* outcome: the player attempted to spend a charge, the spend was recorded, the attempt failed. On the next successful action, downstream replay derives charge from `(starting cap) − sum(CHARGE_SPENT.amount on active branch chain)`, so the failed-spend is naturally ignored because it lives on a branch that was never adopted. Document this explicitly in the `RewindReplayError` docstring.
8. **Emit `TEMPORAL_REWIND`** at the *new* branch (now safely live in memory), payload `{actor_id, from_turn, to_turn, branch_id: new_branch_id}`. Persistent — never undone.
9. **Return** `RewindResult`.

**Why CHARGE_SPENT before TEMPORAL_REWIND, not after**: it lets the charge spend be a record of the *attempt*, which survives even a botched replay. It also matches narrative tense — the player "spent the charge to try the rewind" before time actually warps. Reversing the order would let a replay crash silently consume nothing while the player thinks they paid.

**Branch_id increment rule**: monotonically increasing, scoped to a single `CombatContext` instance. Branch 0 is the original line. Each rewind increments by exactly 1, regardless of `turns`. Lives on `CombatContext`, read by `CombatEventBuilder` at emit time.

**Builder change** (`combat_events.py`): `CombatEventBuilder` gains a `branch_id: int = 0` field + a `set_branch(branch_id: int)` mutator. See Section 5 for the decision rationale. New builder methods (some land in Step 2):
- `charge_spent(turn_number, actor_id, amount, ability)`
- `temporal_rewind(turn_number, actor_id, from_turn, to_turn, branch_id)`

Each emit reads `self.branch_id` and stamps the `GameEvent`.

---

## 4. Replay Mechanics

### Query
Use existing `EventStore.get_events_by_timeline(timeline_id)`. Filter in Python by `aggregate_id == combat_id` and `branch_id <= current_branch_id` (in Step 3 only branch 0 exists at replay time — the new branch is empty until post-replay events fire). **No new EventStore method required for Step 3.** Step 4 (multi-turn / cross-branch) likely justifies `get_events_for_combat(combat_id, branch_chain)` — flagged and deferred.

### Filter
Partition via `is_rewindable(event.event_type)`:
- **Rewindable set** (`TURN_STARTED`, `ACTION_EXECUTED`, `SHIELD_BROKEN`, `BOOST_POINT_GAINED`, `CHARGE_SPENT`, `CHARGE_REGENERATED`, `ECHO_*`): truncate to those whose recorded `turn_number <= to_turn`. These are the replay set.
- **Persistent set** (`COMBAT_STARTED`, `COMBAT_ENDED`, `TEMPORAL_REWIND`, `COUNTER_STOP_TRIGGERED`, future loot/XP): left in the store, no state mutation needed.

### RNG strategy — LOCKED: reseed and replay (no snapshots)

**Decision**: reseed from `combat._seed` and replay forward through the rewindable event set. Locked for Step 3 *and* Step 4.

**Cost analysis** (per replay):
- `combat._rng` draws: 1 per damage_calc init (combat start), ~1 per flee. Realistic Step 4 worst case (3 turns of 1v1 combat with flees) = ~5 draws.
- `damage_calc.rng` draws: 2 per attack (uniform variance + randint for crit). Step 4 worst case = 3 turns × 2 attackers × 2 draws = 12 draws.
- `ai.rng` draws (one per enemy): 1 per `select_action()` call. Step 4 worst case = 3 turns × 1 enemy = 3 draws per AI.

Total worst-case replay RNG work: ~25 `Random.random()` calls. At Python's ~50ns per `Random.uniform`/`randint`, that's <2µs. The 16ms frame budget (Principle 14) has 8000× headroom. The marginal "snapshot per turn" cost — bytes copied, dict allocations, the conceptual overhead of a parallel snapshot system to keep in sync — is strictly worse than reseed-and-replay at this scale.

Snapshotting reintroduces the very thing Principle 1 ("Event Sourcing is Sacred") forbids: a parallel state representation. Reseed-and-replay derives RNG state from the event stream the same way it derives HP — that's the architectural invariant we want.

**Locked.** Revisit only if Phase 4+ introduces deep rewinds (10+ turns) or RNG hot-paths (procedural-gen rolls during combat).

### AI hidden-state audit — LOCKED: all archetypes are stateless

Grep + read confirms: `AggressiveAI`, `DefensiveAI`, `TacticalAI`, `BerserkerAI` (`src/core/ai.py:172–324`) each implement `_get_base_weights()` (pure constant) and `_calculate_situational_weights()` (pure function of `self.enemy.hp_percent` + `combat_state`). No instance attributes mutate across `select_action()` calls. The `EnemyAI` base class stores `self.enemy`, `self.rng`, and `self.base_weights` — only `self.rng` carries state, and that's covered by reseeding.

| Archetype | Carries cross-call state? | Rewind handling |
|---|---|---|
| `AggressiveAI` | No (besides RNG) | Reseed `rng` from snapshot of `combat._rng.randint` chain |
| `DefensiveAI` | No (besides RNG) | Same |
| `TacticalAI` | No (besides RNG) | Same |
| `BerserkerAI` | No (besides RNG) | Same |

**Implication**: replay does NOT re-instantiate AIs. We mutate `ai.rng.setstate(snapshot)` for each `_enemy_ais` entry as part of the rollback path (Section 8a), and during replay we reseed combatant RNG via `combat._rng = random.Random(seed)`, then re-derive per-AI seeds by replaying the same `randint(0, 2**31)` calls the constructor does. AI archetypes themselves require no special handling.

**Locked.** New Chronomancer archetype (Step 7) may carry state ("last-targeted ability"); audit again at that point and add explicit replay handling if so.

### Rebuild combat-local state

Re-derive from `COMBAT_STARTED` snapshot + rewindable replay:

1. Reset live `Player`/`Enemy` instances to their `COMBAT_STARTED` snapshot values (hp, max_hp, boost_points=0, shield_points=max, is_broken=False, break_turns_remaining=0, temporal_charge=starting cap).
2. Reset `combat._total_turns = 0`, `_round_number = 0`, `_turn_index = 0`, `_turn_order = []`, `_phase = ROUND_START`.
3. **Reseed RNG**: `combat._rng = random.Random(combat._seed)`, then re-derive subordinate seeds by walking the same `randint(0, 2**31)` calls the constructor performs (`_damage_calc` seed, then one per AI in `enemies` order). Bit-identical to original initialization.
4. Loop over replay set in chronological order; for each event, mutate state via a private `_apply_event(event)` dispatch. For Step 3 this needs only:
   - `TURN_STARTED` → set `_total_turns`, `_turn_index`, current combatant pointer.
   - `ACTION_EXECUTED(attack)` → recompute damage via reseeded `_damage_calc` (NOT trust `damage_dealt` from event — recompute, then assert equality as a determinism check), apply via `target.take_damage`.
   - `ACTION_EXECUTED(defend|flee)` → consume RNG only if original did (flee draws 1; defend draws 0), apply state change.
   - `SHIELD_BROKEN` → no extra state change (already handled by `take_damage` in `ACTION_EXECUTED` replay); used as an integrity assertion.
   - `BOOST_POINT_GAINED` → `player.gain_bp(amount_gained)`.
   - `CHARGE_SPENT` → `actor.spend_charge(amount)` (within replay window — irrelevant for Step 3 single-turn but defined for forward-compat).
   - `COMBATANT_DEFEATED` → assert HP == 0 (defensive; already implied by ACTION_EXECUTED).
5. After replay, position is at exactly `to_turn`. Set `_phase = AWAITING_PLAYER_INPUT` (player got the rewind, player acts next).

**Persistent events preserved**: explicitly do NOT re-emit them; they were never removed. Boundary enforced via `is_rewindable()`.

### Branch handling for new events
After replay + Section 3 step 8, `_current_branch_id == new_branch_id` and the builder is already stamping it. Replay itself emits NOTHING — replay is pure in-memory mutation. Principle 11 (immutable events): we are not deleting or rewriting prior events; we walk a new branch forward from the same logical turn position.

---

## 5. `CombatContext` Changes

New state:
- `self._current_branch_id: int = 0`
- `self._temporal: TemporalSystem` (injected via constructor — DI per Principle 2).

New public method:
```python
def rewind_to_turn(self, target_turn: int, actor: Combatant | None = None) -> RewindResult:
    actor = actor or self.player
    turns_back = self._total_turns - target_turn
    return self._temporal.rewind(self, actor, turns=turns_back)
```

Internal hooks:
- `_emit_event()` unchanged in shape; builder now stamps current branch_id.
- `_set_phase_for_current_combatant()` reused as-is post-replay.
- `start_round()`, `advance_turn()` unchanged.

**60 FPS path** (Principle 14): rewind work is amortized — runs once per player rewind action (player-initiated, not per frame). Worst-case Step 3 replay = 1 turn of events (handful of rows + <25 RNG draws). Target: rewind completes in <16ms for a 1-turn window on an in-memory SQLite store. Add a benchmark in `tests/benchmarks/bench_rewind.py`.

### Builder mutation decision — LOCKED: `set_branch()` mutator on the existing instance

`CombatEventBuilder` already gains a `branch_id` field; mutate via `set_branch(id)` on the single instance owned by `CombatContext`. **Rationale**: (1) the builder is a stateless event factory whose identity carries no semantic weight — only the *events* it produces are required to be immutable (Principle 11), and they are (frozen dataclass). (2) Replacing the instance forces callers (`_emit_event` and every method that reads `self._event_builder`) to re-bind the reference, multiplying touch points without behavioral gain. (3) `set_branch` is a 2-line method with a single invariant (monotonic increase, validated). Locked.

---

## 6. Concrete Edits

| File | Change |
|---|---|
| `src/core/temporal.py` | Replace Step 2 stub with `TemporalSystem.rewind()`, `RewindResult` dataclass, `_replay_events()`, `_apply_event()` dispatcher, `_snapshot_rollback_state()` + `_restore_rollback_state()` (Section 8a). |
| `src/core/exceptions.py` | Add `TemporalError(TemporalEchoesError)` base + `InsufficientChargeError`, `RewindBoundaryError`, `RewindUnavailableError`, `RewindReplayError`. |
| `src/core/combat.py` | Add `_temporal: TemporalSystem` constructor arg, `_current_branch_id` field, `rewind_to_turn()` public method, expose `_snapshot_for_rollback()` helper for temporal to call. Update constructor to pass `branch_id=0` to builder. |
| `src/core/combat_events.py` | Add `branch_id: int = 0` field + `set_branch(branch_id)` method. Thread `branch_id` into every emitted `GameEvent`. Add `charge_spent()`, `temporal_rewind()` methods (if not already in Step 2). |
| `src/entities/combatant.py` | (Step 2) confirm `temporal_charge`, `max_temporal_charge`, `spend_charge()`, `gain_charge()` exist — verified present at lines 65–203. No edits required for Step 3. |
| `tests/fixtures/combat_fixtures.py` | Add `TemporalSystem` instance to default `create_combat_context()` wiring. |
| `tests/unit/test_temporal.py` | New file. Unit tests for `TemporalSystem.rewind()` + error paths + rollback. |
| `tests/integration/test_rewind_scenarios.py` | New file. End-to-end combat → rewind → assert state + event log. |
| `tests/benchmarks/bench_rewind.py` | New file. Frame-time budget proof. |

Estimated diff: **~700–900 LOC added**, ~60 LOC modified. ~9 files touched.

---

## 7. Test Plan

### Unit (`tests/unit/test_temporal.py`)
- `test_rewind_with_zero_charge_raises_insufficient_charge` — and asserts no events emitted.
- `test_rewind_zero_turns_raises_value_error`
- `test_rewind_multi_turn_raises_not_implemented` (Step 3 scope guard)
- `test_rewind_before_turn_zero_raises_boundary_error`
- `test_rewind_to_turn_zero_succeeds` — `to_turn == 0` is valid (rewind to combat start); only `< 0` is the boundary.
- `test_rewind_when_combat_over_raises_unavailable`
- `test_rewind_during_executing_phase_raises_unavailable`
- `test_rewind_emits_charge_spent_then_temporal_rewind` — assert exact order in event store.
- `test_temporal_rewind_event_carries_new_branch_id`
- `test_charge_spent_event_carries_old_branch_id`
- `test_branch_id_increments_by_one_per_rewind`
- `test_rewind_decrements_actor_charge_by_one`
- `test_rewind_result_payload_shape` — all 5 RewindResult fields populated correctly.
- `test_rewind_replay_failure_restores_actor_charge` — inject `_apply_event` failure, assert charge restored, branch reverted, phase unchanged.
- `test_rewind_replay_failure_leaves_charge_spent_in_store` — same inject, assert CHARGE_SPENT remains as immutable historical record.
- `test_rewind_replay_failure_restores_rng_state` — inject failure mid-replay, assert next damage roll matches pre-rewind expected value (uses `Random.getstate()` equality).

### Integration (`tests/integration/test_rewind_scenarios.py`)
- `test_three_turns_then_rewind_one_restores_turn_two_state` — combat → attack/defend/attack → rewind(1) → assert player HP, enemy HP, BP, shield, broken-state match end-of-turn-2 snapshot.
- `test_rewind_preserves_persistent_events` — assert `COMBAT_STARTED` and the new `TEMPORAL_REWIND` are both queryable post-rewind; no events deleted.
- `test_post_rewind_events_carry_new_branch_id` — rewind, then play another turn, assert new turn's `ACTION_EXECUTED` has `branch_id == 1`.
- `test_event_log_append_only_after_rewind` — count events before + emitted-during-rewind (2: CHARGE_SPENT, TEMPORAL_REWIND) = count after; nothing removed.
- `test_rewind_to_turn_zero_restores_combat_start_state` — play 3 turns, rewind to turn 0, assert state == post-`COMBAT_STARTED` snapshot (all HP, BP, shields at start values).
- `test_rewind_at_round_boundary_resets_round_counter` — play through end of round 1, rewind to a turn mid-round 1, assert `_round_number == 1` and `_turn_index` correct. (See known semantics below.)
- `test_rewind_during_enemy_turn_window_raises_unavailable` — drive combat into a state where an enemy is the current combatant and call `rewind_to_turn`; since the phase will be `EXECUTING_TURN` during the enemy's resolve, expect `RewindUnavailableError`. Player can only rewind on their own turn or at `ROUND_END`.
- `test_rewind_mid_round_preserves_turn_index_invariant` — in a 3-combatant round (player + 2 enemies), play through enemy A, rewind to player's turn, assert `_turn_index` points to player (0), not enemy A (1).

### Determinism (`tests/integration/test_rewind_scenarios.py`)
- `test_rewind_then_same_action_produces_same_state` — seed S → play 3 turns A,B,C → rewind 1 → replay action C → assert post-state identical to pre-rewind post-C (bit-identical HP, RNG state, shield).
- `test_rewind_then_different_action_diverges_cleanly` — same setup → rewind → play action D instead → assert state differs in expected places, no leakage from prior branch.
- `test_event_log_hash_stable_across_runs` — run identical seeded combat twice (including a rewind), `hash(tuple((e.event_type, e.branch_id, e.event_data) for e in events))` matches across runs. Proves the locked RNG strategy keeps the event log bit-stable.
- `test_replay_damage_matches_recorded_damage` — after rewind, internal `_apply_event` recomputed-damage equals the `damage_dealt` field in every replayed `ACTION_EXECUTED`. Assertion lives inside `_apply_event` (raise on mismatch); test triggers it by running a multi-attack scenario through rewind.

### Known semantics surfaced by edge-case tests
- **`_round_number` on rewind across a round boundary**: replay walks `TURN_STARTED` events from turn 0. `_round_number` is incremented by `start_round()`, *not* by any event. Replay must explicitly call `start_round()` (suppressing its event emissions — see implementation note in `_replay_events`) or, simpler, re-derive `_round_number` from the count of `TURN_STARTED` events whose `turn_number % len(turn_order) == 1` in the replay set. **Locked approach**: derive from event count, do not re-invoke `start_round()`. Add unit test `test_replay_derives_round_number_from_turn_count`.
- **Player-mid-flight rewind**: disallowed via `phase != EXECUTING_TURN` validation. Player can only trigger rewind between their own actions or at round end.

### Property/coverage
- Defer `pytest-hypothesis` style property test (random seed + random valid action sequence + rewind 1 always converges) to Step 4 once multi-turn lands. Determinism-replay test above is the hard gate for Step 3.

Coverage gate: ≥80% on `src/core/temporal.py` and new builder methods (Principle 5).

---

## 8. Open Questions

Closed in this refinement: RNG strategy (reseeded), AI hidden state (none), builder mutation (in-place `set_branch`), failure rollback (Section 8a), `CHARGE_SPENT` ordering and the immutable-record semantics, `_round_number` re-derivation strategy.

**Truly open** (need human input before/during implementation):
1. **Should `RewindReplayError` surface to UI as "rewind failed, charge consumed" or as a developer-only crash?** The technical contract (Section 8a) preserves player charge in memory but the `CHARGE_SPENT` event lives in the log forever. For Step 3 with no UI, either path is fine; the Phase 4 UI/animation work needs to pick a story. **Recommend**: developer-only crash for Step 3 (raise to test layer), document the choice deferred to Step 8 (visual feedback).

---

## 8a. Failure Rollback Contract

When `TemporalSystem.rewind()` fails *after* `CHARGE_SPENT` emits but *before* `TEMPORAL_REWIND` emits, the system MUST restore the in-memory `CombatContext` to its pre-rewind state and raise `RewindReplayError`. The store retains `CHARGE_SPENT` as an immutable record of the failed attempt (Principle 11).

**Snapshot fields** (taken before any mutation, Section 3 step 2):
- `actor.temporal_charge`
- `combat._current_branch_id`, `combat._phase`, `combat._total_turns`, `combat._round_number`, `combat._turn_index`
- Shallow copy of `combat._turn_order` (the Combatant references are restored too — see next)
- Per-combatant snapshot: `hp`, `boost_points` (if Player), `shield_points` (if Enemy), `is_broken`, `break_turns_remaining`, `temporal_charge`
- `combat._rng.getstate()`, `combat._damage_calc.rng.getstate()`
- `{enemy_id: ai.rng.getstate() for enemy_id, ai in combat._enemy_ais.items()}`
- `combat._event_builder.branch_id`

**Restore order** (reverse of snapshot, all in memory):
1. Restore combatant fields (HP, BP, shields, break, charge).
2. Restore RNG states (combat, damage_calc, each AI).
3. Restore turn counters + phase + turn_order + turn_index.
4. Restore branch_id on combat and builder.

**Invariants**:
- The event store is never rolled back. Once `CHARGE_SPENT` is in the store, it stays.
- The in-memory state after a failed rewind is bit-identical to the pre-rewind state *except* for `actor.temporal_charge`, which is also restored (the spend lives only as an event, not as a stat decrement that survived).
- Re-attempting the rewind after a `RewindReplayError` will emit a *second* `CHARGE_SPENT` event. This is intentional: the log truthfully records both attempts.
- Charge resolution on the active branch chain (Step 4 multi-rewind concern) sums `CHARGE_SPENT.amount` *minus* `CHARGE_REGENERATED.amount` only along the live branch lineage; failed-rewind events on abandoned branches don't contribute.

**Test coverage**: `test_rewind_replay_failure_*` trio in Section 7 exercises this contract.

---

## 9. Estimated Edits

- **Files touched**: 9 (4 modified, 5 new — incl. 1 benchmark).
- **LOC added**: ~700–900.
- **Test count target**: 16 unit + 11 integration = 27 new tests minimum.
- **Build time**: ~1 focused implementation session (5–7 hrs incl. tests + coverage + benchmark).
