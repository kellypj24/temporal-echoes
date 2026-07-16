# Phase 3 Step 6 — Counter-Stop

**Status**: implementation-ready
**Prereqs**: Steps 1–5 merged to `main` (Step 5 Echo Cast via PR #21 @ `f50adca`). Both counterable abilities (rewind, echo cast) exist end-to-end; `COUNTER_STOP_TRIGGERED` event type exists and is already **excluded** from the rewindable set (`src/core/events.py` — persistent per the DESIGN partition table).

---

## 1. Goal & Scope

Deliver the **interrupt model** (DESIGN, decided 2026-05-13): temporal abilities are *announced* before they take effect; the opposing side gets a response window; a responder holding 3 Charges may Counter-Stop, making the ability **fizzle with the caster's Charge cost still spent**. The announce → window → resolve machinery ships fully tested; the *deciders* come later (Chronomancer AI weights in Step 7, interactive player response UI in Step 8) via the policy seam this step creates.

In scope:
- `TemporalAnnouncement` + response-window machinery inside `TemporalSystem`, wired into both `rewind()` and `echo_cast()` between charge-spend and execution.
- `CounterStopPolicy` protocol + `NeverCounterPolicy` default, injected via DI. One policy instance decides for **both sides** (decided 2026-07-15) — tests script it; Step 7 replaces it for Chronomancers.
- `CounterStopResult` frozen dataclass; `rewind()` / `echo_cast()` / `rewind_to_turn()` return unions (`XResult | CounterStopResult`).
- Event flow for a countered cast: caster `CHARGE_SPENT` → responder `CHARGE_SPENT(3, "counter_stop")` → `COUNTER_STOP_TRIGGERED` (persistent).
- Rewind-replay compatibility (needs **zero new `_apply_event` handlers** — see §5).
- Unit + integration + determinism tests; ≥80% coverage.

Out of scope:
- Chronomancer archetype and its counter-decision weights (Step 7 — the policy hook is its seam).
- Interactive player response window / UI (Step 8; nothing can trigger it until Step 7 anyway).
- Announce-phase analytics event (`TEMPORAL_ANNOUNCED`) — Open Question 1.
- Cast animations / "read the tell and bait the counter" visuals (Step 8).

---

## 2. Locked Semantics (decided 2026-07-15 with PJ)

1. **Counters are final.** Only `rewind` and `echo_cast` are counterable; a Counter-Stop opens no response window of its own. No nested announcements, no regress. Structural consequence: the policy is consulted **exactly once** per cast.
2. **Countering is a reactive free action.** Cost is exactly `COUNTER_STOP_COST = 3` Charges — the full pool — and nothing else. No turn skip, no new state for replay to reconstruct.
3. **Union result, not exception.** Being countered is a legitimate game outcome. `rewind() -> RewindResult | CounterStopResult`, `echo_cast() -> EchoCastResult | CounterStopResult`. Exceptions stay reserved for *invalid* casts.
4. **Policy hook only.** `CounterStopPolicy` decides responses for both sides. Default `NeverCounterPolicy` — every existing flow is behaviorally unchanged out of the box (all 600 current tests must pass untouched).

Additional semantics locked in this plan (flag in PR review if any feels wrong):

5. **The caster commits before the window opens** (DESIGN: "the acting side commits to the cast"). Order: validate → caster `CHARGE_SPENT` + decrement → **response window** → execute or fizzle. A countered rewind never snapshots, never bumps the branch, never replays; a countered echo cast never builds or registers an `Echo`.
6. **Validation failures never announce.** An invalid cast (insufficient charge, bad turns, no history, …) raises before any event or any policy consultation — you cannot bait a counter with a cast you couldn't afford.
7. **Eligible responders** = living combatants on the *opposing* side with `temporal_charge >= 3`, in deterministic order (enemy side: `living_enemies` list order; player side: just the player). If nobody is eligible, the **window is skipped entirely — the policy is not called** (zero overhead on the common path, and policies never see empty choices).
8. **Policy contract**: `decide(combat, announcement, eligible) -> Combatant | None`. Returning `None` = no counter. Returning a combatant not in `eligible` raises `ValueError` — that's a programming error in the policy, not a game state.
9. **No RNG in the counter path.** The window, the default policy, and counter resolution draw nothing — the locked reseed-and-replay rewind strategy is untouched (Step 7's Chronomancer policy may use its AI's own RNG; that's audited then, per STEP-3-PLAN's standing note).
10. **Counter events land at the current turn, current branch.** `COUNTER_STOP_TRIGGERED` payload: `{actor_id: responder, caster_id, target_ability, turn_number}`. It is persistent — a historical fact that survives any later rewind (same standing as `TEMPORAL_REWIND`).
11. **The public `counter_stop()` stub is removed**, not implemented. In the interrupt model, Counter-Stop is never invoked directly — it only exists as a response inside the window. The machinery lives in a private `_offer_counter_window()`; there is deliberately no public "cast counter-stop" API.

---

## 3. New Types (`src/core/temporal.py`)

```python
COUNTER_STOP_COST = 3

@dataclass(frozen=True)
class TemporalAnnouncement:
    ability: str          # "rewind" | "echo_cast"
    caster_id: str
    magnitude: int        # turns rewound / echo window N
    turn_number: int

@dataclass(frozen=True)
class CounterStopResult:
    countered_ability: str
    caster_id: str
    responder_id: str
    caster_charge_lost: int      # what the fizzled cast cost (turns / 2)
    responder_charge_spent: int  # always COUNTER_STOP_COST
    turn_number: int

class CounterStopPolicy(Protocol):
    def decide(
        self,
        combat: CombatContext,
        announcement: TemporalAnnouncement,
        eligible: Sequence[Combatant],
    ) -> Combatant | None: ...

class NeverCounterPolicy:
    """Default policy: nobody ever counters. Step 6 ships this; Step 7 swaps in Chronomancer weights."""
    def decide(self, combat, announcement, eligible) -> Combatant | None:
        return None
```

DI wiring: `TemporalSystem.__init__` gains `counter_policy: CounterStopPolicy | None = None` (defaulting to `NeverCounterPolicy()`); `CombatContext.__init__` gains the same defaulted parameter and threads it through. Zero churn at existing call sites (Principle 2 — constructor injection, defaulted).

---

## 4. The Response Window — `_offer_counter_window()`

Private method on `TemporalSystem`:

```python
def _offer_counter_window(
    self,
    combat: CombatContext,
    caster: Combatant,
    ability: str,
    magnitude: int,
    caster_charge_lost: int,
) -> CounterStopResult | None:
```

1. Build the eligible list (locked semantic 7). Empty → return `None` (policy never called).
2. Build `TemporalAnnouncement`; call `self._counter_policy.decide(combat, announcement, eligible)`.
3. `None` → return `None` (cast proceeds).
4. Validate the responder is in `eligible`, else `ValueError` (locked semantic 8).
5. Emit `CHARGE_SPENT` — `{actor_id: responder.id, amount: 3, ability: "counter_stop"}` — then `responder.spend_charge(3)` (matches the emit-then-decrement convention used everywhere since Step 2).
6. Emit `COUNTER_STOP_TRIGGERED` (persistent) — payload per locked semantic 10.
7. Log via `combat._logger.log_counter_stop(responder, caster, ability)`.
8. Return `CounterStopResult`.

**Integration into `rewind()`** (current order: validate → snapshot → CHARGE_SPENT → spend → branch → replay → TEMPORAL_REWIND):
- Move the window in **after** the spend, **before** the snapshot: validate → CHARGE_SPENT → spend → **window** → (countered? return `CounterStopResult`) → snapshot → branch bump → replay → TEMPORAL_REWIND. The snapshot exists solely to protect the replay; a countered cast has nothing to roll back — charges are meant to stay spent.

**Integration into `echo_cast()`** (current order: validate → capture window → CHARGE_SPENT → spend → build Echo → ECHO_SPAWNED):
- validate → capture source window → CHARGE_SPENT → spend → **window** → (countered? return `CounterStopResult` — no Echo built, no ECHO_SPAWNED, nothing registered) → build → register → ECHO_SPAWNED.

**`CombatContext` call sites**:
- `rewind_to_turn()` return type widens to `RewindResult | CounterStopResult` (pure pass-through).
- `submit_player_action()`'s `"echo_cast"` branch pattern-matches the union: `EchoCastResult` → `log_echo_spawned`; `CounterStopResult` → `log_counter_stop` fizzle message. Either way the cast **consumed the turn** (you committed — locked semantic 5 extends Step 5's turn-cost decision to the fizzle case).

