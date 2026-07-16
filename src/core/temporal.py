"""
TemporalSystem — DI entry point for all temporal abilities.

This module is the single place that orchestrates charge spend/regeneration
and will later host the full rewind, echo-cast, and counter-stop logic.
Each ability step is owned by a separate implementation phase:

- Phase 3 Step 2 (this file): resource management — spend / regenerate.
- Phase 3 Step 3: TemporalSystem.rewind() — single-turn rewind end-to-end.
- Phase 3 Step 5: TemporalSystem.echo_cast().
- Phase 3 Step 6: Counter-Stop — the announce/response-window interrupt
  model, wired into rewind() and echo_cast() via the private
  _offer_counter_window(). There is deliberately no public "cast
  counter-stop" API; it only exists as a response inside the window.

Design constraints (see assignments/active/phase-3-timeline-mechanics/DESIGN.md):
- DI-only: all dependencies pass through the constructor (Constitution principle 2).
- Event sourcing: every charge change emits an immutable event (principle 1).
- Combat-bounded: TemporalSystem is constructed inside CombatContext; temporal
  abilities only exist in combat.
"""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from src.core.combat_events import CombatEventBuilder
from src.core.events import EventTypes, GameEvent, is_rewindable
from src.core.exceptions import (
    EchoAlreadyActiveError,
    EchoHistoryError,
    EchoUnavailableError,
    InsufficientChargeError,
    RewindBoundaryError,
    RewindReplayError,
    RewindUnavailableError,
)
from src.core.persistence import EventStore
from src.entities.combatant import Combatant
from src.entities.damage_types import DamageType
from src.entities.enemy import Enemy
from src.entities.player import Player

if TYPE_CHECKING:
    from src.core.combat import CombatContext

# Echo Cast constants (Phase 3 Step 5). Named so tuning is one line — see
# DESIGN.md Open Question 1 (flat 0.5 scale vs. scaling by N or recency).
ECHO_CAST_COST = 2  # flat charge cost, regardless of `turns`
ECHO_DAMAGE_SCALE = 0.5
MAX_ECHO_TURNS = 3  # mirrors the rewind/charge cap

# Counter-Stop constants (Phase 3 Step 6).
COUNTER_STOP_COST = 3  # flat — a responder's entire pool, spent whole


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


@dataclass(frozen=True)
class EchoSourceAction:
    """
    One action from the owner's history, embedded in an Echo for replay.

    Captured from ``CombatContext._action_history`` at cast time and
    embedded directly in the ``ECHO_SPAWNED`` payload, so rewind replay
    reconstructs the Echo from that one event with no query against prior
    ACTION_EXECUTED rows (see Phase 3 Step 5 plan §3).

    Attributes:
        source_turn: Turn number the original action was executed on.
        action_type: "attack", "defend", or "flee".
        target_id: Original target ID (attack only), else None.
        damage_dealt: Original recorded damage (attack only), else None.
    """

    source_turn: int
    action_type: str
    target_id: str | None
    damage_dealt: int | None


@dataclass
class Echo:
    """
    A past-self echo that replays an owner's recent actions at reduced damage.

    Not frozen: ``next_index`` mutates as the echo acts on each of its
    owner's subsequent turns until ``is_expired``.

    Attributes:
        echo_id: Deterministic identifier (``f"echo_{owner_id}_t{cast_turn}"``,
            no UUIDs — required for the event-log-hash determinism test).
        owner_id: ID of the combatant who cast the echo.
        source_actions: Embedded source window, chronological order (most
            recent last).
        next_index: Index into ``source_actions`` of the next act.
    """

    echo_id: str
    owner_id: str
    source_actions: tuple[EchoSourceAction, ...]
    next_index: int = field(default=0)

    @property
    def is_expired(self) -> bool:
        """Whether the echo has replayed all of its source actions."""
        return self.next_index >= len(self.source_actions)


