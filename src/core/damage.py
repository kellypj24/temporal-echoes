"""
Damage calculation system for combat.

This module implements the hybrid damage formula with all multipliers:
- Base damage: (ATK * Power) / (DEF * 0.5 + 10)
- Random variance: 85-100%
- Boost multiplier: 1.0x to 2.5x (based on BP spent)
- Type effectiveness: 2.0x for weaknesses
- Critical hit: 1.5x damage
- Break bonus: 1.5x when enemy is broken
- Clamped: [1, 9999]

All RNG is seeded for deterministic replay.
"""

import random
from dataclasses import dataclass, field

from src.entities import DamageType


@dataclass
class DamageResult:
    """
    Result of a damage calculation.

    Attributes:
        damage: Final damage amount
        is_critical: Whether the attack was a critical hit
        is_weakness: Whether the attack hit a weakness
        multipliers: Dictionary of all multipliers applied
        random_factor: Random variance factor (0.85-1.00)
    """

    damage: int
    is_critical: bool = False
    is_weakness: bool = False
    multipliers: dict[str, float] = field(default_factory=dict)
    random_factor: float = 1.0


class DamageCalculator:
    """
    Deterministic damage calculator with all combat modifiers.

    Uses a seeded RNG for deterministic combat replay. The damage formula
    incorporates base damage, random variance, and multiple multipliers.

    Formula:
        Damage = (ATK * Power / (DEF * 0.5 + 10))
                 * Random(0.85, 1.00)
                 * Boost_Mult * Type_Mult * Crit_Mult * Break_Mult
                 → Clamped [1, 9999]

    Attributes:
        rng: Seeded random number generator
        seed: Original seed value for debugging
    """

    # Constants
    MIN_DAMAGE = 1
    MAX_DAMAGE = 9999
    BASE_CRIT_CHANCE = 5  # 5% default crit chance
    RANDOM_VARIANCE_MIN = 0.85
    RANDOM_VARIANCE_MAX = 1.00

    # Multipliers
    BOOST_MULTIPLIERS = {
        0: 1.0,  # No boost
        1: 1.5,  # 1 BP spent
        2: 2.0,  # 2 BP spent
        3: 2.5,  # 3 BP spent (max)
    }
    TYPE_EFFECTIVENESS_MULT = 2.0
    CRITICAL_HIT_MULT = 1.5
    BREAK_BONUS_MULT = 1.5

    def __init__(self, rng_seed: int):
        """
        Initialize damage calculator with seeded RNG.

        Args:
            rng_seed: Seed for random number generator (for deterministic replay)

        Raises:
            ValueError: If rng_seed is negative
        """
        if rng_seed < 0:
            raise ValueError(f"rng_seed must be non-negative, got {rng_seed}")

        self.seed = rng_seed
        self.rng = random.Random(rng_seed)

    def calculate(
        self,
        attacker_atk: int,
        defender_def: int,
        skill_power: int = 100,
        boost_points: int = 0,
        damage_type: DamageType = DamageType.PHYSICAL,
        defender_weaknesses: list[DamageType] | None = None,
        defender_is_broken: bool = False,
        crit_chance: int = BASE_CRIT_CHANCE,
    ) -> DamageResult:
        """
        Calculate damage with full formula and all modifiers.

        Args:
            attacker_atk: Attacker's attack stat
            defender_def: Defender's defense stat
            skill_power: Skill power multiplier (default 100 = 1.0x)
            boost_points: BP spent (0-3)
            damage_type: Type of damage being dealt
            defender_weaknesses: List of defender's weakness types
            defender_is_broken: Whether defender is in broken state
            crit_chance: Critical hit chance percentage (0-100)

        Returns:
            DamageResult with final damage and metadata

        Raises:
            ValueError: If parameters are out of valid ranges
        """
        # Validate inputs
        if attacker_atk < 0:
            raise ValueError(f"attacker_atk cannot be negative, got {attacker_atk}")
        if defender_def < 0:
            raise ValueError(f"defender_def cannot be negative, got {defender_def}")
        if skill_power <= 0:
            raise ValueError(f"skill_power must be positive, got {skill_power}")
        if boost_points < 0 or boost_points > 3:
            raise ValueError(f"boost_points must be 0-3, got {boost_points}")
        if crit_chance < 0 or crit_chance > 100:
            raise ValueError(f"crit_chance must be 0-100, got {crit_chance}")

        if defender_weaknesses is None:
            defender_weaknesses = []

        # Step 1: Calculate base damage
        # Formula: (ATK * Power) / (DEF * 0.5 + 10)
        # The DEF formula prevents division by zero and provides diminishing returns
        safe_def = max(1, defender_def)
        base_damage = (attacker_atk * skill_power) / (safe_def * 0.5 + 10)

        # Step 2: Apply random variance (85-100%)
        random_factor = self.rng.uniform(self.RANDOM_VARIANCE_MIN, self.RANDOM_VARIANCE_MAX)
        damage = base_damage * random_factor

        # Step 3: Apply boost multiplier
        boost_mult = self.BOOST_MULTIPLIERS[boost_points]
        damage *= boost_mult

        # Step 4: Apply type effectiveness
        is_weakness = damage_type in defender_weaknesses
        type_mult = self.TYPE_EFFECTIVENESS_MULT if is_weakness else 1.0
        damage *= type_mult

        # Step 5: Roll for critical hit
        crit_roll = self.rng.randint(1, 100)
        is_critical = crit_roll <= crit_chance
        crit_mult = self.CRITICAL_HIT_MULT if is_critical else 1.0
        damage *= crit_mult

        # Step 6: Apply break bonus
        break_mult = self.BREAK_BONUS_MULT if defender_is_broken else 1.0
        damage *= break_mult

        # Step 7: Clamp to valid range [1, 9999]
        final_damage = int(damage)
        final_damage = max(self.MIN_DAMAGE, min(final_damage, self.MAX_DAMAGE))

        return DamageResult(
            damage=final_damage,
            is_critical=is_critical,
            is_weakness=is_weakness,
            multipliers={
                "boost": boost_mult,
                "type": type_mult,
                "critical": crit_mult,
                "break": break_mult,
            },
            random_factor=random_factor,
        )

    def calculate_expected_damage(
        self,
        attacker_atk: int,
        defender_def: int,
        skill_power: int = 100,
        boost_points: int = 0,
        damage_type: DamageType = DamageType.PHYSICAL,
        defender_weaknesses: list[DamageType] | None = None,
        defender_is_broken: bool = False,
    ) -> float:
        """
        Calculate expected damage without random variance or critical hits.

        Useful for AI decision-making and balancing. Uses average random
        factor (0.925) and ignores critical hits.

        Args:
            attacker_atk: Attacker's attack stat
            defender_def: Defender's defense stat
            skill_power: Skill power multiplier (default 100)
            boost_points: BP spent (0-3)
            damage_type: Type of damage being dealt
            defender_weaknesses: List of defender's weakness types
            defender_is_broken: Whether defender is in broken state

        Returns:
            Expected damage as a float
        """
        if defender_weaknesses is None:
            defender_weaknesses = []

        # Base damage
        safe_def = max(1, defender_def)
        base_damage = (attacker_atk * skill_power) / (safe_def * 0.5 + 10)

        # Average random factor (midpoint of 0.85-1.00)
        avg_random = (self.RANDOM_VARIANCE_MIN + self.RANDOM_VARIANCE_MAX) / 2
        damage = base_damage * avg_random

        # Apply all non-random multipliers
        boost_mult = self.BOOST_MULTIPLIERS[boost_points]
        damage *= boost_mult

        is_weakness = damage_type in defender_weaknesses
        type_mult = self.TYPE_EFFECTIVENESS_MULT if is_weakness else 1.0
        damage *= type_mult

        # Don't apply critical hit for expected value

        break_mult = self.BREAK_BONUS_MULT if defender_is_broken else 1.0
        damage *= break_mult

        # Clamp
        final_damage = max(self.MIN_DAMAGE, min(damage, self.MAX_DAMAGE))

        return final_damage

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return f"DamageCalculator(seed={self.seed})"

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"DamageCalculator with seed {self.seed}"