**60 FPS** (Principle 14): the window is a list build + one policy call + at most 3 event appends. No store reads, no RNG, no replay. No new benchmark — the counter path is strictly cheaper than the already-benched rewind (0.143ms median) and echo (0.095ms) flows it gates; `bench_rewind`/`bench_echo` cover the uncountered hot paths.

---

## 5. Rewind-Replay Compatibility — zero new handlers

A countered cast leaves exactly three events, and replay already handles every one:

| Event | Rewindable? | Replay behavior |
|---|---|---|
| `CHARGE_SPENT(caster, ability="rewind"/"echo_cast")` | yes | existing handler applies `spend_charge` |
| `CHARGE_SPENT(responder, 3, "counter_stop")` | yes | same handler |
| `COUNTER_STOP_TRIGGERED` | **no — persistent** | skipped by `is_rewindable()`, no state to rebuild (charge state is fully carried by the two CHARGE_SPENTs) |

So `_apply_event` needs **no changes**, the §8a rollback snapshot needs **no new fields** (the policy is stateless config, not combat state), and charge totals reconcile on any branch: a rewind that lands *before* a countered cast excludes both CHARGE_SPENTs from the replay window → both sides effectively refunded; the `COUNTER_STOP_TRIGGERED` row remains in the log as history, mutating nothing. This no-new-handlers property is a **test target**, not just a convenience (see §7 integration tests).