@dataclass(frozen=True)
class EchoCastResult:
    """
    Outcome payload returned from a successful ``TemporalSystem.echo_cast`` call.

    By the time this is constructed, CHARGE_SPENT and ECHO_SPAWNED are
    already persisted and the echo is registered in
    ``combat._active_echoes``. Failed casts raise an exception instead of
    returning this dataclass.

    Attributes:
        echo_id: The newly spawned echo's deterministic identifier.
        owner_id: ID of the combatant who cast the echo.
        duration: Number of turns the echo will act (1-3).
        charge_spent: Charge debited from the actor (always ECHO_CAST_COST).
        source_turns: Turn numbers of the embedded source actions, in the
            same chronological order they will replay in.
    """

    echo_id: str
    owner_id: str
    duration: int
    charge_spent: int
    source_turns: tuple[int, ...]


@dataclass(frozen=True)
class TemporalAnnouncement:
    """
    Declares a temporal ability's cast before it resolves, opening the
    Counter-Stop response window (DESIGN interrupt model: "the acting side
    commits to the cast; the opposing side gets a response window").

    Attributes:
        ability: The announced ability — "rewind" or "echo_cast".
        caster_id: ID of the combatant casting the ability.
        magnitude: Turns rewound (rewind) or echo window N (echo_cast).
        turn_number: Current combat turn at announcement time.
    """

    ability: str
    caster_id: str
    magnitude: int
    turn_number: int


@dataclass(frozen=True)
class CounterStopResult:
    """
    Outcome payload returned when a Counter-Stop fizzles an announced cast.

    Being countered is a legitimate game outcome, not an error (Phase 3
    Step 6 locked semantic 3) — ``rewind()`` / ``echo_cast()`` return this
    instead of their usual result dataclass. By construction time, the
    caster's CHARGE_SPENT (for the fizzled ability), the responder's
    CHARGE_SPENT(3, "counter_stop"), and COUNTER_STOP_TRIGGERED are all
    persisted. The caster's charge stays spent — the ability fizzles but
    its cost is not refunded — so there is nothing to roll back.

    Attributes:
        countered_ability: The ability that fizzled — "rewind" or "echo_cast".
        caster_id: ID of the combatant whose cast was countered.
        responder_id: ID of the combatant who countered.
        caster_charge_lost: Charge the fizzled cast cost the caster (the
            rewound turn count, or ECHO_CAST_COST for echo_cast).
        responder_charge_spent: Charge the responder spent (always
            COUNTER_STOP_COST).
        turn_number: Turn number the counter landed on.
    """

    countered_ability: str
    caster_id: str
    responder_id: str
    caster_charge_lost: int
    responder_charge_spent: int
    turn_number: int


class CounterStopPolicy(Protocol):
    """
    Decides whether an eligible combatant Counter-Stops an announced cast.

    One policy instance decides for **both sides** (decided 2026-07-15) —
    the same policy answers on behalf of the player and every enemy.
    Step 6 ships only ``NeverCounterPolicy``; Step 7 swaps in Chronomancer
    decision weights through this same seam, with no changes required to
    ``rewind()`` / ``echo_cast()`` / ``_offer_counter_window()``.
    """

    def decide(
        self,
        combat: CombatContext,
        announcement: TemporalAnnouncement,
        eligible: Sequence[Combatant],
    ) -> Combatant | None:
        """
        Choose a responder to Counter-Stop, or decline.

        Args:
            combat: The active CombatContext.
            announcement: The cast being announced.
            eligible: Combatants who may respond — always non-empty; the
                caller only invokes this once at least one candidate
                qualifies (Phase 3 Step 6 locked semantic 7).

        Returns:
            The responding Combatant to counter with, or None to let the
            cast proceed uncontested. Returning a combatant not present in
            ``eligible`` is a programming error the caller raises on
            (locked semantic 8).
        """
        ...


