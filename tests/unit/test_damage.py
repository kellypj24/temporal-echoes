"""
Unit tests for damage calculation system.

Tests for DamageCalculator class including:
- Initialization and validation
- Base damage formula
- All multipliers (boost, type, critical, break)
- Random variance
- Damage clamping
- Determinism
- Edge cases
"""

import pytest

from src.core.damage import DamageCalculator
from src.entities import DamageType

# ============================================================================
# Initialization Tests
# ============================================================================


class TestDamageCalculatorInitialization:
    """Tests for DamageCalculator initialization."""

    def test_create_with_valid_seed(self):
        """Test creating calculator with valid seed."""
        calc = DamageCalculator(rng_seed=42)

        assert calc.seed == 42
        assert calc.rng is not None

    def test_create_with_zero_seed(self):
        """Test creating calculator with seed 0 is valid."""
        calc = DamageCalculator(rng_seed=0)

        assert calc.seed == 0

    def test_create_with_negative_seed_raises_error(self):
        """Test that negative seed raises ValueError."""
        with pytest.raises(ValueError, match="rng_seed must be non-negative"):
            DamageCalculator(rng_seed=-1)

    def test_repr(self):
        """Test repr includes seed."""
        calc = DamageCalculator(rng_seed=123)
        result = repr(calc)

        assert "DamageCalculator" in result
        assert "seed=123" in result

    def test_str(self):
        """Test str representation."""
        calc = DamageCalculator(rng_seed=456)
        result = str(calc)

        assert "DamageCalculator" in result
        assert "456" in result


# ============================================================================
# Input Validation Tests
# ============================================================================


class TestDamageCalculatorValidation:
    """Tests for input validation in calculate()."""

    def test_negative_attacker_atk_raises_error(self):
        """Test negative attacker_atk raises ValueError."""
        calc = DamageCalculator(rng_seed=42)

        with pytest.raises(ValueError, match="attacker_atk cannot be negative"):
            calc.calculate(attacker_atk=-10, defender_def=30)

    def test_negative_defender_def_raises_error(self):
        """Test negative defender_def raises ValueError."""
        calc = DamageCalculator(rng_seed=42)

        with pytest.raises(ValueError, match="defender_def cannot be negative"):
            calc.calculate(attacker_atk=50, defender_def=-10)

    def test_zero_skill_power_raises_error(self):
        """Test skill_power <= 0 raises ValueError."""
        calc = DamageCalculator(rng_seed=42)

        with pytest.raises(ValueError, match="skill_power must be positive"):
            calc.calculate(attacker_atk=50, defender_def=30, skill_power=0)

    def test_negative_skill_power_raises_error(self):
        """Test negative skill_power raises ValueError."""
        calc = DamageCalculator(rng_seed=42)

        with pytest.raises(ValueError, match="skill_power must be positive"):
            calc.calculate(attacker_atk=50, defender_def=30, skill_power=-100)

    def test_invalid_boost_points_raises_error(self):
        """Test boost_points outside 0-3 raises ValueError."""
        calc = DamageCalculator(rng_seed=42)

        with pytest.raises(ValueError, match="boost_points must be 0-3"):
            calc.calculate(attacker_atk=50, defender_def=30, boost_points=4)

        with pytest.raises(ValueError, match="boost_points must be 0-3"):
            calc.calculate(attacker_atk=50, defender_def=30, boost_points=-1)

    def test_invalid_crit_chance_raises_error(self):
        """Test crit_chance outside 0-100 raises ValueError."""
        calc = DamageCalculator(rng_seed=42)

        with pytest.raises(ValueError, match="crit_chance must be 0-100"):
            calc.calculate(attacker_atk=50, defender_def=30, crit_chance=101)

        with pytest.raises(ValueError, match="crit_chance must be 0-100"):
            calc.calculate(attacker_atk=50, defender_def=30, crit_chance=-5)


# ============================================================================
# Basic Damage Calculation Tests
# ============================================================================