---

## 6. Concrete Edits

| File | Change |
|---|---|
| `src/core/temporal.py` | `COUNTER_STOP_COST`, `TemporalAnnouncement`, `CounterStopResult`, `CounterStopPolicy` protocol, `NeverCounterPolicy`, `_offer_counter_window()`; window insertion in `rewind()` + `echo_cast()`; return types widened; **remove** the `counter_stop()` stub; constructor gains `counter_policy` param. |
| `src/core/combat.py` | Constructor gains defaulted `counter_policy` param, threaded to `TemporalSystem`; `rewind_to_turn()` return type widened; `submit_player_action` echo branch pattern-matches the union. |
| `src/core/combat_events.py` | `counter_stop_triggered(turn_number, actor_id, caster_id, target_ability)` builder method (follow the `charge_spent` template). |
| `src/core/combat_logger.py` | `log_counter_stop(responder, caster, ability)`. |
| `tests/unit/test_counter_stop.py` | NEW — unit tests (§7). |
| `tests/integration/test_counter_stop_scenarios.py` | NEW — end-to-end + rewind-interop + determinism (§7). |

No new exception types (`ValueError` covers the one programming-error path). No `events.py` change (`COUNTER_STOP_TRIGGERED` + its persistent classification shipped in Step 1). No new benchmark (§4 rationale).

Estimated diff: **~400–550 LOC added**, ~60 LOC modified, 6 files touched.

---

## 7. Test Plan

Test policies (module-level in the test files): `ScriptedPolicy(responses: list[Combatant | None])` popping per call and recording every `(announcement, eligible)` it saw; `AlwaysFirstEligiblePolicy`.

### Unit (`tests/unit/test_counter_stop.py`)
Default behavior (regression guard):
- `test_default_policy_rewind_proceeds_unchanged` / `test_default_policy_echo_proceeds_unchanged`
- `test_no_eligible_responder_skips_policy_entirely` (enemy at 2 charge; policy call count == 0)