class NeverCounterPolicy:
    """
    Default Counter-Stop policy: nobody ever counters.

    Every existing flow is behaviorally unchanged out of the box with this
    policy in place (Phase 3 Step 6 locked semantic 4) — all pre-Step-6
    tests pass untouched. Step 7 swaps in Chronomancer weights.
    """

    def decide(
        self,
        combat: CombatContext,  # noqa: ARG002
        announcement: TemporalAnnouncement,  # noqa: ARG002
        eligible: Sequence[Combatant],  # noqa: ARG002
    ) -> Combatant | None:
        """Always decline — see class docstring."""
        return None


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
        _counter_policy: Decides Counter-Stop responses for both sides
            (Phase 3 Step 6). Defaults to ``NeverCounterPolicy``.

    Example:
        >>> system = TemporalSystem(event_store=store, event_builder=builder)
        >>> system.spend(actor=player, amount=1, ability="rewind", turn_number=3)
        >>> gained = system.regenerate(actor=player, amount=1, turn_number=0)
    """

    def __init__(
        self,
        event_store: EventStore,
        event_builder: CombatEventBuilder,
        counter_policy: CounterStopPolicy | None = None,
    ) -> None:
        """
        Initialise TemporalSystem with injected dependencies.

        Args:
            event_store: Append-only persistence layer for combat events.
            event_builder: Shared builder; branch_id is read from the builder
                at emit time so rewind branch updates propagate automatically.
            counter_policy: Decides Counter-Stop responses for both sides
                (Phase 3 Step 6). Defaulted so existing call sites need no
                changes; defaults to ``NeverCounterPolicy()``, which keeps
                every pre-Step-6 flow behaviorally unchanged.
        """
        self._event_store = event_store
        self._event_builder = event_builder
        self._counter_policy = (
            counter_policy if counter_policy is not None else NeverCounterPolicy()
        )

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
    ) -> RewindResult | CounterStopResult:
        """
        Rewind combat ``turns`` turns back on a new branch.

        Single-turn shipped in Step 3; multi-turn (``turns > 1``) in Step 4.
        Each rewound turn costs 1 charge, so the charge pool bounds depth.
        Rewind is counterable (Step 6): the opposing side gets a response
        window after the actor commits, before the replay-heavy work starts.

        Event ordering (see STEP-3-PLAN.md §3, extended by STEP-6-PLAN.md §4):
        1. Validate (charge, turns, target_turn, phase, is_over).
        2. Snapshot rollback state (§8a). Taken *before* the spend — a
           deliberate deviation from STEP-6-PLAN.md §4's literal
           "spend → window → snapshot" ordering: if the snapshot were taken
           after the spend, a later *replay failure* (a distinct error path
           from being countered) could only restore actor charge to its
           post-spend value, not its true pre-rewind value, breaking the
           existing replay-failure rollback contract (principle 11 / §8a).
           A countered cast still never touches this snapshot beyond taking
           it — it returns before restore is ever called, so nothing is
           observably rolled back for that path either way.
        3. Emit CHARGE_SPENT at pre-rewind branch/turn — immutable historical
           record. This event remains in the store even if the cast is later
           countered or replay fails; the actor's charge stays spent either
           way (DESIGN: "the acting side commits to the cast").
        4. Decrement actor charge.
        5. Offer the Counter-Stop response window. Countered → return
           CounterStopResult immediately; nothing below runs (no branch
           bump, no replay, no TEMPORAL_REWIND).
        6. Compute and apply new_branch_id on combat + builder.
        7. Replay events inside try/except; on failure restore snapshot and
           raise RewindReplayError. CHARGE_SPENT stays in store (principle 11).
        8. Emit TEMPORAL_REWIND at new branch.
        9. Return RewindResult.

        Args:
            combat: The active CombatContext to rewind.
            actor: The combatant spending charge to trigger the rewind
                (typically the player).
            turns: Number of turns to rewind (>= 1; bounded by available charge).

        Returns:
            RewindResult with from_turn, to_turn, new_branch_id,
            events_replayed, and charge_spent — or CounterStopResult if an
            eligible opposing combatant countered the cast (Step 6).

        Raises:
            ValueError: If ``turns < 1``, or if the configured
                ``CounterStopPolicy`` returns a combatant outside the
                eligible set (a policy programming error).
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
        # Multi-turn rewind (turns > 1) is supported as of Step 4; it costs
        # `turns` charges, so the per-combat charge cap naturally bounds depth.

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
        # Taken before the spend (not after — see deviation note on this
        # method's docstring): a countered cast returns before this snapshot
        # is ever acted upon (never restored-from), so taking it here costs
        # nothing observable; taking it after the spend would mean a later
        # *replay failure* (a distinct, non-counter error path) could only
        # restore actor charge back to its post-spend value, not its true
        # pre-rewind value — breaking the existing replay-failure rollback
        # contract (Constitution principle 11 / STEP-3-PLAN §8a).
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

        # --- Step 5: Offer the Counter-Stop response window ---
        counter_result = self._offer_counter_window(
            combat,
            caster=actor,
            ability="rewind",
            magnitude=turns,
            caster_charge_lost=turns,
        )
        if counter_result is not None:
            return counter_result

        # --- Step 6: Compute and apply new branch ---
        new_branch_id = combat._current_branch_id + 1
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
    # Echo Cast — implemented in Step 5
    # -------------------------------------------------------------------------

    def echo_cast(
        self,
        combat: CombatContext,
        actor: Combatant,
        turns: int = 1,
    ) -> EchoCastResult | CounterStopResult:
        """
        Cast an Echo: a past-self replays the actor's last ``turns`` actions.

        Casting consumes the actor's turn (Phase 3 Step 5 locked semantic
        1) — this method rides ``submit_player_action``'s existing rails,
        same as ``_execute_attack``. No phase validation is performed here;
        the player path is phase-gated by the dispatcher, and enemy casts
        (driven manually until the Chronomancer AI lands in Step 7) run
        inside EXECUTING_TURN too. Echo Cast is counterable (Step 6): the
        opposing side gets a response window after the actor commits,
        before the Echo is built.

        Event flow on success (see STEP-5-PLAN.md §3, extended by
        STEP-6-PLAN.md §4):
        1. Validate (below) — no events, no mutation on any error path.
        2. Capture the source window from ``combat._action_history``.
        3. Emit CHARGE_SPENT.
        4. ``actor.spend_charge(ECHO_CAST_COST)``.
        5. Offer the Counter-Stop response window. Countered → return
           CounterStopResult immediately; no Echo is built or registered,
           no ECHO_SPAWNED is emitted.
        6. Build the Echo with a deterministic ``echo_id``; register it in
           ``combat._active_echoes[side]``.
        7. Emit ECHO_SPAWNED with the source window embedded in the payload.
        8. Return EchoCastResult.

        No ACTION_EXECUTED is emitted for the cast turn — the turn's
        record is TURN_STARTED -> CHARGE_SPENT -> ECHO_SPAWNED. This also
        keeps casts from polluting the action history future casts draw
        from.

        Args:
            combat: The active CombatContext.
            actor: The combatant casting the echo (spends the charge and
                becomes the echo's owner).
            turns: Number of the actor's most recent actions the echo will
                replay, one per the actor's next ``turns`` turns (1-3,
                default 1). Cost is a flat ECHO_CAST_COST regardless of N.

        Returns:
            EchoCastResult describing the newly spawned echo, or
            CounterStopResult if an eligible opposing combatant countered
            the cast (Step 6).

        Raises:
            ValueError: If ``turns < 1`` or ``turns > MAX_ECHO_TURNS``, or
                if the configured ``CounterStopPolicy`` returns a combatant
                outside the eligible set (a policy programming error).
            InsufficientChargeError: If ``actor.temporal_charge <
                ECHO_CAST_COST``.
            EchoHistoryError: If the actor has fewer than ``turns``
                recorded actions to draw a source window from.
            EchoAlreadyActiveError: If the actor's side already has a live
                (non-expired, owner-alive) echo.
            EchoUnavailableError: If ``combat.is_over``.
        """
        # --- Validate (order matches STEP-5-PLAN.md §3 error table) ---
        if turns < 1 or turns > MAX_ECHO_TURNS:
            raise ValueError(f"turns must be between 1 and {MAX_ECHO_TURNS}, got {turns}")

        if actor.temporal_charge < ECHO_CAST_COST:
            raise InsufficientChargeError(
                f"Insufficient temporal charge: have {actor.temporal_charge}, need {ECHO_CAST_COST}"
            )

        history = combat._action_history.get(actor.id, deque())
        if len(history) < turns:
            raise EchoHistoryError(
                f"Not enough recorded actions for echo cast: have {len(history)}, need {turns}"
            )

        side = combat._side_of(actor)
        existing = combat._active_echoes.get(side)
        if existing is not None and self._is_echo_live(combat, existing):
            raise EchoAlreadyActiveError(f"A live echo is already active on side {side!r}")

        if combat.is_over:
            raise EchoUnavailableError("Cannot cast echo: combat is over")

        # --- Capture source window (last `turns` entries, chronological) ---
        source_actions = tuple(
            EchoSourceAction(
                source_turn=entry.source_turn,
                action_type=entry.action_type,
                target_id=entry.target_id,
                damage_dealt=entry.damage_dealt,
            )
            for entry in list(history)[-turns:]
        )

        turn_number = combat._total_turns

        # --- Emit CHARGE_SPENT, then deduct ---
        charge_event = self._event_builder.charge_spent(
            turn_number=turn_number,
            actor_id=actor.id,
            amount=ECHO_CAST_COST,
            ability="echo_cast",
        )
        self._event_store.append_event(charge_event)
        actor.spend_charge(ECHO_CAST_COST)

        # --- Offer the Counter-Stop response window ---
        counter_result = self._offer_counter_window(
            combat,
            caster=actor,
            ability="echo_cast",
            magnitude=turns,
            caster_charge_lost=ECHO_CAST_COST,
        )
        if counter_result is not None:
            return counter_result

        # --- Build Echo, register, emit ECHO_SPAWNED ---
        echo_id = f"echo_{actor.id}_t{turn_number}"
        echo = Echo(echo_id=echo_id, owner_id=actor.id, source_actions=source_actions)
        combat._active_echoes[side] = echo

        spawn_event = self._event_builder.echo_spawned(
            turn_number=turn_number,
            echo_id=echo_id,
            owner_id=actor.id,
            duration=turns,
            damage_scale=ECHO_DAMAGE_SCALE,
            source_actions=[
                {
                    "source_turn": sa.source_turn,
                    "action_type": sa.action_type,
                    "target_id": sa.target_id,
                    "damage_dealt": sa.damage_dealt,
                }
                for sa in source_actions
            ],
        )
        self._event_store.append_event(spawn_event)

        return EchoCastResult(
            echo_id=echo_id,
            owner_id=actor.id,
            duration=turns,
            charge_spent=ECHO_CAST_COST,
            source_turns=tuple(sa.source_turn for sa in source_actions),
        )

    def execute_echo_turn(self, combat: CombatContext, owner: Combatant) -> list[str]:
        """
        Advance the owner's side echo through one act, if one is due.

        Called by ``CombatContext`` after the owner's own action resolves
        (attack, defend, or flee) — never on the cast turn itself (locked
        semantic 5), and including the broken-enemy skip path (locked
        semantic 10: a stunned owner's echo still acts, since the echo is
        a temporal entity independent of its owner's present state).

        Dispatch per source action type (Phase 3 Step 5 locked semantics
        6-7): "attack" resolves a live target (retargeting to the first
        living enemy / the player if the original target has died) and
        deals ``max(1, floor(damage_dealt * ECHO_DAMAGE_SCALE))`` — zero
        new RNG draws; "defend" replays as a flavor no-op; "flee" (or an
        attack with no living target) replays as a fizzle. Every act emits
        exactly one ECHO_ACTED.

        Args:
            combat: The active CombatContext.
            owner: The combatant whose turn just resolved.

        Returns:
            List of log messages from the echo's act (empty if no echo is
            due to act this turn).
        """
        side = combat._side_of(owner)
        echo = combat._active_echoes.get(side)
        if echo is None or echo.owner_id != owner.id or echo.is_expired or combat.is_over:
            return []

        source_action = echo.source_actions[echo.next_index]
        echo.next_index += 1
        turn_number = combat._total_turns
        msgs: list[str] = []

        if source_action.action_type == "attack":
            target = self._resolve_echo_target(combat, owner, source_action.target_id)
            if target is None or source_action.damage_dealt is None:
                msgs.extend(
                    self._emit_echo_act(
                        combat,
                        echo,
                        owner,
                        "fizzle",
                        None,
                        None,
                        source_action.source_turn,
                        turn_number,
                    )
                )
            else:
                damage = max(1, math.floor(source_action.damage_dealt * ECHO_DAMAGE_SCALE))
                entity_result = target.take_damage(damage, DamageType.PHYSICAL)
                msgs.extend(
                    self._emit_echo_act(
                        combat,
                        echo,
                        owner,
                        "attack",
                        target.id,
                        damage,
                        source_action.source_turn,
                        turn_number,
                        target=target,
                    )
                )
                if isinstance(target, Enemy) and entity_result.shield_broken:
                    msgs.extend(combat._logger.log_shield_break(target))
                    self._event_store.append_event(
                        self._event_builder.shield_broken(
                            turn_number=turn_number,
                            combatant_id=target.id,
                            broke_by=owner.id,
                            damage_type=DamageType.PHYSICAL.name,
                        )
                    )
                if not target.is_alive:
                    msgs.extend(combat._logger.log_defeat(target))
                    self._event_store.append_event(
                        self._event_builder.combatant_defeated(
                            turn_number=turn_number,
                            combatant_id=target.id,
                            defeated_by=owner.id,
                            final_damage=damage,
                        )
                    )
        elif source_action.action_type == "defend":
            msgs.extend(
                self._emit_echo_act(
                    combat,
                    echo,
                    owner,
                    "defend",
                    None,
                    None,
                    source_action.source_turn,
                    turn_number,
                )
            )
        else:  # "flee" or any other unresolvable source action
            msgs.extend(
                self._emit_echo_act(
                    combat,
                    echo,
                    owner,
                    "fizzle",
                    None,
                    None,
                    source_action.source_turn,
                    turn_number,
                )
            )

        # Re-check via next_index directly (not `echo.is_expired`): mypy
        # narrows the early-return guard's `echo.is_expired` to Literal[False]
        # and doesn't see that the mutation above (`next_index += 1`)
        # invalidates it, so the property read alone is flagged unreachable.
        if echo.next_index >= len(echo.source_actions):
            del combat._active_echoes[side]

        return msgs

    def _emit_echo_act(
        self,
        combat: CombatContext,
        echo: Echo,
        owner: Combatant,
        action_type: str,
        target_id: str | None,
        damage_dealt: int | None,
        source_turn: int,
        turn_number: int,
        target: Combatant | None = None,
    ) -> list[str]:
        """
        Log and emit ECHO_ACTED for one echo act.

        Args:
            combat: The active CombatContext.
            echo: The acting echo.
            owner: The echo's owner (for log message formatting).
            action_type: "attack", "defend", or "fizzle".
            target_id: Resolved target ID (attack only), else None.
            damage_dealt: Scaled damage dealt (attack only), else None.
            source_turn: Turn number of the source action being replayed.
            turn_number: Current combat turn (the owner's just-executed turn).
            target: The struck combatant, for log formatting (attack only).

        Returns:
            List of log messages for this act.
        """
        msgs = combat._logger.log_echo_acted(owner, action_type, target, damage_dealt)
        self._event_store.append_event(
            self._event_builder.echo_acted(
                turn_number=turn_number,
                echo_id=echo.echo_id,
                owner_id=owner.id,
                action_type=action_type,
                target_id=target_id,
                damage_dealt=damage_dealt,
                source_turn=source_turn,
            )
        )
        return msgs

    def _resolve_echo_target(
        self,
        combat: CombatContext,
        owner: Combatant,
        original_target_id: str | None,
    ) -> Combatant | None:
        """
        Resolve the live target for an echo attack act.

        Prefers the original recorded target if it is still alive;
        otherwise retargets to the first living enemy (player-owned echo,
        list order — deterministic) or the player (enemy-owned echo).

        Args:
            combat: The active CombatContext.
            owner: The echo's owner.
            original_target_id: The target_id recorded on the source action.

        Returns:
            A living Combatant to strike, or None if no target is available
            (the caller falls through to a fizzle).
        """
        if original_target_id is not None:
            try:
                original = self._find_combatant(combat, original_target_id)
            except ValueError:
                original = None
            if original is not None and original.is_alive:
                return original

        if isinstance(owner, Player):
            living = combat.living_enemies
            return living[0] if living else None
        return combat.player if combat.player.is_alive else None

    def _is_echo_live(self, combat: CombatContext, echo: Echo) -> bool:
        """
        Whether an echo still occupies its side's single-echo slot.

        An echo is "live" unless it has replayed all its source actions
        (expired) or its owner is dead (inert — locked semantic 9). Both
        conditions free the side up for a new cast.

        Args:
            combat: The active CombatContext.
            echo: The echo to check.

        Returns:
            True if the echo still counts against the side cap.
        """
        if echo.is_expired:
            return False
        owner = self._find_combatant(combat, echo.owner_id)
        return owner.is_alive

    # -------------------------------------------------------------------------
    # Counter-Stop — implemented in Step 6
    # -------------------------------------------------------------------------

    def _offer_counter_window(
        self,
        combat: CombatContext,
        caster: Combatant,
        ability: str,
        magnitude: int,
        caster_charge_lost: int,
    ) -> CounterStopResult | None:
        """
        Offer the opposing side a chance to Counter-Stop an announced cast.

        Called by ``rewind()`` / ``echo_cast()`` after the caster has
        already committed (CHARGE_SPENT emitted and deducted) but before
        any further work happens — a countered cast leaves nothing else to
        undo (Phase 3 Step 6 locked semantic 5).

        Args:
            combat: The active CombatContext.
            caster: The combatant whose cast is being announced.
            ability: "rewind" or "echo_cast".
            magnitude: Turns rewound (rewind) or echo window N (echo_cast).
            caster_charge_lost: Charge the caster already spent on this
                cast — embedded in the result if countered.

        Returns:
            CounterStopResult if an eligible responder countered, else
            None (the cast proceeds).

        Raises:
            ValueError: If the configured ``CounterStopPolicy`` returns a
                combatant not present in the eligible list.
        """
        eligible = self._eligible_responders(combat, caster)
        if not eligible:
            # No eligible responder: the window is skipped entirely and the
            # policy is never called (locked semantic 7 — zero overhead on
            # the common path, and policies never see empty choices).
            return None

        turn_number = combat._total_turns
        announcement = TemporalAnnouncement(
            ability=ability,
            caster_id=caster.id,
            magnitude=magnitude,
            turn_number=turn_number,
        )
        responder = self._counter_policy.decide(combat, announcement, eligible)
        if responder is None:
            return None

        if not any(responder.id == candidate.id for candidate in eligible):
            raise ValueError(
                f"CounterStopPolicy returned a combatant not in the eligible list: {responder.id!r}"
            )

        # --- Emit responder CHARGE_SPENT, then deduct ---
        charge_event = self._event_builder.charge_spent(
            turn_number=turn_number,
            actor_id=responder.id,
            amount=COUNTER_STOP_COST,
            ability="counter_stop",
        )
        self._event_store.append_event(charge_event)
        responder.spend_charge(COUNTER_STOP_COST)

        # --- Emit COUNTER_STOP_TRIGGERED (persistent) ---
        trigger_event = self._event_builder.counter_stop_triggered(
            turn_number=turn_number,
            actor_id=responder.id,
            caster_id=caster.id,
            target_ability=ability,
        )
        self._event_store.append_event(trigger_event)

        combat._logger.log_counter_stop(responder, caster, ability)

        return CounterStopResult(
            countered_ability=ability,
            caster_id=caster.id,
            responder_id=responder.id,
            caster_charge_lost=caster_charge_lost,
            responder_charge_spent=COUNTER_STOP_COST,
            turn_number=turn_number,
        )

    def _eligible_responders(
        self,
        combat: CombatContext,
        caster: Combatant,
    ) -> list[Combatant]:
        """
        Build the deterministic list of combatants eligible to Counter-Stop.

        Eligible = living combatants on the *opposing* side with
        ``temporal_charge >= COUNTER_STOP_COST`` (locked semantic 7).
        Enemy side order is ``combat.living_enemies`` list order; the
        player side is just the player.

        Args:
            combat: The active CombatContext.
            caster: The combatant whose cast is being announced.

        Returns:
            Eligible responders in deterministic order (possibly empty).
        """
        if isinstance(caster, Player):
            candidates: list[Combatant] = list(combat.living_enemies)
        else:
            candidates = [combat.player] if combat.player.is_alive else []
        return [c for c in candidates if c.temporal_charge >= COUNTER_STOP_COST]

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
            builder_branch_id, active_echoes (copy of each Echo — Step 5),
            action_history (copy of each combatant's deque — Step 5).
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
            "active_echoes": {
                side: Echo(
                    echo_id=echo.echo_id,
                    owner_id=echo.owner_id,
                    source_actions=echo.source_actions,
                    next_index=echo.next_index,
                )
                for side, echo in combat._active_echoes.items()
            },
            "action_history": {
                combatant_id: list(history)
                for combatant_id, history in combat._action_history.items()
            },
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

        # 3b. Restore echo + action-history read-model state (Step 5)
        combat._active_echoes = snapshot["active_echoes"]
        restored_history: defaultdict[str, deque[EchoSourceAction]] = defaultdict(
            lambda: deque(maxlen=MAX_ECHO_TURNS)
        )
        for combatant_id, entries in snapshot["action_history"].items():
            restored_history[combatant_id] = deque(entries, maxlen=MAX_ECHO_TURNS)
        combat._action_history = restored_history

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

        # --- Reset echo + action-history read-model state (Step 5) ---
        combat._active_echoes = {}
        combat._action_history = defaultdict(lambda: deque(maxlen=MAX_ECHO_TURNS))

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
            # TURN_STARTED is the canonical per-turn marker emitted by the combat
            # loop. Reconstruct counters straight from the event: turn_number is
            # the running total-turn count, and round_number is recorded so replay
            # needs no turn-order arithmetic (turn_order is empty during replay).
            turn_number = data.get("turn_number", 0)
            combat._total_turns = turn_number
            if "round_number" in data:
                combat._round_number = data["round_number"]
            elif turn_number >= 1:
                # Legacy fallback for events emitted before round_number was
                # recorded (none exist in practice; kept for safety).
                turn_order_len = len(combat._turn_order) if combat._turn_order else 1
                if turn_number == 1 or (turn_number - 1) % turn_order_len == 0:
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

            # Rebuild the action-history read model (Step 5) — mirrors the
            # append CombatContext._execute_* makes on the live path, so
            # echoes cast on the post-rewind branch draw from a correct
            # source window.
            combat._action_history[actor_id].append(
                EchoSourceAction(
                    source_turn=data.get("turn_number", 0),
                    action_type=action_type,
                    target_id=target_id,
                    damage_dealt=damage_dealt,
                )
            )

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

        elif etype == EventTypes.ECHO_SPAWNED:
            echo_id = data.get("echo_id", "")
            owner_id = data.get("owner_id", "")
            source_actions = tuple(
                EchoSourceAction(
                    source_turn=sa.get("source_turn", 0),
                    action_type=sa.get("action_type", ""),
                    target_id=sa.get("target_id"),
                    damage_dealt=sa.get("damage_dealt"),
                )
                for sa in data.get("source_actions", [])
            )
            owner = self._find_combatant(combat, owner_id)
            side = combat._side_of(owner)

            existing = combat._active_echoes.get(side)
            assert existing is None or existing.is_expired, (
                f"Echo replay invariant violated: side {side!r} already has a "
                f"live echo when replaying ECHO_SPAWNED for {echo_id!r}"
            )

            combat._active_echoes[side] = Echo(
                echo_id=echo_id, owner_id=owner_id, source_actions=source_actions
            )

        elif etype == EventTypes.ECHO_ACTED:
            echo_id = data.get("echo_id", "")
            owner_id = data.get("owner_id", "")
            action_type = data.get("action_type", "")
            target_id = data.get("target_id")
            damage_dealt = data.get("damage_dealt")

            owner = self._find_combatant(combat, owner_id)
            side = combat._side_of(owner)
            echo = combat._active_echoes.get(side)

            if echo is not None and echo.echo_id == echo_id:
                source_action = echo.source_actions[echo.next_index]
                echo.next_index += 1

                if action_type == "attack" and target_id is not None and damage_dealt is not None:
                    assert source_action.damage_dealt is not None, (
                        f"Echo replay determinism failure: recorded attack act for "
                        f"{echo_id!r} has no source damage to recompute from"
                    )
                    expected_damage = max(
                        1, math.floor(source_action.damage_dealt * ECHO_DAMAGE_SCALE)
                    )
                    assert expected_damage == damage_dealt, (
                        f"Echo replay determinism failure: recomputed damage "
                        f"{expected_damage} != recorded {damage_dealt} for echo {echo_id!r}"
                    )
                    target = self._find_combatant(combat, target_id)
                    target.take_damage(damage_dealt, DamageType.PHYSICAL)

                if echo.is_expired:
                    del combat._active_echoes[side]

        # ECHO_STONE_USED: pre-Phase-3 event type, unused, untouched.

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
