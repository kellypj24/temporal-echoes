"""
Combat manager that orchestrates full combat flow.

This module wires together all combat subsystems (entities, damage calc,
events, enemy AI) into a CombatContext that manages internal combat phases.
The game transitions to GameState.COMBAT, then CombatContext manages its
own phases internally — keeping the top-level state machine clean.

Related Decisions: DEC-2001 through DEC-2006
"""

from __future__ import annotations

import random
from enum import Enum, auto

from src.core.ai import AIArchetype, CombatAction, CombatState, EnemyAI, create_enemy_ai
from src.core.combat_events import CombatEventBuilder
from src.core.combat_logger import CombatLogger
from src.core.damage import DamageCalculator
from src.core.events import GameEvent
from src.core.persistence import EventStore
from src.core.temporal import RewindResult, TemporalSystem
from src.entities import Combatant, DamageType, Enemy, Player


class CombatPhase(Enum):
    """Internal phases for combat flow management."""

    INITIALIZING = auto()
    ROUND_START = auto()
    AWAITING_PLAYER_INPUT = auto()
    EXECUTING_TURN = auto()
    ROUND_END = auto()
    COMBAT_OVER = auto()


class CombatOutcome(Enum):
    """Possible outcomes when combat ends."""

    VICTORY = auto()
    DEFEAT = auto()
    FLED = auto()


# Map archetype string names to AIArchetype enum
_ARCHETYPE_MAP: dict[str, AIArchetype] = {
    "aggressive": AIArchetype.AGGRESSIVE,
    "defensive": AIArchetype.DEFENSIVE,
    "tactical": AIArchetype.TACTICAL,
    "berserker": AIArchetype.BERSERKER,
}

# Base flee chance percentage
_BASE_FLEE_CHANCE = 50