Countered rewind:
- `test_countered_rewind_returns_counter_stop_result` (full payload shape)
- `test_countered_rewind_leaves_caster_charge_spent`
- `test_countered_rewind_does_not_bump_branch_or_emit_temporal_rewind`
- `test_countered_rewind_leaves_combat_state_untouched` (HP/turns/phase/RNG `getstate()` all unchanged except the two charge pools)
- `test_countered_rewind_event_sequence` (caster CHARGE_SPENT → responder CHARGE_SPENT(3,"counter_stop") → COUNTER_STOP_TRIGGERED; nothing else)

Countered echo:
- `test_countered_echo_returns_counter_stop_result`
- `test_countered_echo_spawns_nothing` (no ECHO_SPAWNED, `_active_echoes` empty)
- `test_countered_echo_still_consumed_the_turn` (via `submit_player_action`; phase/`_total_turns` advanced)

Window mechanics:
- `test_policy_receives_announcement_and_eligible_list` (fields + deterministic eligible order with 2 eligible enemies)
- `test_policy_consulted_exactly_once_per_cast` (locked semantic 1, structurally)
- `test_responder_spends_exactly_three_charges`
- `test_policy_returning_ineligible_combatant_raises_value_error` (dead / under-charged / wrong-side each)
- `test_validation_failure_never_announces` (insufficient-charge rewind: policy call count == 0, zero events)
- `test_counter_path_draws_no_rng` (`getstate()` equality across a countered cast)
- `test_counter_events_carry_current_branch`
- `test_counter_stop_triggered_is_not_rewindable` (guards the events.py classification)
- `test_player_can_counter_enemy_echo_cast` (symmetric: manually drive enemy `echo_cast`, policy answers with the player)

### Integration (`tests/integration/test_counter_stop_scenarios.py`)
- `test_full_combat_with_countered_rewind` — seeded combat, both sides at 3 charge, player rewinds, enemy counters; combat continues on branch 0 with intact turn structure; exact event log asserted.
- `test_countered_echo_then_successful_recast` — counter drains the enemy to 0; player re-accumulates 2 charges and the re-cast goes through (window skipped: responder no longer eligible).
- `test_rewind_before_countered_cast_refunds_both_sides` — the §5 no-new-handlers property: rewind to a turn before the countered cast; both charge pools reflect exclusion; COUNTER_STOP_TRIGGERED still queryable (persistent).
- `test_rewind_after_countered_cast_replays_charge_spends` — rewind to a turn *after* it; both CHARGE_SPENTs replay; charge totals match live values bit-exactly.
- `test_chess_clock_scenario` — DESIGN's success-criterion combat: 1 rewind + 1 echo cast + 1 counter-stop in one seeded fight, completes deterministically.

### Determinism
- `test_event_log_hash_stable_with_counter` — the §5 scenario run twice, event-log hash identical.

Coverage gate: ≥80% on touched files (Principle 5). Full gauntlet (`just lint`, `just test`) before push; `just bench` once to confirm no regression.

~20 unit + 5 integration + 1 determinism = **~26 new tests** (600 → ~626).

---

## 8. Open Questions

Closed in this plan: counter-counter (no), counter turn-cost (none), API shape (union result), responder scope (policy only), commit-before-window ordering, skip-empty-window, single-policy-both-sides, no announce event, stub removal.

**Truly open** (not blocking):
1. **`TEMPORAL_ANNOUNCED` analytics event** — the synchronous window makes it mechanically redundant (countered/uncountered outcomes are fully event-described), but dbt funnel analysis ("how often is a rewind announced vs. countered?") might want it. Defer until Phase 3's dbt modeling lands; adding it later is append-only.
2. **Should a fizzled cast have a distinct player-facing tell** (vs. the counter's own animation)? Step 8.
3. **Chronomancer counter thresholds** (counter when player HP low? hoard vs. spend?) — Step 7, expressed as a `CounterStopPolicy`.

---

## 9. Estimates

- **Files touched**: 6 (4 modified, 2 new).
- **LOC added**: ~400–550.
- **Test count target**: ~26 new (600 → ~626).
- **Build time**: 1 focused session (3–5 hrs) — smaller than Step 5; the machinery is narrow and replay needs no changes.
- **Branch**: `phase/3-step-6-counter-stop` off `main`.
