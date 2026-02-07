"""
Player character entity for combat.

This module defines the Player class with Boost Point mechanics
inspired by Octopath Traveler.
"""

from dataclasses import dataclass

from .combatant import Combatant, DamageResult
from .damage_types import DamageType


@dataclass
class Player(Combatant):
    """
    Player character with Boost Point system.

    Players gain 1 BP per turn (max 5) and can spend BP to boost
    attack damage with multipliers:
    - 0 BP: 1.0x damage (normal attack)
    - 1 BP: 1.5x damage
    - 2 BP: 2.0x damage
    - 3 BP: 2.5x damage

    Attributes:
        boost_points: Current BP (0-5)
        max_boost_points: Maximum BP (default 5)
    """

    boost_points: int = 0
    max_boost_points: int = 5

    def __post_init__(self) -> None:
        """Validate player stats and BP after initialization."""
        super().__post_init__()

        if self.boost_points < 0:
            raise ValueError(f"boost_points cannot be negative, got {self.boost_points}")

        if self.boost_points > self.max_boost_points:
            raise ValueError(
                f"boost_points ({self.boost_points}) cannot exceed "
                f"max_boost_points ({self.max_boost_points})"
            )

        if self.max_boost_points <= 0:
            raise ValueError(f"max_boost_points must be positive, got {self.max_boost_points}")

    def gain_bp(self, amount: int = 1) -> int:
        """
        Gain Boost Points (capped at max_boost_points).

        Args:
            amount: BP to gain (default 1 per turn)

        Returns:
            Actual BP gained (may be less if capped)

        Raises:
            ValueError: If amount is negative
        """
        if amount < 0:
            raise ValueError(f"BP gain amount cannot be negative, got {amount}")

        old_bp = self.boost_points
        self.boost_points = min(self.boost_points + amount, self.max_boost_points)
        actual_gained = self.boost_points - old_bp

        return actual_gained

    def spend_bp(self, amount: int) -> float:
        """
        Spend BP and return the damage multiplier.

        Multipliers:
        - 0 BP: 1.0x (normal attack, no BP spent)
        - 1 BP: 1.5x
        - 2 BP: 2.0x
        - 3 BP: 2.5x

        Args:
            amount: BP to spend (0-3)

        Returns:
            Damage multiplier (1.0x to 2.5x)

        Raises:
            ValueError: If amount is invalid or insufficient BP
        """
        if amount < 0 or amount > 3:
            raise ValueError(f"Can only spend 0-3 BP, got {amount}")

        if amount > self.boost_points:
            raise ValueError(f"Not enough BP: have {self.boost_points}, need {amount}")

        # Spend BP
        self.boost_points -= amount

        # Return multiplier
        multipliers = {
            0: 1.0,
            1: 1.5,
            2: 2.0,
            3: 2.5,
        }
        return multipliers[amount]

    def take_damage(
        self,
        damage: int,
        damage_type: DamageType,  # noqa: ARG002
    ) -> DamageResult:
        """
        Apply damage to player (simple damage application).

        Players don't have special damage mechanics like the Break System,
        so this just reduces HP.

        Args:
            damage: Damage amount to apply
            damage_type: Type of damage (for future resistance system)

        Returns:
            DamageResult with actual damage dealt
        """
        if damage < 0:
            raise ValueError(f"Damage cannot be negative, got {damage}")

        # Apply damage
        actual_damage = min(damage, self.hp)  # Can't deal more than current HP
        self.hp = max(0, self.hp - damage)

        return DamageResult(
            damage=actual_damage,
            weakness_hit=False,
            shield_broken=False,
            is_critical=False,
        )

    def __str__(self) -> str:
        """Return human-readable player description with BP."""
        return f"{self.name} (Lv{self.level}): {self.hp}/{self.max_hp} HP | {self.boost_points}/{self.max_boost_points} BP"
