"""
Enemy AI decision-making system for combat.

This module implements weighted random enemy AI with 5 archetypes:
- AGGRESSIVE: Always attacks, rarely defends
- DEFENSIVE: Cautious, defends often
- TACTICAL: Adapts to player/enemy HP, uses abilities strategically
- BERSERKER: Attacks MORE when low HP (rage mode)
- CHRONOMANCER: Rewinds when hurt, echoes when alone, counters temporal casts

AI decisions are deterministic using seeded RNG for event replay.
Weights are modified by HP thresholds for basic situational awareness.

Related Decisions: DEC-2005, DEC-2006
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from src.entities import Enemy, Player

if TYPE_CHECKING:
    from src.core.temporal import TemporalAnnouncement

# Chronomancer thresholds. Tuned through eval/fixtures/chronomancer.yaml.
CHRONO_REWIND_HP_PCT = 40  # rewinds while own HP is below this percentage
CHRONO_MAX_REWINDS = 2  # per combat, counted from persistent TEMPORAL_REWIND events
CHRONO_REWIND_TURNS = 1  # depth of a Chronomancer rewind
CHRONO_REWIND_COST = 1  # charge per turn rewound
CHRONO_ECHO_COST = 2  # mirrors temporal.ECHO_CAST_COST
CHRONO_MAX_ECHO_TURNS = 3  # mirrors temporal.MAX_ECHO_TURNS
CHRONO_HOARD_PLAYER_CHARGE = 2  # player charge at which echo is held back for a counter


class AIArchetype(Enum):
    """
    Enemy AI behavior archetypes.

    Each archetype defines base action weights and HP-based modifiers
    that determine how an enemy selects actions during combat.
    """

    AGGRESSIVE = auto()
    DEFENSIVE = auto()
    TACTICAL = auto()
    BERSERKER = auto()
    CHRONOMANCER = auto()


@dataclass
class CombatAction:
    """
    Represents an action selected by enemy AI.

    Attributes:
        action_type: Type of action ("attack", "defend", "ability",
            "echo_cast", "rewind")
        target_id: ID of the target combatant
        skill_name: Optional skill name for ability actions
        boost_points: BP to spend (always 0 for enemies in Phase 2)
        echo_turns: Number of turns an "echo_cast" action's echo will act
            for (1-3, default 1). Ignored by all other action types.
    """

    action_type: str
    target_id: str
    skill_name: str | None = None
    boost_points: int = 0
    echo_turns: int = 1


@dataclass
class CombatState:
    """
    Snapshot of combat state for AI decision-making.

    Provides the AI with information about the current combat
    situation without exposing mutable combat internals.

    Attributes:
        player: The player combatant
        enemies: List of all enemy combatants
        round_number: Current combat round
        total_turns: Combatant turns completed so far in this combat
        rewind_counts: Combatant id -> rewinds that combatant has cast in
            this combat, counted from persistent events so the number
            survives the rewinds it counts
        history_lengths: Combatant id -> number of that combatant's
            executed actions available as an echo source (0 to 3)
        enemy_echo_active: Whether the enemy side already has a live echo
    """

    player: Player
    enemies: list[Enemy]
    round_number: int = 1
    total_turns: int = 0
    rewind_counts: dict[str, int] = field(default_factory=dict)
    history_lengths: dict[str, int] = field(default_factory=dict)
    enemy_echo_active: bool = False


class EnemyAI(ABC):
    """
    Abstract base class for enemy AI decision-making.

    Uses weighted random action selection with HP-based modifiers.
    All decisions are deterministic via seeded RNG for event replay.

    Attributes:
        enemy: The enemy combatant this AI controls
        rng: Seeded random number generator for deterministic decisions
        base_weights: Archetype-specific base action weights
    """

    def __init__(self, enemy: Enemy, rng: random.Random) -> None:
        """
        Initialize enemy AI with combatant and RNG.

        Args:
            enemy: The enemy combatant this AI controls
            rng: Seeded random number generator

        Raises:
            TypeError: If enemy is not an Enemy instance
            TypeError: If rng is not a random.Random instance
        """
        if not isinstance(enemy, Enemy):
            raise TypeError(f"Expected Enemy instance, got {type(enemy).__name__}")
        if not isinstance(rng, random.Random):
            raise TypeError(f"Expected random.Random instance, got {type(rng).__name__}")

        self.enemy = enemy
        self.rng = rng
        self.base_weights = self._get_base_weights()

    @abstractmethod
    def _get_base_weights(self) -> dict[str, int]:
        """
        Return archetype-specific base action weights.

        Returns:
            Dictionary mapping action types to weight values.
            Weights are relative (e.g., {"attack": 70, "defend": 10, "ability": 20}).
        """
        pass

    @abstractmethod
    def _calculate_situational_weights(self, combat_state: CombatState) -> dict[str, int]:
        """
        Modify weights based on current combat situation.

        Subclasses override this to implement HP-based modifiers
        and archetype-specific situational awareness.

        Args:
            combat_state: Current combat state snapshot

        Returns:
            Modified weights dictionary
        """
        pass

    def select_action(self, combat_state: CombatState) -> CombatAction:
        """
        Select an action using weighted random choice.

        Uses archetype base weights modified by situational modifiers
        (HP thresholds, etc.) to select an action deterministically.

        Args:
            combat_state: Current combat state snapshot

        Returns:
            CombatAction with selected action type and target

        Raises:
            TypeError: If combat_state is not a CombatState instance
        """
        if not isinstance(combat_state, CombatState):
            raise TypeError(f"Expected CombatState instance, got {type(combat_state).__name__}")

        weights = self._calculate_situational_weights(combat_state)

        action_type = self.rng.choices(
            population=list(weights.keys()),
            weights=list(weights.values()),
            k=1,
        )[0]

        # Target player for attacks/abilities, self for defend
        target_id = self.enemy.id if action_type == "defend" else combat_state.player.id

        return CombatAction(
            action_type=action_type,
            target_id=target_id,
        )

    def wants_counter_stop(
        self,
        announcement: TemporalAnnouncement,  # noqa: ARG002
        combat_state: CombatState,  # noqa: ARG002
    ) -> bool:
        """
        Decide whether to Counter-Stop an announced temporal cast.

        Consulted only when this enemy is already eligible (alive, opposing
        the caster, holding the full counter cost). Draws no random number.

        Args:
            announcement: The cast being announced.
            combat_state: Current combat state snapshot.

        Returns:
            False: archetypes without temporal awareness never counter.
        """
        return False


class AggressiveAI(EnemyAI):
    """
    Aggressive enemy AI archetype.

    Heavily favors attacking (70% base), rarely defends.
    Becomes slightly more defensive when HP drops below 30%.

    Base weights: attack=70, defend=10, ability=20
    Low HP modifier: attack=50, defend=25, ability=25
    """

    def _get_base_weights(self) -> dict[str, int]:
        """Return aggressive base weights (70/10/20)."""
        return {"attack": 70, "defend": 10, "ability": 20}

    def _calculate_situational_weights(
        self,
        combat_state: CombatState,  # noqa: ARG002
    ) -> dict[str, int]:
        """
        Modify weights based on enemy HP.

        Args:
            combat_state: Current combat state snapshot

        Returns:
            Modified weights - slightly more defensive when low HP
        """
        weights = self.base_weights.copy()

        # Slightly more defensive when low HP
        if self.enemy.hp_percent < 30:
            weights["attack"] = 50
            weights["defend"] = 25
            weights["ability"] = 25

        return weights


class DefensiveAI(EnemyAI):
    """
    Defensive enemy AI archetype.

    Balanced between attack and defense (40/40 base).
    Becomes even more defensive when HP drops below 50%.

    Base weights: attack=40, defend=40, ability=20
    Low HP modifier: attack=20, defend=60, ability=20
    """

    def _get_base_weights(self) -> dict[str, int]:
        """Return defensive base weights (40/40/20)."""
        return {"attack": 40, "defend": 40, "ability": 20}

    def _calculate_situational_weights(
        self,
        combat_state: CombatState,  # noqa: ARG002
    ) -> dict[str, int]:
        """
        Modify weights based on enemy HP.

        Args:
            combat_state: Current combat state snapshot

        Returns:
            Modified weights - even more defensive when low HP
        """
        weights = self.base_weights.copy()

        # Even more defensive when low HP
        if self.enemy.hp_percent < 50:
            weights["attack"] = 20
            weights["defend"] = 60

        return weights


class TacticalAI(EnemyAI):
    """
    Tactical enemy AI archetype.

    Adapts to both player and self HP. Uses abilities strategically
    when player is vulnerable, and defends when self HP is low.

    Base weights: attack=50, defend=20, ability=30
    Player low HP: ability=50 (finish them off)
    Self low HP: defend=50 (survive)
    """

    def _get_base_weights(self) -> dict[str, int]:
        """Return tactical base weights (50/20/30)."""
        return {"attack": 50, "defend": 20, "ability": 30}

    def _calculate_situational_weights(self, combat_state: CombatState) -> dict[str, int]:
        """
        Modify weights based on both player and enemy HP.

        Args:
            combat_state: Current combat state snapshot

        Returns:
            Modified weights - adapts to combat situation
        """
        weights = self.base_weights.copy()

        # Finish off low HP player with abilities
        if combat_state.player.hp_percent < 40:
            weights["ability"] = 50

        # Defend when low HP (takes priority over offensive)
        if self.enemy.hp_percent < 30:
            weights["defend"] = 50

        return weights


class BerserkerAI(EnemyAI):
    """
    Berserker enemy AI archetype.

    Attacks MORE when low HP (rage mode). Opposite of defensive
    behavior - becomes increasingly aggressive as HP drops.

    Base weights: attack=60, defend=20, ability=20
    Rage mode (<30% HP): attack=80, defend=5, ability=15
    """

    def _get_base_weights(self) -> dict[str, int]:
        """Return berserker base weights (60/20/20)."""
        return {"attack": 60, "defend": 20, "ability": 20}

    def _calculate_situational_weights(
        self,
        combat_state: CombatState,  # noqa: ARG002
    ) -> dict[str, int]:
        """
        Modify weights based on enemy HP (rage mode).

        Args:
            combat_state: Current combat state snapshot

        Returns:
            Modified weights - MORE aggressive when low HP
        """
        weights = self.base_weights.copy()

        # RAGE MODE: More aggressive when low HP
        if self.enemy.hp_percent < 30:
            weights["attack"] = 80
            weights["defend"] = 5
            weights["ability"] = 15

        return weights


class ChronomancerAI(EnemyAI):
    """
    Chronomancer enemy AI archetype: wields the player's temporal abilities.

    Temporal decisions are deterministic rules, first match wins:

    1. Rewind 1 turn when own HP is below 40%, it holds at least 1 charge,
       it has cast fewer than 2 rewinds this combat, and a turn exists to
       rewind into.
    2. Echo Cast when it is the last living enemy, holds at least 2
       charge, has an action to echo, has no live echo, and the player
       holds fewer than 2 charge (otherwise the pool is kept for a
       Counter-Stop).

    Otherwise it falls through to the weighted mix every archetype uses.
    It counters every temporal cast it is eligible to counter. The rule
    layer draws no random number and the class holds no state of its own:
    its memory of past rewinds is the persistent event log, read through
    ``CombatState.rewind_counts``.

    Base weights: attack=45, defend=35, ability=20
    """

    def _get_base_weights(self) -> dict[str, int]:
        """Return chronomancer base weights (45/35/20)."""
        return {"attack": 45, "defend": 35, "ability": 20}

    def _calculate_situational_weights(
        self,
        combat_state: CombatState,  # noqa: ARG002
    ) -> dict[str, int]:
        """
        Return the mundane action mix; temporal choices are not weighted.

        Args:
            combat_state: Current combat state snapshot

        Returns:
            The unmodified base weights.
        """
        return self.base_weights.copy()

    def select_action(self, combat_state: CombatState) -> CombatAction:
        """
        Apply the temporal rules, then fall through to the weighted mix.

        Args:
            combat_state: Current combat state snapshot

        Returns:
            A "rewind" or "echo_cast" action when a rule fires, otherwise
            the base class's weighted choice.

        Raises:
            TypeError: If combat_state is not a CombatState instance
        """
        if not isinstance(combat_state, CombatState):
            raise TypeError(f"Expected CombatState instance, got {type(combat_state).__name__}")

        if self._should_rewind(combat_state):
            return CombatAction(action_type="rewind", target_id=self.enemy.id)

        if self._should_echo(combat_state):
            history = combat_state.history_lengths.get(self.enemy.id, 0)
            return CombatAction(
                action_type="echo_cast",
                target_id=self.enemy.id,
                echo_turns=min(CHRONO_MAX_ECHO_TURNS, history),
            )

        return super().select_action(combat_state)

    def _should_rewind(self, combat_state: CombatState) -> bool:
        """
        Rule 1: rewind when hurt, while the cap and the charge allow.

        Args:
            combat_state: Current combat state snapshot

        Returns:
            True if the rewind rule fires.
        """
        return (
            self.enemy.hp_percent < CHRONO_REWIND_HP_PCT
            and self.enemy.temporal_charge >= CHRONO_REWIND_COST * CHRONO_REWIND_TURNS
            and combat_state.rewind_counts.get(self.enemy.id, 0) < CHRONO_MAX_REWINDS
            and combat_state.total_turns >= CHRONO_REWIND_TURNS
        )

    def _should_echo(self, combat_state: CombatState) -> bool:
        """
        Rule 2: echo when alone, unless the player threatens temporal play.

        Args:
            combat_state: Current combat state snapshot

        Returns:
            True if the echo rule fires.
        """
        living = [e for e in combat_state.enemies if e.is_alive]
        return (
            len(living) == 1
            and self.enemy.temporal_charge >= CHRONO_ECHO_COST
            and combat_state.player.temporal_charge < CHRONO_HOARD_PLAYER_CHARGE
            and combat_state.history_lengths.get(self.enemy.id, 0) >= 1
            and not combat_state.enemy_echo_active
        )

    def wants_counter_stop(
        self,
        announcement: TemporalAnnouncement,  # noqa: ARG002
        combat_state: CombatState,  # noqa: ARG002
    ) -> bool:
        """
        Counter every temporal cast this enemy is eligible to counter.

        Args:
            announcement: The cast being announced.
            combat_state: Current combat state snapshot.

        Returns:
            True, always: eligibility is filtered before this is asked.
        """
        return True


def create_enemy_ai(enemy: Enemy, archetype: AIArchetype, rng: random.Random) -> EnemyAI:
    """
    Factory function to create an AI instance based on archetype.

    Args:
        enemy: The enemy combatant the AI will control
        archetype: AI behavior archetype to use
        rng: Seeded random number generator for deterministic decisions

    Returns:
        EnemyAI subclass instance matching the archetype

    Raises:
        ValueError: If archetype is not a valid AIArchetype
    """
    ai_classes: dict[AIArchetype, type[EnemyAI]] = {
        AIArchetype.AGGRESSIVE: AggressiveAI,
        AIArchetype.DEFENSIVE: DefensiveAI,
        AIArchetype.TACTICAL: TacticalAI,
        AIArchetype.BERSERKER: BerserkerAI,
        AIArchetype.CHRONOMANCER: ChronomancerAI,
    }

    if archetype not in ai_classes:
        raise ValueError(f"Unknown archetype: {archetype}")

    return ai_classes[archetype](enemy, rng)
