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

from src.core.combat_events import CombatEventBuilder
from src.core.persistence import EventStore
from src.entities.combatant import Combatant


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
    # Stubs — implemented in later steps
    # -------------------------------------------------------------------------

    def rewind(self, *args: object, **kwargs: object) -> object:
        """
        Rewind combat to a prior turn on a new branch.

        Not yet implemented. Full single-turn rewind (including branch_id
        allocation, event replay, and state rebuild) lands in Phase 3 Step 3.

        Raises:
            NotImplementedError: Always — implementation pending Step 3.
        """
        raise NotImplementedError("Phase 3 Step 3")

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
