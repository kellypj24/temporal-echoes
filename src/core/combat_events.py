"""
Combat event builder for structured event creation.

This module provides helper classes to build combat events with correct
schemas and validation. All combat events follow the event sourcing pattern
and integrate with Phase 1's EventStore.
"""

import json
from dataclasses import dataclass

from .events import EventTypes, GameEvent


@dataclass
class CombatEventBuilder:
    """
    Builder for combat events with schema validation.

    Helps create properly structured combat events that integrate with
    Phase 1's event store. All events use the combat_id as aggregate_id
    for easy querying of complete combat sequences.

    Attributes:
        session_id: Current game session identifier
        timeline_id: Current timeline branch identifier
        combat_id: Unique identifier for this combat encounter

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

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.timeline_id:
            raise ValueError("timeline_id is required")
        if not self.combat_id:
            raise ValueError("combat_id is required")

    def combat_started(
        self,
        rng_seed: int,
        player: dict,
        enemies: list[dict],
        location: str | None = None,
        **kwargs,
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
            event_data=json.dumps(event_data),
        )

    def combat_ended(
        self,
        outcome: str,
        victory: bool,
        total_turns: int,
        duration_ms: float | None = None,
        rewards: dict | None = None,
        **kwargs,
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
            event_data=json.dumps(event_data),
        )

    def turn_started(
        self, turn_number: int, active_combatant_id: str, **kwargs
    ) -> GameEvent:
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
        **kwargs,
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
            event_data=json.dumps(event_data),
        )

    def shield_broken(
        self,
        turn_number: int,
        combatant_id: str,
        broke_by: str,
        damage_type: str,
        **kwargs,
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
            event_data=json.dumps(event_data),
        )

    def boost_point_gained(
        self, turn_number: int, combatant_id: str, new_total: int, **kwargs
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
            event_data=json.dumps(event_data),
        )

    def combatant_defeated(
        self,
        turn_number: int,
        combatant_id: str,
        defeated_by: str,
        final_damage: int,
        **kwargs,
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
            event_data=json.dumps(event_data),
        )

    def combat_fled(
        self, turn_number: int, flee_success: bool, fled_by: str, **kwargs
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
            event_data=json.dumps(event_data),
        )
