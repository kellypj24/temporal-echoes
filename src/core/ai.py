"""
Enemy AI decision-making system for combat.

This module implements weighted random enemy AI with 4 archetypes:
- AGGRESSIVE: Always attacks, rarely defends
- DEFENSIVE: Cautious, defends often
- TACTICAL: Adapts to player/enemy HP, uses abilities strategically
- BERSERKER: Attacks MORE when low HP (rage mode)

AI decisions are deterministic using seeded RNG for event replay.
Weights are modified by HP thresholds for basic situational awareness.

Related Decisions: DEC-2005, DEC-2006
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from src.entities import Enemy, Player


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


@dataclass
class CombatAction:
    """
    Represents an action selected by enemy AI.

    Attributes:
        action_type: Type of action ("attack", "defend", "ability")
        target_id: ID of the target combatant
        skill_name: Optional skill name for ability actions
        boost_points: BP to spend (always 0 for enemies in Phase 2)
    """

    action_type: str
    target_id: str
    skill_name: str | None = None
    boost_points: int = 0


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
    """

    player: Player
    enemies: list[Enemy]
    round_number: int = 1


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
            raise TypeError(
                f"Expected random.Random instance, got {type(rng).__name__}"
            )

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
    def _calculate_situational_weights(
        self, combat_state: CombatState
    ) -> dict[str, int]:
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
            raise TypeError(
                f"Expected CombatState instance, got {type(combat_state).__name__}"
            )

        weights = self._calculate_situational_weights(combat_state)

        action_type = self.rng.choices(
            population=list(weights.keys()),
            weights=list(weights.values()),
            k=1,
        )[0]

        # Target player for attacks/abilities, self for defend
        target_id = (
            self.enemy.id if action_type == "defend" else combat_state.player.id
        )

        return CombatAction(
            action_type=action_type,
            target_id=target_id,
        )


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
        self, combat_state: CombatState  # noqa: ARG002
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
        self, combat_state: CombatState  # noqa: ARG002
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

    def _calculate_situational_weights(
        self, combat_state: CombatState
    ) -> dict[str, int]:
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
        self, combat_state: CombatState  # noqa: ARG002
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


def create_enemy_ai(
    enemy: Enemy, archetype: AIArchetype, rng: random.Random
) -> EnemyAI:
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
    }

    if archetype not in ai_classes:
        raise ValueError(f"Unknown archetype: {archetype}")

    return ai_classes[archetype](enemy, rng)