class TestBasicDamageCalculation:
    """Tests for basic damage formula without multipliers."""

    def test_calculate_basic_damage(self):
        """Test basic damage calculation with no multipliers."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(
            attacker_atk=50,
            defender_def=30,
            skill_power=100,
            boost_points=0,
            crit_chance=0,  # No crits
        )

        assert result.damage >= 1
        assert result.damage <= 9999
        assert result.is_critical is False
        assert result.is_weakness is False

    def test_higher_attack_increases_damage(self):
        """Test that higher attack increases damage."""
        calc1 = DamageCalculator(rng_seed=42)
        calc2 = DamageCalculator(rng_seed=42)  # Same seed for same random

        result1 = calc1.calculate(attacker_atk=50, defender_def=30, crit_chance=0)
        result2 = calc2.calculate(attacker_atk=100, defender_def=30, crit_chance=0)

        assert result2.damage > result1.damage

    def test_higher_defense_decreases_damage(self):
        """Test that higher defense decreases damage."""
        calc1 = DamageCalculator(rng_seed=42)
        calc2 = DamageCalculator(rng_seed=42)

        result1 = calc1.calculate(attacker_atk=50, defender_def=20, crit_chance=0)
        result2 = calc2.calculate(attacker_atk=50, defender_def=40, crit_chance=0)

        assert result2.damage < result1.damage

    def test_zero_attack_deals_minimum_damage(self):
        """Test that zero attack still deals minimum damage."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(attacker_atk=0, defender_def=30, crit_chance=0)

        assert result.damage == 1  # Minimum damage

    def test_zero_defense_uses_safe_minimum(self):
        """Test that zero defense uses safe minimum in formula."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(attacker_atk=50, defender_def=0, crit_chance=0)

        assert result.damage >= 1
        assert result.damage <= 9999


# ============================================================================
# Boost Multiplier Tests
# ============================================================================


class TestBoostMultiplier:
    """Tests for Boost Point multipliers."""

    def test_boost_0_no_multiplier(self):
        """Test 0 BP = 1.0x damage."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(attacker_atk=50, defender_def=30, boost_points=0, crit_chance=0)

        assert result.multipliers["boost"] == 1.0

    def test_boost_1_multiplier(self):
        """Test 1 BP = 1.5x damage."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(attacker_atk=50, defender_def=30, boost_points=1, crit_chance=0)

        assert result.multipliers["boost"] == 1.5

    def test_boost_2_multiplier(self):
        """Test 2 BP = 2.0x damage."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(attacker_atk=50, defender_def=30, boost_points=2, crit_chance=0)

        assert result.multipliers["boost"] == 2.0

    def test_boost_3_multiplier(self):
        """Test 3 BP = 2.5x damage."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(attacker_atk=50, defender_def=30, boost_points=3, crit_chance=0)

        assert result.multipliers["boost"] == 2.5

    def test_boost_increases_damage_proportionally(self):
        """Test boost increases damage by expected multiplier."""
        calc1 = DamageCalculator(rng_seed=42)
        calc2 = DamageCalculator(rng_seed=42)

        result_no_boost = calc1.calculate(
            attacker_atk=50, defender_def=30, boost_points=0, crit_chance=0
        )
        result_boost_2 = calc2.calculate(
            attacker_atk=50, defender_def=30, boost_points=2, crit_chance=0
        )

        # Boost 2 should be ~2.0x damage of no boost
        ratio = result_boost_2.damage / result_no_boost.damage
        assert pytest.approx(ratio, abs=0.1) == 2.0


# ============================================================================
# Type Effectiveness Tests
# ============================================================================


class TestTypeEffectiveness:
    """Tests for type effectiveness multiplier."""

    def test_no_weakness_normal_damage(self):
        """Test damage with no weakness hit."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(
            attacker_atk=50,
            defender_def=30,
            damage_type=DamageType.PHYSICAL,
            defender_weaknesses=[DamageType.FIRE],
            crit_chance=0,
        )

        assert result.is_weakness is False
        assert result.multipliers["type"] == 1.0

    def test_weakness_hit_doubles_damage(self):
        """Test hitting weakness doubles damage."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(
            attacker_atk=50,
            defender_def=30,
            damage_type=DamageType.FIRE,
            defender_weaknesses=[DamageType.FIRE],
            crit_chance=0,
        )

        assert result.is_weakness is True
        assert result.multipliers["type"] == 2.0

    def test_multiple_weaknesses(self):
        """Test enemy can have multiple weaknesses."""
        calc = DamageCalculator(rng_seed=42)

        weaknesses = [DamageType.FIRE, DamageType.ICE, DamageType.LIGHTNING]

        # Test hitting each weakness
        for weakness in weaknesses:
            result = calc.calculate(
                attacker_atk=50,
                defender_def=30,
                damage_type=weakness,
                defender_weaknesses=weaknesses,
                crit_chance=0,
            )

            assert result.is_weakness is True

    def test_weakness_damage_is_double(self):
        """Test weakness damage is approximately double."""
        calc1 = DamageCalculator(rng_seed=42)
        calc2 = DamageCalculator(rng_seed=42)

        result_normal = calc1.calculate(
            attacker_atk=50,
            defender_def=30,
            damage_type=DamageType.PHYSICAL,
            defender_weaknesses=[DamageType.FIRE],
            crit_chance=0,
        )

        result_weakness = calc2.calculate(
            attacker_atk=50,
            defender_def=30,
            damage_type=DamageType.FIRE,
            defender_weaknesses=[DamageType.FIRE],
            crit_chance=0,
        )

        ratio = result_weakness.damage / result_normal.damage
        assert pytest.approx(ratio, abs=0.1) == 2.0


# ============================================================================
# Critical Hit Tests
# ============================================================================


class TestCriticalHits:
    """Tests for critical hit mechanics."""

    def test_zero_crit_chance_never_crits(self):
        """Test 0% crit chance never produces crits."""
        calc = DamageCalculator(rng_seed=42)

        # Test many attacks
        for _ in range(100):
            result = calc.calculate(attacker_atk=50, defender_def=30, crit_chance=0)
            assert result.is_critical is False

    def test_hundred_crit_chance_always_crits(self):
        """Test 100% crit chance always produces crits."""
        calc = DamageCalculator(rng_seed=42)

        # Test many attacks
        for _ in range(20):
            result = calc.calculate(attacker_atk=50, defender_def=30, crit_chance=100)
            assert result.is_critical is True

    def test_crit_multiplier(self):
        """Test critical hit applies 1.5x multiplier."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(
            attacker_atk=50,
            defender_def=30,
            crit_chance=100,  # Force crit
        )

        assert result.multipliers["critical"] == 1.5

    def test_no_crit_multiplier_is_one(self):
        """Test non-crit has 1.0x multiplier."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(
            attacker_atk=50,
            defender_def=30,
            crit_chance=0,  # No crits
        )

        assert result.multipliers["critical"] == 1.0


# ============================================================================
# Break Bonus Tests
# ============================================================================


class TestBreakBonus:
    """Tests for break bonus multiplier."""

    def test_not_broken_normal_damage(self):
        """Test non-broken enemy takes normal damage."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(
            attacker_atk=50,
            defender_def=30,
            defender_is_broken=False,
            crit_chance=0,
        )

        assert result.multipliers["break"] == 1.0

    def test_broken_bonus_damage(self):
        """Test broken enemy takes 1.5x damage."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(
            attacker_atk=50, defender_def=30, defender_is_broken=True, crit_chance=0
        )

        assert result.multipliers["break"] == 1.5

    def test_break_increases_damage(self):
        """Test break bonus increases damage by ~1.5x."""
        calc1 = DamageCalculator(rng_seed=42)
        calc2 = DamageCalculator(rng_seed=42)

        result_normal = calc1.calculate(
            attacker_atk=50,
            defender_def=30,
            defender_is_broken=False,
            crit_chance=0,
        )

        result_broken = calc2.calculate(
            attacker_atk=50, defender_def=30, defender_is_broken=True, crit_chance=0
        )

        ratio = result_broken.damage / result_normal.damage
        assert pytest.approx(ratio, abs=0.1) == 1.5


# ============================================================================
# Combined Multipliers Tests
# ============================================================================


class TestCombinedMultipliers:
    """Tests for multiple multipliers combined."""

    def test_all_multipliers_combined(self):
        """Test all multipliers stack multiplicatively."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(
            attacker_atk=50,
            defender_def=30,
            boost_points=2,  # 2.0x
            damage_type=DamageType.FIRE,
            defender_weaknesses=[DamageType.FIRE],  # 2.0x
            defender_is_broken=True,  # 1.5x
            crit_chance=100,  # 1.5x (forced crit)
        )

        # Total multiplier: 2.0 * 2.0 * 1.5 * 1.5 = 9.0x
        assert result.multipliers["boost"] == 2.0
        assert result.multipliers["type"] == 2.0
        assert result.multipliers["critical"] == 1.5
        assert result.multipliers["break"] == 1.5
        assert result.is_critical is True
        assert result.is_weakness is True

    def test_boost_plus_weakness(self):
        """Test boost and weakness combine."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(
            attacker_atk=50,
            defender_def=30,
            boost_points=1,  # 1.5x
            damage_type=DamageType.ICE,
            defender_weaknesses=[DamageType.ICE],  # 2.0x
            crit_chance=0,
        )

        # Total: 1.5 * 2.0 = 3.0x
        assert result.multipliers["boost"] == 1.5
        assert result.multipliers["type"] == 2.0


# ============================================================================
# Damage Clamping Tests
# ============================================================================


class TestDamageClamping:
    """Tests for damage clamping to [1, 9999] range."""

    def test_minimum_damage_is_one(self):
        """Test damage never goes below 1."""
        calc = DamageCalculator(rng_seed=42)

        # Very weak attack
        result = calc.calculate(attacker_atk=1, defender_def=100, skill_power=1, crit_chance=0)

        assert result.damage >= 1

    def test_maximum_damage_is_9999(self):
        """Test damage never exceeds 9999."""
        calc = DamageCalculator(rng_seed=42)

        # Very strong attack
        result = calc.calculate(
            attacker_atk=9999,
            defender_def=1,
            skill_power=9999,
            boost_points=3,
            damage_type=DamageType.FIRE,
            defender_weaknesses=[DamageType.FIRE],
            defender_is_broken=True,
            crit_chance=100,
        )

        assert result.damage <= 9999

    def test_damage_in_valid_range(self):
        """Test all damage is in valid range."""
        calc = DamageCalculator(rng_seed=42)

        for _ in range(100):
            result = calc.calculate(attacker_atk=50, defender_def=30, crit_chance=5)

            assert 1 <= result.damage <= 9999


# ============================================================================
# Determinism Tests
# ============================================================================


class TestDeterminism:
    """Tests for deterministic damage calculation."""

    def test_same_seed_same_damage(self):
        """Test same seed produces identical damage."""
        calc1 = DamageCalculator(rng_seed=42)
        calc2 = DamageCalculator(rng_seed=42)

        result1 = calc1.calculate(attacker_atk=50, defender_def=30, crit_chance=5)
        result2 = calc2.calculate(attacker_atk=50, defender_def=30, crit_chance=5)

        assert result1.damage == result2.damage
        assert result1.is_critical == result2.is_critical
        assert result1.random_factor == result2.random_factor

    def test_different_seeds_different_damage(self):
        """Test different seeds produce different damage (usually)."""
        calc1 = DamageCalculator(rng_seed=42)
        calc2 = DamageCalculator(rng_seed=99)

        result1 = calc1.calculate(attacker_atk=50, defender_def=30, crit_chance=5)
        result2 = calc2.calculate(attacker_atk=50, defender_def=30, crit_chance=5)

        # With random variance, these should differ
        assert result1.random_factor != result2.random_factor

    def test_sequence_reproducible(self):
        """Test sequence of calculations is reproducible."""
        calc1 = DamageCalculator(rng_seed=42)
        calc2 = DamageCalculator(rng_seed=42)

        results1 = [
            calc1.calculate(attacker_atk=50, defender_def=30, crit_chance=5) for _ in range(10)
        ]
        results2 = [
            calc2.calculate(attacker_atk=50, defender_def=30, crit_chance=5) for _ in range(10)
        ]

        for r1, r2 in zip(results1, results2, strict=False):
            assert r1.damage == r2.damage
            assert r1.is_critical == r2.is_critical


# ============================================================================
# Expected Damage Tests
# ============================================================================


class TestExpectedDamage:
    """Tests for expected damage calculation."""

    def test_expected_damage_no_randomness(self):
        """Test expected damage uses average random factor."""
        calc = DamageCalculator(rng_seed=42)

        expected = calc.calculate_expected_damage(attacker_atk=50, defender_def=30)

        assert expected >= 1
        assert expected <= 9999

    def test_expected_damage_with_boost(self):
        """Test expected damage with boost multiplier."""
        calc = DamageCalculator(rng_seed=42)

        expected_normal = calc.calculate_expected_damage(
            attacker_atk=50, defender_def=30, boost_points=0
        )
        expected_boost = calc.calculate_expected_damage(
            attacker_atk=50, defender_def=30, boost_points=2
        )

        # Boost 2 should be 2x
        assert pytest.approx(expected_boost / expected_normal, abs=0.01) == 2.0

    def test_expected_damage_with_weakness(self):
        """Test expected damage with weakness."""
        calc = DamageCalculator(rng_seed=42)

        expected_normal = calc.calculate_expected_damage(
            attacker_atk=50,
            defender_def=30,
            damage_type=DamageType.PHYSICAL,
            defender_weaknesses=[DamageType.FIRE],
        )
        expected_weakness = calc.calculate_expected_damage(
            attacker_atk=50,
            defender_def=30,
            damage_type=DamageType.FIRE,
            defender_weaknesses=[DamageType.FIRE],
        )

        # Weakness should be 2x
        assert pytest.approx(expected_weakness / expected_normal, abs=0.01) == 2.0