class CombatContext:
    """
    Orchestrates full combat flow by integrating all combat subsystems.

    Manages internal combat phases (INITIALIZING -> ROUND_START ->
    AWAITING_PLAYER_INPUT / EXECUTING_TURN -> ROUND_END -> COMBAT_OVER)
    without modifying the top-level GameStateMachine.

    Turn flow:
        start_round() -> for each combatant in speed order:
            if player -> submit_player_action()
            if enemy -> execute_enemy_turn()
        -> advance_turn() -> repeat until combat ends.

    Attributes:
        combat_id: Unique identifier for this combat encounter.
        player: The player combatant.
        enemies: List of enemy combatants.
        event_store: Persistence layer for combat events.
        logger: Text formatter for combat messages.
        temporal_system: Read-only access to the TemporalSystem for tests and
            external callers; construction is internal (DI-via-constructor of
            subsystems is acceptable when both arguments are already injected).
    """

    def __init__(
        self,
        combat_id: str,
        seed: int,
        player: Player,
        enemies: list[Enemy],
        event_store: EventStore,
        session_id: str,
        timeline_id: str,
    ) -> None:
        """
        Initialize combat context and emit COMBAT_STARTED event.

        Args:
            combat_id: Unique identifier for this combat encounter.
            seed: RNG seed for deterministic replay.
            player: The player combatant.
            enemies: List of enemy combatants.
            event_store: Persistence layer for combat events.
            session_id: Current game session identifier.
            timeline_id: Current timeline branch identifier.

        Raises:
            ValueError: If combat_id, session_id, or timeline_id is empty,
                or if enemies list is empty.
        """
        if not combat_id:
            raise ValueError("combat_id is required")
        if not session_id:
            raise ValueError("session_id is required")
        if not timeline_id:
            raise ValueError("timeline_id is required")
        if not enemies:
            raise ValueError("At least one enemy is required")

        self.combat_id = combat_id
        self._seed = seed
        self.player = player
        self.enemies = list(enemies)
        self._event_store = event_store
        self._session_id = session_id
        self._timeline_id = timeline_id

        # Initialize subsystems
        self._rng = random.Random(seed)
        self._damage_calc = DamageCalculator(rng_seed=self._rng.randint(0, 2**31))
        self._event_builder = CombatEventBuilder(
            session_id=session_id,
            timeline_id=timeline_id,
            combat_id=combat_id,
        )
        self._logger = CombatLogger()

        # Initialize enemy AIs
        self._enemy_ais: dict[str, EnemyAI] = {}
        for enemy in self.enemies:
            archetype = _ARCHETYPE_MAP.get(enemy.archetype, AIArchetype.AGGRESSIVE)
            ai_rng = random.Random(self._rng.randint(0, 2**31))
            self._enemy_ais[enemy.id] = create_enemy_ai(enemy, archetype, ai_rng)

        # Temporal system (constructed here from already-injected subsystems)
        self._temporal = TemporalSystem(
            event_store=event_store,
            event_builder=self._event_builder,
        )

        # Combat-local rewind branch (0 = original line, increments per rewind)
        self._current_branch_id: int = 0

        # Combat state
        self._phase = CombatPhase.INITIALIZING
        self._outcome: CombatOutcome | None = None
        self._round_number = 0
        self._turn_order: list[Combatant] = []
        self._turn_index = 0
        self._total_turns = 0

        # Emit combat started event
        self._emit_event(
            self._event_builder.combat_started(
                rng_seed=seed,
                player={
                    "id": player.id,
                    "name": player.name,
                    "hp": player.hp,
                    "max_hp": player.max_hp,
                    "attack": player.attack,
                    "defense": player.defense,
                    "speed": player.speed,
                    "boost_points": player.boost_points,
                },
                enemies=[
                    {
                        "id": e.id,
                        "name": e.name,
                        "hp": e.hp,
                        "max_hp": e.max_hp,
                        "attack": e.attack,
                        "defense": e.defense,
                        "speed": e.speed,
                        "shield_points": e.shield_points,
                        "max_shield_points": e.max_shield_points,
                        "weaknesses": [w.name for w in e.weaknesses],
                        "archetype": e.archetype,
                    }
                    for e in enemies
                ],
            )
        )

        # Log combat start
        self._logger.log_combat_start(player, enemies)

    # --- Properties ---

    @property
    def phase(self) -> CombatPhase:
        """Return the current combat phase."""
        return self._phase

    @property
    def is_over(self) -> bool:
        """Return True if combat has ended."""
        return self._phase == CombatPhase.COMBAT_OVER

    @property
    def outcome(self) -> CombatOutcome | None:
        """Return the combat outcome, or None if still in progress."""
        return self._outcome

    @property
    def current_combatant(self) -> Combatant:
        """
        Return the combatant whose turn it currently is.

        Raises:
            IndexError: If turn_index is out of range.
        """
        return self._turn_order[self._turn_index]

    @property
    def living_enemies(self) -> list[Enemy]:
        """Return list of enemies that are still alive."""
        return [e for e in self.enemies if e.is_alive]

    @property
    def round_number(self) -> int:
        """Return the current round number."""
        return self._round_number

    @property
    def log_messages(self) -> list[str]:
        """Return all accumulated combat log messages."""
        return self._logger.messages

    @property
    def temporal_system(self) -> TemporalSystem:
        """
        Read-only access to the TemporalSystem for tests and external callers.

        Returns:
            The TemporalSystem instance owned by this CombatContext.
        """
        return self._temporal

    # --- Core Flow ---

    def start_round(self) -> list[str]:
        """
        Start a new combat round.

        Calculates turn order based on speed, grants player 1 BP,
        emits relevant events, and transitions to the first combatant's turn.

        Returns:
            List of log messages for this round start.

        Raises:
            RuntimeError: If called when combat is over.
        """
        if self._phase == CombatPhase.COMBAT_OVER:
            raise RuntimeError("Cannot start round: combat is over")

        self._round_number += 1
        self._phase = CombatPhase.ROUND_START

        # Calculate turn order
        self._turn_order = self._calculate_turn_order()
        self._turn_index = 0

        msgs: list[str] = []

        # Log round start
        msgs.extend(self._logger.log_round_start(self._round_number, self._turn_order))

        # Grant player 1 BP at round start
        actual_gained = self.player.gain_bp(1)
        msgs.extend(self._logger.log_bp_gain(self.player, actual_gained))

        # Emit BP gained event
        self._emit_event(
            self._event_builder.boost_point_gained(
                turn_number=self._total_turns,
                combatant_id=self.player.id,
                new_total=self.player.boost_points,
                amount_gained=actual_gained,
            )
        )

        # Regenerate 1 temporal charge for player and each living enemy.
        # regenerate() emits CHARGE_REGENERATED only when charge is actually gained.
        self._temporal.regenerate(
            actor=self.player,
            amount=1,
            turn_number=self._total_turns,
        )
        for enemy in self.living_enemies:
            self._temporal.regenerate(
                actor=enemy,
                amount=1,
                turn_number=self._total_turns,
            )

        # Set phase based on first combatant
        self._set_phase_for_current_combatant()

        return msgs

    def get_enemy_action(self, enemy: Enemy) -> CombatAction:
        """
        Get AI decision for an enemy.

        Args:
            enemy: The enemy combatant to get an action for.

        Returns:
            CombatAction selected by the enemy's AI.

        Raises:
            ValueError: If enemy has no registered AI.
        """
        ai = self._enemy_ais.get(enemy.id)
        if ai is None:
            raise ValueError(f"No AI registered for enemy {enemy.id}")

        combat_state = CombatState(
            player=self.player,
            enemies=self.living_enemies,
            round_number=self._round_number,
        )
        return ai.select_action(combat_state)

    def submit_player_action(self, action: CombatAction) -> list[str]:
        """
        Submit and execute the player's action.

        Args:
            action: The player's chosen combat action.

        Returns:
            List of log messages from executing the action.

        Raises:
            RuntimeError: If not awaiting player input.
            ValueError: If action_type is invalid.
        """
        if self._phase != CombatPhase.AWAITING_PLAYER_INPUT:
            raise RuntimeError(f"Cannot submit player action in phase {self._phase.name}")

        self._phase = CombatPhase.EXECUTING_TURN
        self._total_turns += 1
        msgs: list[str] = []

        if action.action_type == "attack":
            target = self._find_combatant(action.target_id)
            msgs.extend(self._execute_attack(self.player, target, action))
        elif action.action_type == "defend":
            msgs.extend(self._execute_defend(self.player))
        elif action.action_type == "flee":
            msgs.extend(self._execute_flee(self.player))
        else:
            raise ValueError(f"Unknown action type: {action.action_type}")

        return msgs

    def execute_enemy_turn(self, enemy: Enemy) -> list[str]:
        """
        Execute an enemy's turn (get AI action and execute it).

        Broken enemies skip their turn.

        Args:
            enemy: The enemy whose turn it is.

        Returns:
            List of log messages from the turn.
        """
        self._phase = CombatPhase.EXECUTING_TURN
        self._total_turns += 1
        msgs: list[str] = []

        # Broken enemies skip their turn
        if enemy.is_broken:
            msgs.append(f"{enemy.name} is stunned and cannot act!")
            self._logger._messages.append(f"{enemy.name} is stunned and cannot act!")
            return msgs

        action = self.get_enemy_action(enemy)

        if action.action_type == "attack":
            msgs.extend(self._execute_attack(enemy, self.player, action))
        elif action.action_type == "defend":
            msgs.extend(self._execute_defend(enemy))
        elif action.action_type == "ability":
            # Abilities act as attacks for now
            msgs.extend(self._execute_attack(enemy, self.player, action))
        else:
            msgs.extend(self._execute_defend(enemy))

        return msgs

    def advance_turn(self) -> list[str]:
        """
        Advance to the next combatant's turn or end the round.

        Processes turn-end effects (break recovery) for the current combatant,
        checks combat end conditions, then moves to the next combatant.

        Returns:
            List of log messages from turn-end processing.
        """
        msgs: list[str] = []

        # Process turn-end effects for current combatant
        current = self._turn_order[self._turn_index]
        if isinstance(current, Enemy) and current.is_alive:
            recovery_msg = current.process_turn_end()
            if recovery_msg:
                msgs.append(recovery_msg)
                self._logger._messages.append(recovery_msg)

        # Check combat end conditions
        if self._check_combat_end():
            return msgs

        # Move to next combatant
        self._turn_index += 1

        # If we've gone through all combatants, round is over
        if self._turn_index >= len(self._turn_order):
            self._phase = CombatPhase.ROUND_END
            return msgs

        # Skip dead combatants
        while self._turn_index < len(self._turn_order):
            combatant = self._turn_order[self._turn_index]
            if combatant.is_alive:
                break
            self._turn_index += 1

        # Check if round is over after skipping dead combatants
        if self._turn_index >= len(self._turn_order):
            self._phase = CombatPhase.ROUND_END
            return msgs

        # Set phase for next combatant
        self._set_phase_for_current_combatant()

        return msgs

    # --- Action Execution (Private) ---

    def _execute_attack(
        self,
        actor: Combatant,
        target: Combatant,
        action: CombatAction,
    ) -> list[str]:
        """
        Execute an attack action.

        Args:
            actor: The attacking combatant.
            target: The target combatant.
            action: The combat action with boost points.

        Returns:
            List of log messages.
        """
        msgs: list[str] = []
        bp_spent = action.boost_points

        # Player spends BP if applicable
        if isinstance(actor, Player) and bp_spent > 0:
            actor.spend_bp(bp_spent)

        # Determine damage type (PHYSICAL for basic attacks)
        damage_type = DamageType.PHYSICAL

        # Get defender properties for damage calc
        defender_weaknesses: list[DamageType] = []
        defender_is_broken = False
        if isinstance(target, Enemy):
            defender_weaknesses = target.weaknesses
            defender_is_broken = target.is_broken

        # Calculate damage
        damage_result = self._damage_calc.calculate(
            attacker_atk=actor.attack,
            defender_def=target.defense,
            boost_points=bp_spent,
            damage_type=damage_type,
            defender_weaknesses=defender_weaknesses,
            defender_is_broken=defender_is_broken,
        )

        # Apply damage to target
        entity_result = target.take_damage(damage_result.damage, damage_type)

        # Log the attack (use entity_result for shield break info)
        msgs.extend(self._logger.log_attack(actor, target, damage_result, bp_spent))

        # Handle shield break
        if isinstance(target, Enemy) and entity_result.shield_broken:
            msgs.extend(self._logger.log_shield_break(target))
            self._emit_event(
                self._event_builder.shield_broken(
                    turn_number=self._total_turns,
                    combatant_id=target.id,
                    broke_by=actor.id,
                    damage_type=damage_type.name,
                )
            )

        # Emit action event
        self._emit_event(
            self._event_builder.action_executed(
                turn_number=self._total_turns,
                actor_id=actor.id,
                action_type="attack",
                target_id=target.id,
                damage_dealt=damage_result.damage,
                boost_points_spent=bp_spent if bp_spent > 0 else None,
                was_critical=damage_result.is_critical,
                was_weakness=damage_result.is_weakness,
            )
        )

        # Check if target was defeated
        if not target.is_alive:
            msgs.extend(self._logger.log_defeat(target))
            self._emit_event(
                self._event_builder.combatant_defeated(
                    turn_number=self._total_turns,
                    combatant_id=target.id,
                    defeated_by=actor.id,
                    final_damage=damage_result.damage,
                )
            )

        return msgs

    def _execute_defend(self, actor: Combatant) -> list[str]:
        """
        Execute a defend action.

        Args:
            actor: The defending combatant.

        Returns:
            List of log messages.
        """
        msgs = self._logger.log_defend(actor)

        self._emit_event(
            self._event_builder.action_executed(
                turn_number=self._total_turns,
                actor_id=actor.id,
                action_type="defend",
            )
        )

        return msgs

    def _execute_flee(self, actor: Combatant) -> list[str]:
        """
        Execute a flee attempt.

        Flee chance is based on player speed vs average enemy speed.
        Base 50% + (player_speed - avg_enemy_speed).

        Args:
            actor: The fleeing combatant.

        Returns:
            List of log messages.
        """
        msgs: list[str] = []

        # Calculate flee chance
        avg_enemy_speed = sum(e.speed for e in self.living_enemies) / max(
            len(self.living_enemies), 1
        )
        flee_chance = _BASE_FLEE_CHANCE + (actor.speed - avg_enemy_speed)
        flee_chance = max(10, min(90, flee_chance))  # Clamp to 10-90%

        # Roll for flee
        roll = self._rng.randint(1, 100)
        success = roll <= flee_chance

        msgs.extend(self._logger.log_flee(actor, success))

        self._emit_event(
            self._event_builder.combat_fled(
                turn_number=self._total_turns,
                flee_success=success,
                fled_by=actor.id,
                flee_chance=flee_chance,
            )
        )

        if success:
            self._outcome = CombatOutcome.FLED
            self._phase = CombatPhase.COMBAT_OVER
            msgs.extend(self._logger.log_combat_end("fled"))
            self._emit_event(
                self._event_builder.combat_ended(
                    outcome="fled",
                    victory=False,
                    total_turns=self._total_turns,
                )
            )

        return msgs

    def _check_combat_end(self) -> bool:
        """
        Check if combat should end (all enemies dead or player dead).

        Returns:
            True if combat is over, False otherwise.
        """
        if not self.player.is_alive:
            self._outcome = CombatOutcome.DEFEAT
            self._phase = CombatPhase.COMBAT_OVER
            self._logger.log_combat_end("defeat")
            self._emit_event(
                self._event_builder.combat_ended(
                    outcome="defeat",
                    victory=False,
                    total_turns=self._total_turns,
                )
            )
            return True

        if not self.living_enemies:
            self._outcome = CombatOutcome.VICTORY
            self._phase = CombatPhase.COMBAT_OVER
            self._logger.log_combat_end("victory")
            self._emit_event(
                self._event_builder.combat_ended(
                    outcome="victory",
                    victory=True,
                    total_turns=self._total_turns,
                )
            )
            return True

        return False

    def _calculate_turn_order(self) -> list[Combatant]:
        """
        Calculate turn order based on speed (highest first).

        Deterministic tiebreak: use combatant ID string comparison.

        Returns:
            List of living combatants sorted by speed (descending).
        """
        combatants: list[Combatant] = [self.player] + [e for e in self.enemies if e.is_alive]
        # Sort by speed descending, then by ID ascending for deterministic tiebreak
        combatants.sort(key=lambda c: (-c.speed, c.id))
        return combatants

    def _find_combatant(self, combatant_id: str) -> Combatant:
        """
        Find a combatant by ID.

        Args:
            combatant_id: The combatant's unique identifier.

        Returns:
            The matching Combatant.

        Raises:
            ValueError: If no combatant with that ID exists.
        """
        if self.player.id == combatant_id:
            return self.player
        for enemy in self.enemies:
            if enemy.id == combatant_id:
                return enemy
        raise ValueError(f"No combatant found with id: {combatant_id}")

    def _set_phase_for_current_combatant(self) -> None:
        """Begin the current combatant's turn: emit TURN_STARTED, then set the phase.

        TURN_STARTED is the canonical per-turn marker the rewind replay uses to
        reconstruct ``_total_turns`` and ``_round_number`` (see
        ``TemporalSystem._apply_event``). ``turn_number`` is the turn about to be
        taken — ``_total_turns`` is incremented by the action method that follows
        (``submit_player_action`` / ``execute_enemy_turn``) — and ``round_number``
        is recorded so replay needs no turn-order arithmetic.

        This is the single choke point reached at every turn boundary (from
        ``start_round`` and ``advance_turn``), so emitting here covers all turns.
        """
        current = self._turn_order[self._turn_index]
        self._emit_event(
            self._event_builder.turn_started(
                turn_number=self._total_turns + 1,
                active_combatant_id=current.id,
                round_number=self._round_number,
            )
        )
        if isinstance(current, Player):
            self._phase = CombatPhase.AWAITING_PLAYER_INPUT
        else:
            self._phase = CombatPhase.EXECUTING_TURN

    def rewind_to_turn(
        self,
        target_turn: int,
        actor: Combatant | None = None,
    ) -> RewindResult:
        """
        Rewind combat to ``target_turn`` on a new branch.

        Delegates to ``TemporalSystem.rewind`` after computing ``turns_back``
        from the difference between the current total turns and the requested
        target. The player is used as the actor if none is provided.

        Args:
            target_turn: Turn number to rewind to (must be ≥ 0 and ≤
                ``_total_turns``).
            actor: Combatant spending the charge (defaults to the player).

        Returns:
            RewindResult with from_turn, to_turn, new_branch_id,
            events_replayed, and charge_spent.

        Raises:
            ValueError: If ``turns_back < 1`` (i.e. ``target_turn >=
                _total_turns``).
            InsufficientChargeError: If the actor has insufficient charge
                (multi-turn rewinds cost ``turns_back`` charges).
            RewindBoundaryError: If the target turn would be < 0.
            RewindUnavailableError: If combat phase forbids rewind.
            RewindReplayError: If event replay fails mid-flight.
        """
        actor = actor or self.player
        turns_back = self._total_turns - target_turn
        return self._temporal.rewind(self, actor, turns=turns_back)

    def _emit_event(self, event: GameEvent) -> None:
        """
        Persist a combat event to the event store.

        Args:
            event: The GameEvent to persist.
        """
        self._event_store.append_event(event)
