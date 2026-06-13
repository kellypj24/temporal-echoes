"""
Base combatant class for all combat participants.

This module provides the abstract base class for Player and Enemy entities,
defining shared attributes and behavior for all combat participants.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .damage_types import DamageType

# Default cap for temporal charge. Matches the maximum rewind window from
# the Phase 3 design (rewind up to 3 turns, 1 charge per turn rewound).
DEFAULT_MAX_TEMPORAL_CHARGE = 3


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

    Provides shared attributes (HP, ATK, DEF, Speed, TemporalCharge) and
    common functionality for both Player and Enemy entities.

    TemporalCharge is the combat-local resource that gates time abilities
    (rewind, echo, counter-stop) per Phase 3 design. It is symmetric across
    Player and Enemy (Chronomancers wield the same primitives the player
    does) and resets to 0 at the start of each combat.

    Attributes:
        id: Unique identifier for this combatant
        name: Display name
        level: Current level (affects stats)
        hp: Current hit points
        max_hp: Maximum hit points
        attack: Base attack stat
        defense: Base defense stat
        speed: Speed stat (determines turn order)
        temporal_charge: Current temporal charge (0 to max_temporal_charge)
        max_temporal_charge: Maximum temporal charge (default 3, matching
            the maximum rewind window from Phase 3 design)
    """

    id: str
    name: str
    level: int
    hp: int
    max_hp: int
    attack: int
    defense: int
    speed: int
    temporal_charge: int = field(default=0, kw_only=True)
    max_temporal_charge: int = field(default=3, kw_only=True)

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

        if self.max_temporal_charge <= 0:
            raise ValueError(
                f"max_temporal_charge must be positive, got {self.max_temporal_charge}"
            )

        if self.temporal_charge < 0:
            raise ValueError(f"temporal_charge cannot be negative, got {self.temporal_charge}")

        if self.temporal_charge > self.max_temporal_charge:
            raise ValueError(
                f"temporal_charge ({self.temporal_charge}) cannot exceed "
                f"max_temporal_charge ({self.max_temporal_charge})"
            )

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

    def gain_charge(self, amount: int = 1) -> int:
        """
        Gain temporal charge (capped at max_temporal_charge).

        Mirrors the BP gain pattern on Player. Charges are the resource gate
        for all time abilities (rewind, echo, counter-stop) and regenerate
        slowly through combat (typically 1 per round at round start).

        Args:
            amount: Charge to gain (default 1; must be non-negative)

        Returns:
            Actual charge gained (may be less than requested if the cap was hit)

        Raises:
            ValueError: If amount is negative
        """
        if amount < 0:
            raise ValueError(f"Charge gain amount cannot be negative, got {amount}")

        old_charge = self.temporal_charge
        self.temporal_charge = min(self.temporal_charge + amount, self.max_temporal_charge)
        return self.temporal_charge - old_charge

    def spend_charge(self, amount: int) -> None:
        """
        Spend temporal charge to fuel a time ability.

        Unlike BP spend (which returns a damage multiplier), charge spend has
        no return value: charges are a pure resource gate, not a scalar
        modifier. The caller is responsible for translating the spend into
        an ability effect (rewind depth, echo duration, counter cost).

        Args:
            amount: Charge to spend (must be non-negative and ≤ current charge)

        Raises:
            ValueError: If amount is negative or exceeds current charge
        """
        if amount < 0:
            raise ValueError(f"Charge spend amount cannot be negative, got {amount}")

        if amount > self.temporal_charge:
            raise ValueError(
                f"Not enough temporal charge: have {self.temporal_charge}, need {amount}"
            )

        self.temporal_charge -= amount

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
