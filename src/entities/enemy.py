"""
Enemy entity with Break System mechanics.

This module defines the Enemy class with the Break System inspired
by Octopath Traveler, where hitting weaknesses breaks shields and
stuns the enemy for bonus damage.
"""

from dataclasses import dataclass, field

from .combatant import Combatant, DamageResult
from .damage_types import DamageType


@dataclass
class Enemy(Combatant):
    """
    Enemy combatant with Break System.

    Enemies have shield points and weaknesses. When a weakness is hit,
    the shield is damaged. When the shield breaks (reaches 0), the enemy
    is stunned for 1 turn and takes 1.5x damage.

    Break System:
    - Enemies start with shield_points (e.g., 3-5)
    - Hitting a weakness reduces shield by 1
    - Shield breaking to 0 triggers "Broken" state
    - Broken state: 1.5x damage taken, stunned for 1 turn
    - Shield regenerates when break ends

    Attributes:
        shield_points: Current shield strength
        max_shield_points: Shield strength when restored
        weaknesses: List of damage types that reduce shield
        is_broken: Whether enemy is currently in Broken state
        break_turns_remaining: Turns left in Broken state
        archetype: AI archetype for behavior (used in Step 4)
    """

    shield_points: int
    max_shield_points: int
    weaknesses: list[DamageType] = field(default_factory=list)
    is_broken: bool = False
    break_turns_remaining: int = 0
    archetype: str = "aggressive"  # Default archetype

    def __post_init__(self) -> None:
        """Validate enemy stats and break system after initialization."""
        super().__post_init__()

        if self.shield_points < 0:
            raise ValueError(
                f"shield_points cannot be negative, got {self.shield_points}"
            )

        if self.max_shield_points <= 0:
            raise ValueError(
                f"max_shield_points must be positive, got {self.max_shield_points}"
            )

        if self.shield_points > self.max_shield_points:
            raise ValueError(
                f"shield_points ({self.shield_points}) cannot exceed "
                f"max_shield_points ({self.max_shield_points})"
            )

        if self.break_turns_remaining < 0:
            raise ValueError(
                f"break_turns_remaining cannot be negative, got {self.break_turns_remaining}"
            )

    def take_damage(self, damage: int, damage_type: DamageType) -> DamageResult:
        """
        Apply damage with Break System mechanics.

        Process:
        1. Apply break multiplier if currently broken (before shield check)
        2. Check if damage type hits weakness
        3. If weakness hit and not broken, reduce shield
        4. If shield reaches 0, trigger break (for next hit)
        5. Reduce HP

        Args:
            damage: Raw damage amount
            damage_type: Type of damage being dealt

        Returns:
            DamageResult with actual damage, weakness flag, and break status
        """
        if damage < 0:
            raise ValueError(f"Damage cannot be negative, got {damage}")

        # Apply break damage multiplier FIRST (if already broken from previous hit)
        break_multiplier = 1.5 if self.is_broken else 1.0
        actual_damage = int(damage * break_multiplier)

        # Check weakness
        weakness_hit = damage_type in self.weaknesses
        shield_broken = False

        # Handle shield damage (only if not already broken)
        # Note: This happens AFTER damage calculation, so breaking hit gets normal damage
        if weakness_hit and not self.is_broken:
            self.shield_points -= 1

            # Check if shield just broke
            if self.shield_points <= 0:
                shield_broken = True
                self.trigger_break()

        # Apply damage to HP
        actual_damage = min(actual_damage, self.hp)  # Can't deal more than current HP
        self.hp = max(0, self.hp - actual_damage)

        return DamageResult(
            damage=actual_damage,
            weakness_hit=weakness_hit,
            shield_broken=shield_broken,
            is_critical=False,  # Critical hits are calculated in damage calculator
            multipliers={"break": break_multiplier},
        )

    def trigger_break(self) -> None:
        """
        Trigger Break state (stun enemy for 1 turn with 1.5x damage).

        Called when shield_points reaches 0. The enemy is stunned
        and cannot act for 1 turn.
        """
        self.is_broken = True
        self.break_turns_remaining = 1
        self.shield_points = 0

    def process_turn_end(self) -> str | None:
        """
        Process end-of-turn effects for Break System.

        Reduces break turns remaining. When break ends, restores shield.
        Should be called at the end of this enemy's turn.

        Returns:
            Status message if break state changed, None otherwise
        """
        if not self.is_broken:
            return None

        self.break_turns_remaining -= 1

        if self.break_turns_remaining <= 0:
            # Break ends, restore shield
            self.is_broken = False
            self.break_turns_remaining = 0
            self.shield_points = self.max_shield_points
            return f"{self.name}'s shield has been restored!"

        return None

    def __str__(self) -> str:
        """Return human-readable enemy description with shield status."""
        shield_status = (
            "BROKEN"
            if self.is_broken
            else f"{self.shield_points}/{self.max_shield_points} Shield"
        )
        return f"{self.name} (Lv{self.level}): {self.hp}/{self.max_hp} HP | {shield_status}"
