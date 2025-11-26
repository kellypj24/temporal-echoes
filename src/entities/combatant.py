"""
Base combatant class for all combat participants.

This module provides the abstract base class for Player and Enemy entities,
defining shared attributes and behavior for all combat participants.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .damage_types import DamageType


@dataclass
class DamageResult:
    """
    Result of a damage calculation.

    Attributes:
        damage: Final damage amount dealt
        weakness_hit: Whether the attack hit a weakness
        shield_broken: Whether the attack broke the target's shield
        is_critical: Whether the attack was a critical hit
        multipliers: Dictionary of all multipliers applied
    """

    damage: int
    weakness_hit: bool = False
    shield_broken: bool = False
    is_critical: bool = False
    multipliers: dict[str, float] = field(default_factory=dict)


@dataclass
class Combatant(ABC):
    """
    Abstract base class for all combat participants.

    Provides shared attributes (HP, ATK, DEF, Speed) and common
    functionality for both Player and Enemy entities.

    Attributes:
        id: Unique identifier for this combatant
        name: Display name
        level: Current level (affects stats)
        hp: Current hit points
        max_hp: Maximum hit points
        attack: Base attack stat
        defense: Base defense stat
        speed: Speed stat (determines turn order)
    """

    id: str
    name: str
    level: int
    hp: int
    max_hp: int
    attack: int
    defense: int
    speed: int

    def __post_init__(self) -> None:
        """Validate combatant stats after initialization."""
        if self.max_hp <= 0:
            raise ValueError(f"max_hp must be positive, got {self.max_hp}")

        if self.hp < 0:
            raise ValueError(f"hp cannot be negative, got {self.hp}")

        if self.hp > self.max_hp:
            raise ValueError(f"hp ({self.hp}) cannot exceed max_hp ({self.max_hp})")

        if self.attack < 0:
            raise ValueError(f"attack cannot be negative, got {self.attack}")

        if self.defense < 0:
            raise ValueError(f"defense cannot be negative, got {self.defense}")

        if self.speed < 0:
            raise ValueError(f"speed cannot be negative, got {self.speed}")

    @property
    def hp_percent(self) -> float:
        """
        Calculate HP as percentage of max HP.

        Returns:
            HP percentage (0.0 to 100.0)
        """
        if self.max_hp <= 0:
            return 0.0
        return (self.hp / self.max_hp) * 100.0

    @property
    def is_alive(self) -> bool:
        """
        Check if combatant can still act in combat.

        Returns:
            True if HP > 0, False otherwise
        """
        return self.hp > 0

    def heal(self, amount: int) -> int:
        """
        Restore HP without exceeding max HP.

        Args:
            amount: HP to restore (must be non-negative)

        Returns:
            Actual HP restored (may be less if capped at max_hp)

        Raises:
            ValueError: If amount is negative
        """
        if amount < 0:
            raise ValueError(f"Heal amount cannot be negative, got {amount}")

        old_hp = self.hp
        self.hp = min(self.hp + amount, self.max_hp)
        actual_healed = self.hp - old_hp

        return actual_healed

    @abstractmethod
    def take_damage(self, damage: int, damage_type: DamageType) -> DamageResult:
        """
        Apply damage to this combatant.

        This method must be implemented by subclasses to handle
        class-specific damage logic (e.g., Break System for enemies).

        Args:
            damage: Raw damage amount
            damage_type: Type of damage being dealt

        Returns:
            DamageResult with final damage and metadata
        """
        pass

    def __str__(self) -> str:
        """Return human-readable combatant description."""
        return f"{self.name} (Lv{self.level}): {self.hp}/{self.max_hp} HP"
