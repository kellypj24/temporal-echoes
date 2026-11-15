# Phase 3 Step 5 — Echo Cast

**Status**: implementation-ready
**Prereqs**: Steps 1–4 merged to `main` (Steps 1–3 via PR #18, Step 4 via PR #20 @ `3915144`). Multi-turn rewind works end-to-end; `TURN_STARTED` is emitted at every turn boundary; `ECHO_SPAWNED` / `ECHO_ACTED` event types and their `is_rewindable()` membership already exist (`src/core/events.py:142–161`).

---

## 1. Goal & Scope

Deliver Echo Cast end-to-end: **the player spends 2 Charges as their turn action; a past-self echo replays their last N actions at 50% damage over their next N turns**. Symmetric — the mechanism works for enemy-owned echoes too (Chronomancer AI that *decides* to cast lands in Step 7; tests drive enemy casts manually).

In scope:
- `TemporalSystem.echo_cast()` real implementation (replaces the Step 2 stub).
- `"echo_cast"` as a fourth `action_type` in `CombatContext.submit_player_action()` — casting **consumes the turn** (decided 2026-07-15).
- Echo lifecycle: spawn → act once per owner turn → expire after N acts.
- Event flow: `CHARGE_SPENT(2, "echo_cast")` → `ECHO_SPAWNED`; one `ECHO_ACTED` per echo act (plus `SHIELD_BROKEN` / `COMBATANT_DEFEATED` when echo damage triggers them).
- Rewind interop: `_apply_event` handlers for `ECHO_SPAWNED` / `ECHO_ACTED`; rollback snapshot (§8a of STEP-3-PLAN) extended with echo + action-history state.
- Unit + integration + determinism tests; ≥80% coverage on new code.

Out of scope (later steps):
- Counter-Stop (Step 6) — echo cast resolves immediately; the announce → response-window interrupt model is Step 6's whole job. Do NOT build announce infrastructure here.
- Chronomancer AI weights (Step 7).
- UI/animation (Step 8): ghost sprite, alpha ghosting.
- `ECHO_STONE_USED` — pre-Phase-3 event type, unused, untouched.

"End-to-end" means: a test submits `CombatAction(action_type="echo_cast", echo_turns=2)` through the public API, watches `CHARGE_SPENT` + `ECHO_SPAWNED` land in the store, plays 2 more player turns, and asserts the echo dealt floor(recorded × 0.5) damage each turn with `ECHO_ACTED` events on the right branch.

---

## 2. Locked Semantics (decided 2026-07-15 with PJ)

1. **Casting consumes the player's action for the turn.** It rides `submit_player_action()`'s existing rails (phase flip, `_total_turns` increment, `TURN_STARTED` already emitted at the boundary). No separate entry point — rewind keeps that privilege because it erases the turn structure it would live in; Echo Cast has no such excuse.
2. **Echo damage = `floor(recorded damage_dealt × 0.5)`, minimum 1.** Reuses the `damage_dealt` recorded in the source `ACTION_EXECUTED` event. **Zero new RNG draws** — this is what keeps the locked reseed-and-replay rewind strategy untouched and makes echo replay trivially deterministic. The min-1 floor is a tunable (Open Question 1) but ships as stated.
3. **Dead original target → retarget to `combat.living_enemies[0]`** (list order — deterministic; `living_enemies` preserves `enemies` order). Retargeting resolves **at emit time**: `ECHO_ACTED.target_id` records the *actual* target, so rewind replay applies recorded damage to the recorded target with no retarget logic of its own. Enemy-owned echoes always target the player. No living target → fizzle.
4. **N is player-chosen, 1–3** (`echo_turns` on `CombatAction`, default 1). Cap 3 mirrors the rewind/charge cap; bounded by available owner action history. Cost is a **flat 2 Charges regardless of N** (per DESIGN).

Additional semantics locked in this plan (flag in PR if any feels wrong):

5. **The echo does not act on the cast turn.** It acts on the owner's next N turns ("acts alongside them for the *next* N turns" — DESIGN).
6. **Source window** = the owner's last N executed actions (attack/defend/flee), most recent last, replayed in chronological order. The cast turn itself emits no `ACTION_EXECUTED` (see §3), so casts never pollute the source window.
7. **Non-attack source actions**: `defend` replays as a flavor no-op (`ECHO_ACTED` with `action_type="defend"`); `flee` replays as a fizzle (`action_type="fizzle"`) — echoes can't leave the timeline. Both consume the echo's act for that turn. Every act emits exactly one `ECHO_ACTED`, keeping event counts deterministic.
8. **Max 1 active echo per side** (DESIGN M1 constraint). Side = player vs. enemies collectively. A second cast on a side with a live echo raises `EchoAlreadyActiveError`.
9. **Echo of a dead owner is inert.** Echoes act only on their owner's turn; dead combatants have no turns. An inert echo counts as expired for the side-cap check. No removal event — derivable, deterministic.
10. **Stunned (broken) owner's echo still acts.** The echo is a temporal entity independent of its owner's present state. `execute_enemy_turn()`'s broken-skip returns early *before* the action, but the echo hook runs regardless (see §5).
11. **Echoes are intangible**: no HP, not targetable, not in `_turn_order`, take no damage. They deal damage only.
12. **`echo_id` is deterministic**: `f"echo_{owner_id}_t{cast_turn}"`. No UUIDs — the event-log-hash determinism test must stay bit-stable across runs.
13. **No BP interaction**: echo attacks don't grant or spend Boost Points (the recorded damage already includes any BP the original action spent).

---

## 3. `TemporalSystem.echo_cast()` API & Event Flow

```python
ECHO_CAST_COST = 2       # flat, regardless of turns
ECHO_DAMAGE_SCALE = 0.5
MAX_ECHO_TURNS = 3

def echo_cast(
    self,
    combat: CombatContext,
    actor: Combatant,
    turns: int = 1,
) -> EchoCastResult: ...
```

New frozen dataclasses (`src/core/temporal.py`):

- `EchoSourceAction`: `source_turn: int`, `action_type: str`, `target_id: str | None`, `damage_dealt: int | None`
- `Echo` (NOT frozen — `next_index` mutates): `echo_id: str`, `owner_id: str`, `source_actions: tuple[EchoSourceAction, ...]`, `next_index: int = 0`, plus `is_expired` property (`next_index >= len(source_actions)`)
- `EchoCastResult` (frozen): `echo_id`, `owner_id`, `duration`, `charge_spent`, `source_turns: tuple[int, ...]`

**Error cases** (all `TemporalError` subclasses except `ValueError`):

| Condition | Exception |
|---|---|
| `turns < 1` or `turns > MAX_ECHO_TURNS` | `ValueError` |
| `actor.temporal_charge < ECHO_CAST_COST` | `InsufficientChargeError` |
| owner has fewer than `turns` recorded actions | `EchoHistoryError` (new) |
| actor's side already has a live (non-inert) echo | `EchoAlreadyActiveError` (new) |
| `combat.is_over` | `EchoUnavailableError` (new) |

No phase validation inside `echo_cast()` — the player path is phase-gated by `submit_player_action()` (which has already flipped to `EXECUTING_TURN` by dispatch time, same as `_execute_attack`), and enemy casts run inside `EXECUTING_TURN` too. Validate fail-fast: **no events, no mutation** on any error path.

**Event flow on successful cast** (all at the current `turn_number = combat._total_turns`, current branch):

1. Validate (above).
2. Capture source window from `combat._action_history[actor.id]` (last `turns` entries — see §5).
3. Emit `CHARGE_SPENT` — payload `{actor_id, amount: 2, ability: "echo_cast"}`.
4. `actor.spend_charge(2)`.
5. Build `Echo` with deterministic `echo_id`; register in `combat._active_echoes[side]`.
6. Emit `ECHO_SPAWNED` — payload `{echo_id, owner_id, duration, damage_scale: 0.5, source_actions: [{source_turn, action_type, target_id, damage_dealt}, ...]}`. **Source actions are embedded in the payload** so rewind replay reconstructs the echo from this one event, with no branch-lineage queries against prior `ACTION_EXECUTED` rows (that query problem — abandoned branches sharing turn numbers — is exactly what Step 4 deferred; embedding sidesteps it entirely).
7. Return `EchoCastResult`.

**No `ACTION_EXECUTED` is emitted for the cast.** The turn's record is `TURN_STARTED` → `CHARGE_SPENT` → `ECHO_SPAWNED`; an `ACTION_EXECUTED(echo_cast)` would be redundant with `ECHO_SPAWNED` and would pollute the action history that future casts draw from. Replay reconstructs the turn from the three events it does have.

**Failure mid-cast**: steps 1–2 are read-only; the only gap is between `CHARGE_SPENT` (3–4) and `ECHO_SPAWNED` (6), where step 5 is pure in-memory dict insertion that cannot realistically fail. No rollback contract needed — unlike rewind there is no replay between spend and completion. If `append_event` itself raises at step 6, the `CHARGE_SPENT` stays (Principle 11, same "recorded attempt" semantics as rewind).

---

## 4. Echo Acting — `execute_echo_turn()`

`TemporalSystem.execute_echo_turn(combat, owner) -> list[str]` — called by `CombatContext` after the owner's action resolves (§5). Logic:

1. Look up the owner's side echo; return `[]` if none, `owner_id` mismatch, echo expired, or `combat.is_over` (e.g. owner's flee succeeded or owner's attack won the fight — echo never acts after combat ends).
2. Pop `source_actions[next_index]`; `next_index += 1`.
3. Dispatch:
   - **attack**: resolve target — original `target_id` if that combatant `is_alive`, else `living_enemies[0]` for a player-owned echo / `combat.player` for enemy-owned; if no living target, fall through to fizzle. Damage = `max(1, floor(damage_dealt * ECHO_DAMAGE_SCALE))`. Apply via `target.take_damage(damage, DamageType.PHYSICAL)` — the same path as real attacks, so shield/break mechanics just work. Emit `ECHO_ACTED` `{echo_id, owner_id, action_type: "attack", target_id: <resolved>, damage_dealt: <scaled>, source_turn}`. If `entity_result.shield_broken` → emit `SHIELD_BROKEN` (already rewindable; replay's existing integrity assertion covers it). If target dies → emit `COMBATANT_DEFEATED` (persistent-side handling identical to `_execute_attack`).
   - **defend**: emit `ECHO_ACTED` with `action_type: "defend"`, no state change.
   - **flee** (or unresolvable attack): emit `ECHO_ACTED` with `action_type: "fizzle"`.
4. If now expired, delete from `_active_echoes` immediately (replay does the same — deterministic).
5. Return log messages.

`turn_number` on all echo events = `combat._total_turns` (the owner's just-executed turn). Store insertion order gives replay the right intra-turn ordering (owner's events first, echo's after).

**60 FPS** (Principle 14): an echo act is a dict lookup + one `take_damage` + 1–3 event appends. No RNG, no replay, no store reads. Add `bench_echo.py` proving cast + full 3-act lifetime completes in <16ms on an in-memory store.

---

## 5. `CombatContext` Changes

New state:
- `self._action_history: dict[str, deque[EchoSourceAction]]` — per-combatant, `deque(maxlen=MAX_ECHO_TURNS)`. Appended at the end of `_execute_attack` / `_execute_defend` / `_execute_flee` for whichever combatant acted. This is a **read model rebuilt from events** (rewind replay re-appends it in `_apply_event(ACTION_EXECUTED)`), not parallel state — same standing as HP. Echo acts do NOT append (echo actions aren't owner actions).
- `self._active_echoes: dict[str, Echo]` — keyed by side (`"player"` / `"enemy"`), max 1 each. Helper `_side_of(combatant) -> str`.

Changed flow:
- `submit_player_action()`: add `"echo_cast"` to the dispatch → `self._temporal.echo_cast(self, self.player, turns=action.echo_turns)`; then (for ALL action types including echo_cast — locked: the echo does not act on cast turn, which step 1's `is_expired`/registration ordering handles naturally since a fresh echo's first act happens on the *next* turn… enforce explicitly: skip the echo hook on the cast turn) call `msgs.extend(self._temporal.execute_echo_turn(self, self.player))` after the action resolves. Simplest correct form: run the echo hook for attack/defend/flee turns only; the cast turn returns before the hook.
- `execute_enemy_turn()`: append `execute_echo_turn(self, enemy)` after the action — **including the broken-skip early-return path** (locked semantic 10: stunned owner's echo still acts). Restructure the early return so the echo hook is shared.
- `CombatAction` (`src/core/ai.py:39`): add `echo_turns: int = 1` field (after `boost_points`, defaulted — no call-site churn).

Rewind integration (`src/core/temporal.py`):
- `_apply_event` gains:
  - `ECHO_SPAWNED` → rebuild `Echo` from payload (embedded source actions), register in `_active_echoes`; assert side-cap invariant.
  - `ECHO_ACTED` → advance the matching echo's `next_index`; for `action_type == "attack"`, recompute `max(1, floor(source damage_dealt × 0.5))` from the echo's source action and **assert it equals the recorded `damage_dealt`** (determinism check, mirrors the attack-replay assertion), then `target.take_damage(...)` on the recorded `target_id`. Delete the echo when expired.
- `_replay_events`: reset `combat._active_echoes = {}` and `combat._action_history = defaultdict(...)` alongside the existing counter resets, before applying events.
- `_snapshot_rollback_state` / `_restore_rollback_state` (§8a contract): add copies of `_active_echoes` (copy each `Echo` — `next_index` is mutable) and `_action_history` (copy each deque). Restore both in step 3 of the restore order.

**Rewind × echo scenarios that must fall out correctly** (all covered in §7 tests):
- Rewind to before the cast → `CHARGE_SPENT`/`ECHO_SPAWNED` are outside the replay window → echo gone, charges effectively refunded by exclusion.
- Rewind to mid-echo-life → `ECHO_SPAWNED` + some `ECHO_ACTED` replay → echo restored at the right `next_index`; remaining acts continue on the new branch.
- Post-rewind echo events carry the new `branch_id` (builder already stamps it).

Logger (`src/core/combat_logger.py`): add `log_echo_spawned(owner, duration)` and `log_echo_acted(owner, action_type, target, damage)` — pure message formatting, same pattern as existing methods.

Builder (`src/core/combat_events.py`): add `echo_spawned(...)` and `echo_acted(...)` methods following the `charge_spent` template (turn_number + payload + branch stamp).

---

## 6. Concrete Edits

| File | Change |
|---|---|
| `src/core/temporal.py` | Replace `echo_cast` stub; add `EchoSourceAction`, `Echo`, `EchoCastResult`, `ECHO_CAST_COST`/`ECHO_DAMAGE_SCALE`/`MAX_ECHO_TURNS` constants, `execute_echo_turn()`; extend `_apply_event`, `_replay_events`, `_snapshot_rollback_state`, `_restore_rollback_state`. |
| `src/core/exceptions.py` | Add `EchoHistoryError`, `EchoAlreadyActiveError`, `EchoUnavailableError` under `TemporalError`. |
| `src/core/combat.py` | `_action_history` + `_active_echoes` state, `_side_of()`, `"echo_cast"` dispatch in `submit_player_action`, echo hook in `submit_player_action` + `execute_enemy_turn` (incl. broken path), history appends in `_execute_*`. |
| `src/core/ai.py` | `CombatAction.echo_turns: int = 1`. |
| `src/core/combat_events.py` | `echo_spawned()`, `echo_acted()` builder methods. |
| `src/core/combat_logger.py` | `log_echo_spawned()`, `log_echo_acted()`. |
| `tests/unit/test_echo.py` | NEW — unit tests (§7). |
| `tests/integration/test_echo_scenarios.py` | NEW — end-to-end + rewind-interop + determinism (§7). |
| `tests/unit/test_temporal.py` | Extend rollback tests for echo/history snapshot fields. |
| `tests/benchmarks/bench_echo.py` | NEW — frame-budget proof (`bench_*` naming — never `test_*`). |

Estimated diff: **~600–800 LOC added**, ~80 LOC modified, 10 files touched.

---

## 7. Test Plan

### Unit (`tests/unit/test_echo.py`)
Validation:
- `test_echo_cast_turns_zero_raises_value_error` / `test_echo_cast_turns_above_cap_raises_value_error`
- `test_echo_cast_insufficient_charge_raises_and_emits_nothing` (1 charge held, event count unchanged)
- `test_echo_cast_insufficient_history_raises_echo_history_error` (cast turns=2 after 1 action)
- `test_echo_cast_second_on_same_side_raises_already_active`
- `test_echo_cast_when_combat_over_raises_unavailable`
- `test_echo_cast_allowed_when_prior_echo_expired` / `test_echo_cast_allowed_when_prior_echo_owner_dead` (inert = expired for side cap)

Cast mechanics:
- `test_cast_emits_charge_spent_then_echo_spawned_in_order`
- `test_cast_spends_exactly_two_charges_regardless_of_turns`
- `test_echo_id_is_deterministic` (owner + cast turn; two identical seeded runs match)
- `test_echo_spawned_payload_embeds_source_actions` (matches last-N history, chronological)
- `test_cast_emits_no_action_executed`
- `test_echo_cast_result_shape`

Acting:
- `test_echo_does_not_act_on_cast_turn`
- `test_echo_attack_deals_floor_half_recorded_damage` + `test_echo_attack_minimum_one_damage`
- `test_echo_attack_consumes_no_rng` (damage_calc/combat RNG `getstate()` unchanged across an echo act)
- `test_echo_retargets_first_living_enemy_when_target_dead`
- `test_echo_fizzles_when_no_living_target`
- `test_defend_source_replays_as_defend_noop` / `test_flee_source_replays_as_fizzle`
- `test_echo_expires_after_n_acts_and_is_removed`
- `test_echo_acted_payload_shape` (resolved target_id, scaled damage, source_turn)
- `test_echo_shield_break_emits_shield_broken`
- `test_echo_kill_emits_combatant_defeated`
- `test_player_and_enemy_echoes_coexist` (one per side simultaneously)

### Integration (`tests/integration/test_echo_scenarios.py`)
- `test_full_combat_with_echo_cast_two` — 3 attacks → cast(2) → 2 turns: echo replays both attacks at half damage; exact event sequence asserted.
- `test_echo_cast_consumes_the_turn` — phase advances to next combatant, `_total_turns` incremented, no attack damage dealt on cast turn.
- `test_enemy_owned_echo_symmetric` — manually drive `echo_cast` for an enemy; echo hits the player on the enemy's subsequent turns.
- `test_broken_enemy_echo_still_acts` — stun the owner; echo acts on the skipped turn.
- `test_rewind_before_cast_removes_echo_and_refunds_charge` — cast at turn 5, rewind to 3: no echo, charge state excludes the spend.
- `test_rewind_mid_echo_life_restores_next_index` — echo has acted once of two; rewind to just after the first act; second act replays identically on the new branch.
- `test_post_rewind_echo_events_carry_new_branch_id`
- `test_rollback_restores_echo_and_history_state` — inject `_apply_event` failure during a replay that includes echo events; assert `_active_echoes` and `_action_history` bit-restored.

### Determinism
- `test_event_log_hash_stable_with_echo` — seeded combat including cast + acts + a rewind, run twice, event-log hash identical (extends Step 3's hash test; deterministic `echo_id` is what makes this pass).
- `test_replay_echo_damage_matches_recorded` — the `_apply_event` echo-damage assertion, triggered through a rewind over echo acts.

Coverage gate: ≥80% on all touched files (Principle 5). Run the full gauntlet (`just lint`, `just test`) before push; `just bench` for the new benchmark.

---

## 8. Open Questions

Closed in this plan: turn cost (consumes turn), damage source (recorded × 0.5), dead-target retarget, N player-chosen 1–3, no-act-on-cast-turn, fizzle semantics, inert-when-owner-dead, stunned-owner echo acts, deterministic echo_id, embedded source actions in `ECHO_SPAWNED`.

**Truly open** (tunable, not blocking):
1. **Min-1 damage floor** — ships as `max(1, floor(x × 0.5))`; revisit if 1-damage echo chip feels wrong in playtesting.
2. **Flat 0.5 scale vs. scaling by N or recency** — DESIGN Open Question 1. Ships flat; `ECHO_DAMAGE_SCALE` is a named constant so tuning is one line.
3. **Echo visual identity** — Step 8 (alpha ghosting per DESIGN M1 constraints).

---

## 9. Estimates

- **Files touched**: 10 (6 modified, 4 new — incl. 1 benchmark).
- **LOC added**: ~600–800.
- **Test count target**: ~24 unit + 8 integration + 2 determinism = **~34 new tests** minimum (561 → ~595).
- **Build time**: 1 focused implementation session (4–6 hrs incl. tests + coverage + benchmark).
- **Branch**: `phase/3-step-5-echo-cast` off `main`, per the flexible-granularity convention.
