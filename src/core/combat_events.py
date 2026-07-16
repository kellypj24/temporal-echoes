"""
Combat event builder for structured event creation.

This module provides helper classes to build combat events with correct
schemas and validation. All combat events follow the event sourcing pattern
and integrate with Phase 1's EventStore.
"""

import json
from dataclasses import dataclass
from typing import Any

from .events import EventTypes, GameEvent


@dataclass
class CombatEventBuilder:
    """
    Builder for combat events with schema validation.

    Helps create properly structured combat events that integrate with
    Phase 1's event store. All events use the combat_id as aggregate_id
    for easy querying of complete combat sequences.

    The builder is mutable so that ``set_branch`` can update the active
    branch_id after a rewind without replacing the builder instance.
    Branch 0 is the original timeline; each rewind in a combat increments
    the branch (see Phase 3 Step 3 for full branch propagation).

    Attributes:
        session_id: Current game session identifier
        timeline_id: Current timeline branch identifier
        combat_id: Unique identifier for this combat encounter
        branch_id: Current rewind branch (0 = original line)

    Example:
        >>> builder = CombatEventBuilder(
        ...     session_id="sess_001",
        ...     timeline_id="main",
        ...     combat_id="combat_001"
        ... )
        >>> event = builder.combat_started(
        ...     rng_seed=42,
        ...     player={"id": "player_1", "hp": 300},
        ...     enemies=[{"id": "enemy_1", "hp": 200}]
        ... )
    """

    session_id: str
    timeline_id: str
    combat_id: str
    branch_id: int = 0

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.timeline_id:
            raise ValueError("timeline_id is required")
        if not self.combat_id:
            raise ValueError("combat_id is required")

    def set_branch(self, branch_id: int) -> None:
        """
        Update the active rewind branch for subsequent event emissions.

        Called by ``CombatContext.rewind_to_turn()`` after a rewind to
        ensure all post-rewind events carry the new branch identifier.
        The builder instance is reused (not replaced) so that existing
        references to it remain valid.

        Args:
            branch_id: New branch identifier (must be ≥ 0)

        Raises:
            ValueError: If branch_id is negative
        """
        if branch_id < 0:
            raise ValueError(f"branch_id cannot be negative, got {branch_id}")
        self.branch_id = branch_id

    def combat_started(
        self,
        rng_seed: int,
        player: dict,
        enemies: list[dict],
        location: str | None = None,
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create CombatStarted event with all initial combatant data.

        This event marks the beginning of combat and includes all initial
        state needed for deterministic replay.

        Args:
            rng_seed: RNG seed for deterministic combat
            player: Player data (id, name, hp, max_hp, stats, boost_points)
            enemies: List of enemy data (id, name, hp, max_hp, stats, shields, weaknesses)
            location: Optional location where combat started
            **kwargs: Additional optional fields (combat_type, etc.)

        Returns:
            GameEvent with CombatStarted type

        Example:
            >>> event = builder.combat_started(
            ...     rng_seed=42,
            ...     player={"id": "p1", "name": "Hero", "hp": 300, "boost_points": 0},
            ...     enemies=[{"id": "e1", "name": "Goblin", "hp": 200}],
            ...     location="Forest Path"
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "rng_seed": rng_seed,
            "player": player,
            "enemies": enemies,
        }

        if location:
            event_data["location"] = location

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.COMBAT_STARTED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def combat_ended(
        self,
        outcome: str,
        victory: bool,
        total_turns: int,
        duration_ms: float | None = None,
        rewards: dict | None = None,
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create CombatEnded event with combat outcome.

        Args:
            outcome: Outcome description ("victory", "defeat", "fled")
            victory: Whether player won
            total_turns: Number of turns in combat
            duration_ms: Combat duration in milliseconds (optional)
            rewards: Rewards earned (exp, gold, items) (optional)
            **kwargs: Additional fields

        Returns:
            GameEvent with CombatEnded type

        Example:
            >>> event = builder.combat_ended(
            ...     outcome="victory",
            ...     victory=True,
            ...     total_turns=12,
            ...     rewards={"exp": 150, "gold": 50}
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "outcome": outcome,
            "victory": victory,
            "total_turns": total_turns,
        }

        if duration_ms is not None:
            event_data["duration_ms"] = duration_ms

        if rewards:
            event_data["rewards"] = rewards

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.COMBAT_ENDED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def turn_started(self, turn_number: int, active_combatant_id: str, **kwargs: Any) -> GameEvent:
        """
        Create TurnStarted event.

        Args:
            turn_number: Current turn number (1-indexed)
            active_combatant_id: ID of combatant whose turn it is
            **kwargs: Additional fields (turn_order, etc.)

        Returns:
            GameEvent with TurnStarted type

        Example:
            >>> event = builder.turn_started(
            ...     turn_number=1,
            ...     active_combatant_id="player_1"
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "active_combatant_id": active_combatant_id,
        }

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.TURN_STARTED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def action_executed(
        self,
        turn_number: int,
        actor_id: str,
        action_type: str,
        target_id: str | None = None,
        damage_dealt: int | None = None,
        healing_done: int | None = None,
        boost_points_spent: int | None = None,
        was_critical: bool = False,
        was_weakness: bool = False,
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create ActionExecuted event (composite event with all action details).

        This is a composite event containing all action details including
        damage, multipliers, and effects. Per DEC-2004, we use composite
        events to simplify event replay.

        Args:
            turn_number: Current turn number
            actor_id: ID of combatant performing action
            action_type: Type of action ("attack", "defend", "item", "ability", "flee")
            target_id: ID of target combatant (if applicable)
            damage_dealt: Damage amount (if applicable)
            healing_done: Healing amount (if applicable)
            boost_points_spent: BP spent on this action
            was_critical: Whether attack was critical
            was_weakness: Whether attack hit weakness
            **kwargs: Additional fields (multipliers, effects, skill_name, etc.)

        Returns:
            GameEvent with ActionExecuted type

        Example:
            >>> event = builder.action_executed(
            ...     turn_number=1,
            ...     actor_id="player_1",
            ...     action_type="attack",
            ...     target_id="enemy_1",
            ...     damage_dealt=75,
            ...     boost_points_spent=2,
            ...     was_critical=False,
            ...     was_weakness=True
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "actor_id": actor_id,
            "action_type": action_type,
        }

        if target_id is not None:
            event_data["target_id"] = target_id

        if damage_dealt is not None:
            event_data["damage_dealt"] = damage_dealt

        if healing_done is not None:
            event_data["healing_done"] = healing_done

        if boost_points_spent is not None:
            event_data["boost_points_spent"] = boost_points_spent

        if was_critical or was_weakness:
            event_data["was_critical"] = was_critical
            event_data["was_weakness"] = was_weakness

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.ACTION_EXECUTED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def shield_broken(
        self,
        turn_number: int,
        combatant_id: str,
        broke_by: str,
        damage_type: str,
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create ShieldBroken event.

        Args:
            turn_number: Turn when shield broke
            combatant_id: ID of combatant whose shield broke
            broke_by: ID of combatant who broke the shield
            damage_type: Type of damage that broke shield
            **kwargs: Additional fields (shield_points_remaining, etc.)

        Returns:
            GameEvent with ShieldBroken type

        Example:
            >>> event = builder.shield_broken(
            ...     turn_number=3,
            ...     combatant_id="enemy_1",
            ...     broke_by="player_1",
            ...     damage_type="FIRE"
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "combatant_id": combatant_id,
            "broke_by": broke_by,
            "damage_type": damage_type,
        }

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.SHIELD_BROKEN,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def boost_point_gained(
        self, turn_number: int, combatant_id: str, new_total: int, **kwargs: Any
    ) -> GameEvent:
        """
        Create BoostPointGained event.

        Args:
            turn_number: Turn when BP was gained
            combatant_id: ID of combatant who gained BP
            new_total: New BP total after gain
            **kwargs: Additional fields (amount_gained, etc.)

        Returns:
            GameEvent with BoostPointGained type

        Example:
            >>> event = builder.boost_point_gained(
            ...     turn_number=2,
            ...     combatant_id="player_1",
            ...     new_total=3,
            ...     amount_gained=1
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "combatant_id": combatant_id,
            "new_total": new_total,
        }

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.BOOST_POINT_GAINED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def combatant_defeated(
        self,
        turn_number: int,
        combatant_id: str,
        defeated_by: str,
        final_damage: int,
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create CombatantDefeated event.

        Args:
            turn_number: Turn when defeat occurred
            combatant_id: ID of defeated combatant
            defeated_by: ID of combatant who dealt final blow
            final_damage: Damage from final blow
            **kwargs: Additional fields (total_damage_taken, etc.)

        Returns:
            GameEvent with CombatantDefeated type

        Example:
            >>> event = builder.combatant_defeated(
            ...     turn_number=8,
            ...     combatant_id="enemy_1",
            ...     defeated_by="player_1",
            ...     final_damage=45
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "combatant_id": combatant_id,
            "defeated_by": defeated_by,
            "final_damage": final_damage,
        }

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.COMBATANT_DEFEATED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def combat_fled(
        self, turn_number: int, flee_success: bool, fled_by: str, **kwargs: Any
    ) -> GameEvent:
        """
        Create CombatFled event.

        Args:
            turn_number: Turn when flee was attempted
            flee_success: Whether flee succeeded
            fled_by: ID of combatant who attempted to flee
            **kwargs: Additional fields (flee_chance, etc.)

        Returns:
            GameEvent with CombatFled type

        Example:
            >>> event = builder.combat_fled(
            ...     turn_number=5,
            ...     flee_success=True,
            ...     fled_by="player_1"
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "flee_success": flee_success,
            "fled_by": fled_by,
        }

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.COMBAT_FLED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def charge_spent(
        self,
        turn_number: int,
        actor_id: str,
        amount: int,
        ability: str,
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create ChargeSpent event for temporal ability activation.

        Emitted before the charge is deducted from the actor so that
        the event carries the "intent to spend" at the pre-spend turn
        position. The actor's ``spend_charge`` call follows immediately.

        Args:
            turn_number: Turn number at which the ability is activated
            actor_id: ID of the combatant spending charge
            amount: Number of temporal charges spent
            ability: Name of the ability being activated (e.g. "rewind")
            **kwargs: Additional context fields

        Returns:
            GameEvent with ChargeSpent type

        Example:
            >>> event = builder.charge_spent(
            ...     turn_number=3,
            ...     actor_id="player_1",
            ...     amount=1,
            ...     ability="rewind"
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "actor_id": actor_id,
            "amount": amount,
            "ability": ability,
        }

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.CHARGE_SPENT,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def charge_regenerated(
        self,
        turn_number: int,
        actor_id: str,
        amount: int,
        new_total: int,
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create ChargeRegenerated event for per-round charge recovery.

        Emitted only when at least 1 charge is actually gained (i.e. when
        the combatant is not already at ``max_temporal_charge``). The caller
        is responsible for checking the actual gained amount before emitting.

        Args:
            turn_number: Turn number at the time of regeneration
            actor_id: ID of the combatant gaining charge
            amount: Actual charge gained (may be less than requested if capped)
            new_total: Combatant's temporal_charge after the gain
            **kwargs: Additional context fields

        Returns:
            GameEvent with ChargeRegenerated type

        Example:
            >>> event = builder.charge_regenerated(
            ...     turn_number=0,
            ...     actor_id="player_1",
            ...     amount=1,
            ...     new_total=1
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "actor_id": actor_id,
            "amount": amount,
            "new_total": new_total,
        }

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.CHARGE_REGENERATED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def temporal_rewind(
        self,
        turn_number: int,
        actor_id: str,
        from_turn: int,
        to_turn: int,
        branch_id: int,
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create TemporalRewind event marking a successful rewind.

        Emitted *after* replay succeeds and the new branch is live in memory.
        The ``branch_id`` argument is the freshly allocated branch (one higher
        than the pre-rewind branch); the event is stamped with that same
        branch_id so post-rewind queries against the active branch chain
        surface the rewind boundary.

        Args:
            turn_number: Turn position after rewind (i.e. ``to_turn``).
            actor_id: ID of the combatant who triggered the rewind.
            from_turn: Turn number combat was at before rewind.
            to_turn: Turn number combat resumed at.
            branch_id: Newly allocated branch identifier.
            **kwargs: Additional context fields.

        Returns:
            GameEvent with TemporalRewind type, stamped with the new branch_id.
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "actor_id": actor_id,
            "from_turn": from_turn,
            "to_turn": to_turn,
            "branch_id": branch_id,
        }

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.TEMPORAL_REWIND,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=branch_id,
            event_data=json.dumps(event_data),
        )

    def echo_spawned(
        self,
        turn_number: int,
        echo_id: str,
        owner_id: str,
        duration: int,
        damage_scale: float,
        source_actions: list[dict],
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create EchoSpawned event marking a successful Echo Cast.

        The owner's source action window is embedded directly in the
        payload so rewind replay can reconstruct the Echo from this one
        event, with no query against prior ACTION_EXECUTED rows (see
        Phase 3 Step 5 plan §3 — that query problem is exactly what Step 4
        deferred; embedding sidesteps it entirely).

        Args:
            turn_number: Turn number at which the echo was cast.
            echo_id: Deterministic echo identifier
                (``f"echo_{owner_id}_t{cast_turn}"``, no UUIDs).
            owner_id: ID of the combatant who cast the echo.
            duration: Number of turns the echo will act (1-3).
            damage_scale: Fraction of recorded damage the echo deals (0.5).
            source_actions: Embedded source window, chronological order
                (most recent last). Each entry is a dict with keys
                source_turn, action_type, target_id, damage_dealt.
            **kwargs: Additional context fields.

        Returns:
            GameEvent with EchoSpawned type.

        Example:
            >>> event = builder.echo_spawned(
            ...     turn_number=5,
            ...     echo_id="echo_player_1_t5",
            ...     owner_id="player_1",
            ...     duration=2,
            ...     damage_scale=0.5,
            ...     source_actions=[
            ...         {"source_turn": 3, "action_type": "attack",
            ...          "target_id": "enemy_1", "damage_dealt": 40},
            ...     ],
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "echo_id": echo_id,
            "owner_id": owner_id,
            "duration": duration,
            "damage_scale": damage_scale,
            "source_actions": source_actions,
        }

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.ECHO_SPAWNED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def echo_acted(
        self,
        turn_number: int,
        echo_id: str,
        owner_id: str,
        action_type: str,
        target_id: str | None,
        damage_dealt: int | None,
        source_turn: int,
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create EchoActed event for one act of a live echo.

        Args:
            turn_number: Turn number at which the echo acted (the owner's
                just-executed turn).
            echo_id: The acting echo's identifier.
            owner_id: ID of the echo's owner.
            action_type: "attack", "defend", or "fizzle".
            target_id: Resolved target ID (attack only — retargeting, if
                any, has already been applied), else None.
            damage_dealt: Scaled damage dealt (attack only), else None.
            source_turn: Turn number of the source action being replayed.
            **kwargs: Additional context fields.

        Returns:
            GameEvent with EchoActed type.

        Example:
            >>> event = builder.echo_acted(
            ...     turn_number=6,
            ...     echo_id="echo_player_1_t5",
            ...     owner_id="player_1",
            ...     action_type="attack",
            ...     target_id="enemy_1",
            ...     damage_dealt=20,
            ...     source_turn=3,
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "echo_id": echo_id,
            "owner_id": owner_id,
            "action_type": action_type,
            "source_turn": source_turn,
        }

        if target_id is not None:
            event_data["target_id"] = target_id

        if damage_dealt is not None:
            event_data["damage_dealt"] = damage_dealt

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.ECHO_ACTED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )

    def counter_stop_triggered(
        self,
        turn_number: int,
        actor_id: str,
        caster_id: str,
        target_ability: str,
        **kwargs: Any,
    ) -> GameEvent:
        """
        Create CounterStopTriggered event marking a successful counter.

        Persistent (not rewindable — see ``events.is_rewindable``): the act
        of countering is a historical fact that survives any later rewind,
        same standing as TemporalRewind. It lands at the current turn and
        branch — no branch bump of its own, unlike a successful rewind.

        Args:
            turn_number: Turn number the counter landed on.
            actor_id: ID of the responding combatant (who countered).
            caster_id: ID of the combatant whose cast was countered.
            target_ability: The countered ability — "rewind" or "echo_cast".
            **kwargs: Additional context fields.

        Returns:
            GameEvent with CounterStopTriggered type.

        Example:
            >>> event = builder.counter_stop_triggered(
            ...     turn_number=5,
            ...     actor_id="enemy_1",
            ...     caster_id="player_1",
            ...     target_ability="rewind",
            ... )
        """
        event_data = {
            "combat_id": self.combat_id,
            "turn_number": turn_number,
            "actor_id": actor_id,
            "caster_id": caster_id,
            "target_ability": target_ability,
        }

        event_data.update(kwargs)

        return GameEvent(
            event_type=EventTypes.COUNTER_STOP_TRIGGERED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            branch_id=self.branch_id,
            event_data=json.dumps(event_data),
        )
