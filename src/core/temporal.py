"""
TemporalSystem — DI entry point for all temporal abilities.

This module is the single place that orchestrates charge spend/regeneration
and will later host the full rewind, echo-cast, and counter-stop logic.
Each ability step is owned by a separate implementation phase:

- Phase 3 Step 2 (this file): resource management — spend / regenerate.
- Phase 3 Step 3: TemporalSystem.rewind() — single-turn rewind end-to-end.
- Phase 3 Step 5: TemporalSystem.echo_cast().
- Phase 3 Step 6: TemporalSystem.counter_stop().

Design constraints (see assignments/active/phase-3-timeline-mechanics/DESIGN.md):
- DI-only: all dependencies pass through the constructor (Constitution principle 2).
- Event sourcing: every charge change emits an immutable event (principle 1).
- Combat-bounded: TemporalSystem is constructed inside CombatContext; temporal
  abilities only exist in combat.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.core.combat_events import CombatEventBuilder
from src.core.events import EventTypes, GameEvent, is_rewindable
from src.core.exceptions import (
    InsufficientChargeError,
    RewindBoundaryError,
    RewindReplayError,
    RewindUnavailableError,
)
from src.core.persistence import EventStore
from src.entities.combatant import Combatant
from src.entities.enemy import Enemy
from src.entities.player import Player

if TYPE_CHECKING:
    from src.core.combat import CombatContext


@dataclass(frozen=True)
class RewindResult:
    """
    Outcome payload returned from a successful ``TemporalSystem.rewind`` call.

    The result is informational: by the time it is constructed, the
    CHARGE_SPENT and TEMPORAL_REWIND events are already persisted and the
    in-memory ``CombatContext`` is positioned at ``to_turn`` on
    ``new_branch_id``. Failed rewinds raise an exception instead of
    returning this dataclass.

    Attributes:
        from_turn: Turn number combat was at before rewind.
        to_turn: Turn number combat resumed at.
        new_branch_id: Branch identifier allocated for the resumed timeline.
        events_replayed: Count of rewindable events re-applied to rebuild
            combat state up to ``to_turn``.
        charge_spent: Amount of temporal charge debited from the actor.
    """

    from_turn: int
    to_turn: int
    new_branch_id: int
    events_replayed: int
    charge_spent: int


class TemporalSystem:
    """
    Orchestrates temporal charge economy and temporal abilities in combat.

    Constructed by ``CombatContext.__init__`` with the same ``EventStore``
    and ``CombatEventBuilder`` instances that power the rest of combat, so
    all temporal events flow through the same append-only log without any
    extra wiring.

    Attributes:
        _event_store: Append-only event store (Constitution principle 1).
        _event_builder: Shared builder; ``set_branch`` on the builder updates
            the branch_id stamped on all subsequent events (wired in Step 3).

    Example:
        >>> system = TemporalSystem(event_store=store, event_builder=builder)
        >>> system.spend(actor=player, amount=1, ability="rewind", turn_number=3)
        >>> gained = system.regenerate(actor=player, amount=1, turn_number=0)
    """

    def __init__(
        self,
        event_store: EventStore,
        event_builder: CombatEventBuilder,
    ) -> None:
        """
        Initialise TemporalSystem with injected dependencies.

        Args:
            event_store: Append-only persistence layer for combat events.
            event_builder: Shared builder; branch_id is read from the builder
                at emit time so rewind branch updates propagate automatically.
        """
        self._event_store = event_store
        self._event_builder = event_builder

    # -------------------------------------------------------------------------
    # Public API — implemented in Step 2
    # -------------------------------------------------------------------------

    def spend(
        self,
        actor: Combatant,
        amount: int,
        ability: str,
        turn_number: int,
    ) -> None:
        """
        Spend temporal charge from an actor and emit a CHARGE_SPENT event.

        The event is emitted *before* the charge is deducted so that the
        event log records the intent at the current turn position (mirrors
        the ordering convention used by Phase 3 Step 3 rewind logic).

        Args:
            actor: The combatant spending charge.
            amount: Number of charges to spend (must satisfy
                ``actor.spend_charge`` preconditions: non-negative and ≤ current
                charge).
            ability: Name of the ability being activated (e.g. ``"rewind"``).
            turn_number: Current combat turn number for event stamping.

        Raises:
            ValueError: Propagated from ``actor.spend_charge`` if ``amount``
                is negative or exceeds ``actor.temporal_charge``.
        """
        event = self._event_builder.charge_spent(
            turn_number=turn_number,
            actor_id=actor.id,
            amount=amount,
            ability=ability,
        )
        self._event_store.append_event(event)
        actor.spend_charge(amount)

    def regenerate(
        self,
        actor: Combatant,
        amount: int,
        turn_number: int,
    ) -> int:
        """
        Regenerate temporal charge for an actor (capped at max).

        A CHARGE_REGENERATED event is emitted only when at least 1 charge is
        actually gained. If the actor is already at ``max_temporal_charge``,
        no event is emitted and 0 is returned.

        Args:
            actor: The combatant gaining charge.
            amount: Requested charge gain (must be non-negative per
                ``actor.gain_charge`` preconditions).
            turn_number: Current combat turn number for event stamping.

        Returns:
            Actual charge gained (0 if already at cap or if ``amount`` is 0).

        Raises:
            ValueError: Propagated from ``actor.gain_charge`` if ``amount``
                is negative.
        """
        actual_gained = actor.gain_charge(amount)
        if actual_gained > 0:
            event = self._event_builder.charge_regenerated(
                turn_number=turn_number,
                actor_id=actor.id,
                amount=actual_gained,
                new_total=actor.temporal_charge,
            )
            self._event_store.append_event(event)
        return actual_gained

    # -------------------------------------------------------------------------
    # Rewind — implemented in Step 3
    # -------------------------------------------------------------------------

    def rewind(
        self,
        combat: CombatContext,
        actor: Combatant,
        turns: int = 1,
    ) -> RewindResult:
        """
        Rewind combat to a prior turn on a new branch (single-turn, Step 3).

        Event ordering (see STEP-3-PLAN.md §3):
        1. Validate (charge, turns, target_turn, phase, is_over).
        2. Snapshot rollback state (§8a).
        3. Emit CHARGE_SPENT at pre-rewind branch/turn — immutable historical
           record. This event remains in the store even if replay later fails;
           the failed-spend is washed out of charge resolution because it lives
           on a branch that is never adopted.
        4. Decrement actor charge.
        5. Compute and apply new_branch_id on combat + builder.
        6. Replay events inside try/except; on failure restore snapshot and
           raise RewindReplayError. CHARGE_SPENT stays in store (principle 11).
        7. Emit TEMPORAL_REWIND at new branch.
        8. Return RewindResult.

        Args:
            combat: The active CombatContext to rewind.
            actor: The combatant spending charge to trigger the rewind
                (typically the player).
            turns: Number of turns to rewind (must be 1 for Step 3).

        Returns:
            RewindResult with from_turn, to_turn, new_branch_id,
            events_replayed, and charge_spent.

        Raises:
            ValueError: If ``turns < 1``.
            NotImplementedError: If ``turns > 1`` (multi-turn deferred to
                Step 4).
            InsufficientChargeError: If ``actor.temporal_charge < turns``.
            RewindBoundaryError: If the target turn would be < 0.
            RewindUnavailableError: If combat is over or in a phase that
                forbids rewind (only AWAITING_PLAYER_INPUT and ROUND_END are
                permitted).
            RewindReplayError: If event replay fails after CHARGE_SPENT has
                already been recorded. In-memory state is restored from the
                pre-rewind snapshot; the CHARGE_SPENT event is NOT rolled back.
        """
        from src.core.combat import CombatPhase

        # --- Step 1: Validate ---
        if turns < 1:
            raise ValueError(f"turns must be at least 1, got {turns}")
        if turns > 1:
            raise NotImplementedError("multi-turn rewind lands in Step 4")

        if actor.temporal_charge < turns:
            raise InsufficientChargeError(
                f"Insufficient temporal charge: have {actor.temporal_charge}, need {turns}"
            )

        target_turn = combat._total_turns - turns
        if target_turn < 0:
            raise RewindBoundaryError(
                f"Rewind would land before turn 0: total_turns={combat._total_turns}, turns={turns}"
            )

        if combat.is_over or combat.phase == CombatPhase.COMBAT_OVER:
            raise RewindUnavailableError("Cannot rewind: combat is over")

        if combat.phase == CombatPhase.EXECUTING_TURN:
            raise RewindUnavailableError(
                "Cannot rewind during turn execution (EXECUTING_TURN phase)"
            )

        allowed_phases = {CombatPhase.AWAITING_PLAYER_INPUT, CombatPhase.ROUND_END}
        if combat.phase not in allowed_phases:
            raise RewindUnavailableError(
                f"Rewind not allowed in phase {combat.phase.name}; "
                f"allowed: AWAITING_PLAYER_INPUT, ROUND_END"
            )

        from_turn = combat._total_turns

        # --- Step 2: Snapshot rollback state ---
        snapshot = self._snapshot_rollback_state(combat, actor)

        # --- Step 3: Emit CHARGE_SPENT at pre-rewind branch/turn ---
        charge_event = self._event_builder.charge_spent(
            turn_number=combat._total_turns,
            actor_id=actor.id,
            amount=turns,
            ability="rewind",
        )
        self._event_store.append_event(charge_event)

        # --- Step 4: Decrement actor charge ---
        actor.spend_charge(turns)

        # --- Step 5: Compute new branch ---
        new_branch_id = combat._current_branch_id + 1

        # --- Step 6: Bump branch on combat and builder ---
        combat._current_branch_id = new_branch_id
        combat._event_builder.set_branch(new_branch_id)

        # --- Step 7: Replay (with rollback on failure) ---
        try:
            events_replayed = self._replay_events(combat, to_turn=target_turn)
        except Exception as exc:
            self._restore_rollback_state(combat, actor, snapshot)
            raise RewindReplayError(f"Replay failed at target_turn={target_turn}: {exc}") from exc

        # --- Step 8: Emit TEMPORAL_REWIND at new branch ---
        rewind_event = self._event_builder.temporal_rewind(
            turn_number=target_turn,
            actor_id=actor.id,
            from_turn=from_turn,
            to_turn=target_turn,
            branch_id=new_branch_id,
        )
        self._event_store.append_event(rewind_event)

        # --- Step 9: Return result ---
        return RewindResult(
            from_turn=from_turn,
            to_turn=target_turn,
            new_branch_id=new_branch_id,
            events_replayed=events_replayed,
            charge_spent=turns,
        )

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _snapshot_rollback_state(
        self,
        combat: CombatContext,
        actor: Combatant,
    ) -> dict:
        """
        Capture all mutable state needed to restore combat after a failed replay.

        Taken before any mutation. All values are copies; combatant references
        remain the same live objects (we mutate their fields directly on restore).

        Args:
            combat: The active CombatContext.
            actor: The combatant spending charge.

        Returns:
            A dict with keys: actor_charge, branch_id, phase, total_turns,
            round_number, turn_index, turn_order (shallow copy),
            combatants (list of per-combatant field dicts),
            rng_state, damage_calc_rng_state, ai_rng_states (dict),
            builder_branch_id.
        """
        combatant_snapshots: list[dict] = []
        for c in [combat.player] + list(combat.enemies):
            entry: dict = {
                "ref": c,
                "hp": c.hp,
                "temporal_charge": c.temporal_charge,
            }
            if isinstance(c, Player):
                entry["boost_points"] = c.boost_points
            if isinstance(c, Enemy):
                entry["shield_points"] = c.shield_points
                entry["is_broken"] = c.is_broken
                entry["break_turns_remaining"] = c.break_turns_remaining
            combatant_snapshots.append(entry)

        ai_rng_states: dict[str, object] = {
            enemy_id: ai.rng.getstate() for enemy_id, ai in combat._enemy_ais.items()
        }

        return {
            "actor_charge": actor.temporal_charge,
            "branch_id": combat._current_branch_id,
            "phase": combat._phase,
            "total_turns": combat._total_turns,
            "round_number": combat._round_number,
            "turn_index": combat._turn_index,
            "turn_order": list(combat._turn_order),
            "combatants": combatant_snapshots,
            "rng_state": combat._rng.getstate(),
            "damage_calc_rng_state": combat._damage_calc.rng.getstate(),
            "ai_rng_states": ai_rng_states,
            "builder_branch_id": combat._event_builder.branch_id,
        }

    def _restore_rollback_state(
        self,
        combat: CombatContext,
        actor: Combatant,  # noqa: ARG002 — kept for API symmetry with _snapshot
        snapshot: dict,
    ) -> None:
        """
        Restore CombatContext and combatants to a previously-snapshotted state.

        Restore order follows §8a: combatants first, then RNG, then counters,
        then branch. This ensures no invariant is violated mid-restore.

        Args:
            combat: The CombatContext to restore.
            actor: The combatant whose charge was spent (unused directly;
                charge is restored via the combatants snapshot).
            snapshot: Dict produced by ``_snapshot_rollback_state``.
        """
        # 1. Restore combatant fields (HP, BP, shields, break, charge)
        for entry in snapshot["combatants"]:
            c = entry["ref"]
            c.hp = entry["hp"]
            c.temporal_charge = entry["temporal_charge"]
            if isinstance(c, Player):
                c.boost_points = entry["boost_points"]
            if isinstance(c, Enemy):
                c.shield_points = entry["shield_points"]
                c.is_broken = entry["is_broken"]
                c.break_turns_remaining = entry["break_turns_remaining"]

        # 2. Restore RNG states (combat, damage_calc, each AI)
        combat._rng.setstate(snapshot["rng_state"])
        combat._damage_calc.rng.setstate(snapshot["damage_calc_rng_state"])
        for enemy_id, rng_state in snapshot["ai_rng_states"].items():
            combat._enemy_ais[enemy_id].rng.setstate(rng_state)

        # 3. Restore turn counters, phase, turn_order, turn_index
        combat._total_turns = snapshot["total_turns"]
        combat._round_number = snapshot["round_number"]
        combat._turn_index = snapshot["turn_index"]
        combat._turn_order = snapshot["turn_order"]
        combat._phase = snapshot["phase"]

        # 4. Restore branch_id on combat and builder
        combat._current_branch_id = snapshot["branch_id"]
        combat._event_builder.set_branch(snapshot["builder_branch_id"])

    def _replay_events(self, combat: CombatContext, to_turn: int) -> int:
        """
        Rebuild in-memory CombatContext state from the event store up to ``to_turn``.

        Replay is purely in-memory — no events are emitted. Only rewindable
        events (filtered via ``is_rewindable()``) are processed; persistent
        events (COMBAT_STARTED, TEMPORAL_REWIND, etc.) are skipped.

        RNG strategy (LOCKED): reseed from ``combat._seed`` and re-derive all
        subordinate seeds by replaying the same ``randint(0, 2**31)`` chain
        the constructor uses. This is bit-identical to original initialization.

        ``_round_number`` is derived from the count of TURN_STARTED events
        encountered during replay (each TURN_STARTED that begins a new round
        increments the counter). Do NOT call ``start_round()`` — that would
        re-emit events.

        Args:
            combat: CombatContext whose in-memory state will be rebuilt.
            to_turn: Inclusive upper bound on ``turn_number`` for rewindable
                events. Events at turn_number > to_turn are excluded.

        Returns:
            Number of rewindable events applied.

        Raises:
            Any exception from ``_apply_event`` propagates upward (caller
            wraps in RewindReplayError).
        """
        from src.core.combat import CombatPhase

        # --- Query events for this combat's timeline ---
        all_events = self._event_store.get_events_by_timeline(combat._timeline_id)
        combat_events = [
            e
            for e in all_events
            if e.aggregate_id == combat.combat_id
            and e.branch_id <= combat._current_branch_id - 1  # pre-rewind branch only
        ]

        # --- Partition: rewindable, truncated to to_turn ---
        replay_set: list[GameEvent] = []
        for event in combat_events:
            if not is_rewindable(event.event_type):
                continue
            event_data = json.loads(event.event_data)
            turn_number = event_data.get("turn_number", 0)
            if turn_number <= to_turn:
                replay_set.append(event)

        # --- Reset combatants to COMBAT_STARTED state ---
        started_event = next(
            (e for e in combat_events if e.event_type == EventTypes.COMBAT_STARTED),
            None,
        )
        if started_event is not None:
            started_data = json.loads(started_event.event_data)
            player_data = started_data.get("player", {})
            combat.player.hp = player_data.get("hp", combat.player.max_hp)
            combat.player.boost_points = player_data.get("boost_points", 0)
            combat.player.temporal_charge = 0

            enemy_map = {e.get("id"): e for e in started_data.get("enemies", [])}
            for enemy in combat.enemies:
                edata = enemy_map.get(enemy.id, {})
                enemy.hp = edata.get("hp", enemy.max_hp)
                enemy.shield_points = edata.get("shield_points", enemy.max_shield_points)
                enemy.is_broken = False
                enemy.break_turns_remaining = 0
                enemy.temporal_charge = 0
        else:
            # Fallback: reset to max values
            combat.player.hp = combat.player.max_hp
            combat.player.boost_points = 0
            combat.player.temporal_charge = 0
            for enemy in combat.enemies:
                enemy.hp = enemy.max_hp
                enemy.shield_points = enemy.max_shield_points
                enemy.is_broken = False
                enemy.break_turns_remaining = 0
                enemy.temporal_charge = 0

        # --- Reset turn counters ---
        combat._total_turns = 0
        combat._round_number = 0
        combat._turn_index = 0
        combat._turn_order = []
        combat._phase = CombatPhase.ROUND_START

        # --- Reseed RNG: bit-identical to constructor ---
        combat._rng = random.Random(combat._seed)
        combat._damage_calc.rng = random.Random(combat._rng.randint(0, 2**31))
        for enemy in combat.enemies:
            new_ai_seed = combat._rng.randint(0, 2**31)
            combat._enemy_ais[enemy.id].rng = random.Random(new_ai_seed)

        # --- Apply each event in order ---
        for event in replay_set:
            self._apply_event(combat, event)

        # --- Position at to_turn ready for player input ---
        # Replay reset _turn_order to [] above; rebuild it so combat is
        # resumable after the rewind (otherwise the next advance_turn indexes
        # into an empty list). Point _turn_index at the player so the resumed
        # turn belongs to whoever is taking input.
        combat._turn_order = combat._calculate_turn_order()
        combat._turn_index = next(
            (i for i, c in enumerate(combat._turn_order) if c is combat.player),
            0,
        )
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT

        return len(replay_set)

    def _apply_event(self, combat: CombatContext, event: GameEvent) -> None:
        """
        Apply a single rewindable event to rebuild in-memory combat state.

        This is a pure in-memory mutation — no events are emitted. For
        ACTION_EXECUTED attack events the damage is recomputed from the
        reseeded RNG and asserted to match the recorded ``damage_dealt``
        (determinism check). A mismatch raises AssertionError, which the
        caller (``_replay_events``) propagates as ``RewindReplayError``.

        Args:
            combat: CombatContext being rebuilt.
            event: A rewindable GameEvent to apply.

        Raises:
            AssertionError: If recomputed attack damage does not match the
                recorded ``damage_dealt`` (broken RNG determinism).
            ValueError: If a referenced combatant ID is not found.
        """
        data = json.loads(event.event_data)
        etype = event.event_type

        if etype == EventTypes.TURN_STARTED:
            # Derive _round_number and _total_turns from TURN_STARTED events.
            turn_number = data.get("turn_number", 0)
            combat._total_turns = turn_number
            # Increment round counter when turn_index wraps to 0
            turn_order_len = len(combat._turn_order) if combat._turn_order else 1
            if turn_number == 1 or (turn_number > 1 and (turn_number - 1) % turn_order_len == 0):
                combat._round_number += 1

        elif etype == EventTypes.ACTION_EXECUTED:
            action_type = data.get("action_type")
            actor_id = data.get("actor_id", "")
            target_id = data.get("target_id")
            damage_dealt = data.get("damage_dealt")
            bp_spent = data.get("boost_points_spent", 0) or 0

            actor = self._find_combatant(combat, actor_id)
            target = self._find_combatant(combat, target_id) if target_id else None

            if action_type == "attack" and target is not None and damage_dealt is not None:
                from src.entities import DamageType

                defender_weaknesses: list[DamageType] = []
                defender_is_broken = False
                if isinstance(target, Enemy):
                    defender_weaknesses = target.weaknesses
                    defender_is_broken = target.is_broken

                damage_result = combat._damage_calc.calculate(
                    attacker_atk=actor.attack,
                    defender_def=target.defense,
                    boost_points=bp_spent,
                    damage_type=DamageType.PHYSICAL,
                    defender_weaknesses=defender_weaknesses,
                    defender_is_broken=defender_is_broken,
                )

                # Determinism check: recomputed damage must match recorded
                assert damage_result.damage == damage_dealt, (
                    f"Replay determinism failure: recomputed damage "
                    f"{damage_result.damage} != recorded {damage_dealt} "
                    f"for ACTION_EXECUTED at turn {data.get('turn_number')}"
                )

                target.take_damage(damage_result.damage, DamageType.PHYSICAL)

                # Spend BP if player attacked
                if isinstance(actor, Player) and bp_spent > 0:
                    actor.spend_bp(bp_spent)

            elif action_type == "flee":
                # Flee draws 1 RNG value — consume it to stay in sync
                combat._rng.randint(1, 100)

            # defend: no RNG, no state change beyond what's already tracked

        elif etype == EventTypes.SHIELD_BROKEN:
            # Integrity assertion — shield break is already applied by take_damage
            combatant_id = data.get("combatant_id", "")
            combatant = self._find_combatant(combat, combatant_id)
            if isinstance(combatant, Enemy):
                assert combatant.is_broken, (
                    f"SHIELD_BROKEN event for {combatant_id} but enemy not broken "
                    f"after replaying preceding ACTION_EXECUTED"
                )

        elif etype == EventTypes.BOOST_POINT_GAINED:
            combatant_id = data.get("combatant_id", "")
            amount_gained = data.get("amount_gained", 1)
            combatant = self._find_combatant(combat, combatant_id)
            if isinstance(combatant, Player):
                combatant.gain_bp(amount_gained)

        elif etype == EventTypes.CHARGE_SPENT:
            actor_id = data.get("actor_id", "")
            amount = data.get("amount", 0)
            combatant = self._find_combatant(combat, actor_id)
            combatant.spend_charge(amount)

        elif etype == EventTypes.CHARGE_REGENERATED:
            actor_id = data.get("actor_id", "")
            amount = data.get("amount", 0)
            combatant = self._find_combatant(combat, actor_id)
            combatant.gain_charge(amount)

        # ECHO_STONE_USED, ECHO_SPAWNED, ECHO_ACTED: deferred to Step 5

    def _find_combatant(self, combat: CombatContext, combatant_id: str) -> Combatant:
        """
        Look up a combatant by ID within the given CombatContext.

        Args:
            combat: The CombatContext to search.
            combatant_id: Unique combatant identifier.

        Returns:
            The matching Combatant instance.

        Raises:
            ValueError: If no combatant with the given ID is found.
        """
        if combat.player.id == combatant_id:
            return combat.player
        for enemy in combat.enemies:
            if enemy.id == combatant_id:
                return enemy
        raise ValueError(f"Combatant not found in combat: {combatant_id!r}")

    # -------------------------------------------------------------------------
    # Stubs — implemented in later steps
    # -------------------------------------------------------------------------

    def echo_cast(self, *args: object, **kwargs: object) -> object:
        """
        Summon a past-self echo to act alongside the player.

        Not yet implemented. Echo Cast lands in Phase 3 Step 5.

        Raises:
            NotImplementedError: Always — implementation pending Step 5.
        """
        raise NotImplementedError("Phase 3 Step 5")

    def counter_stop(self, *args: object, **kwargs: object) -> object:
        """
        Interrupt an opponent's declared temporal ability.

        Not yet implemented. Counter-Stop lands in Phase 3 Step 6.

        Raises:
            NotImplementedError: Always — implementation pending Step 6.
        """
        raise NotImplementedError("Phase 3 Step 6")
