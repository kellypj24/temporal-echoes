"""
Property-based tests for damage calculation.

These tests verify invariants that should always hold true:
- Damage is always in range [1, 9999]
- Higher attack always increases damage (with same seed)
- Higher defense always decreases damage (with same seed)
- Multipliers always increase damage
- Determinism holds across all parameter combinations
"""

from src.core.damage import DamageCalculator
from src.entities import DamageType


class TestDamageProperties:
    """Property-based tests for damage calculation invariants."""

    def test_damage_always_in_valid_range(self):
        """Test damage is always between 1 and 9999."""
        calc = DamageCalculator(rng_seed=42)

        # Test with many different parameter combinations
        test_cases = [
            {"attacker_atk": 1, "defender_def": 1},
            {"attacker_atk": 1, "defender_def": 999},
            {"attacker_atk": 999, "defender_def": 1},
            {"attacker_atk": 999, "defender_def": 999},
            {"attacker_atk": 50, "defender_def": 30},
            {"attacker_atk": 0, "defender_def": 0},
            {"attacker_atk": 0, "defender_def": 100},
            {"attacker_atk": 100, "defender_def": 0},
        ]

        for params in test_cases:
            result = calc.calculate(**params, crit_chance=0)
            assert 1 <= result.damage <= 9999, f"Damage {result.damage} out of range for {params}"

    def test_damage_never_negative(self):
        """Test damage is never negative even with extreme parameters."""
        calc = DamageCalculator(rng_seed=42)

        # Very weak attack vs very high defense
        result = calc.calculate(attacker_atk=1, defender_def=9999, skill_power=1, crit_chance=0)

        assert result.damage >= 1

    def test_higher_attack_increases_damage(self):
        """Test that increasing attack always increases damage (same RNG)."""
        attack_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        previous_damage = 0

        for atk in attack_values:
            calc = DamageCalculator(rng_seed=42)  # Same seed for each
            result = calc.calculate(attacker_atk=atk, defender_def=30, crit_chance=0)

            assert result.damage >= previous_damage, (
                f"Damage decreased: {atk} ATK -> {result.damage} (prev: {previous_damage})"
            )
            previous_damage = result.damage

    def test_higher_defense_decreases_damage(self):
        """Test that increasing defense always decreases damage (same RNG)."""
        defense_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        previous_damage = 9999

        for def_val in defense_values:
            calc = DamageCalculator(rng_seed=42)  # Same seed for each
            result = calc.calculate(attacker_atk=50, defender_def=def_val, crit_chance=0)

            assert result.damage <= previous_damage, (
                f"Damage increased: {def_val} DEF -> {result.damage} (prev: {previous_damage})"
            )
            previous_damage = result.damage

    def test_boost_always_increases_damage(self):
        """Test that higher boost always increases damage."""
        boost_values = [0, 1, 2, 3]
        previous_damage = 0

        for boost in boost_values:
            calc = DamageCalculator(rng_seed=42)  # Same seed
            result = calc.calculate(
                attacker_atk=50, defender_def=30, boost_points=boost, crit_chance=0
            )

            assert result.damage >= previous_damage, f"Damage decreased with boost {boost}"
            previous_damage = result.damage

    def test_weakness_always_increases_damage(self):
        """Test that hitting weakness always increases damage."""
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

        assert result_weakness.damage >= result_normal.damage

    def test_break_always_increases_damage(self):
        """Test that break bonus always increases damage."""
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

        assert result_broken.damage >= result_normal.damage

    def test_critical_always_increases_damage(self):
        """Test that critical hits always increase damage."""
        calc1 = DamageCalculator(rng_seed=42)
        calc2 = DamageCalculator(rng_seed=42)

        result_normal = calc1.calculate(
            attacker_atk=50,
            defender_def=30,
            crit_chance=0,  # No crits
        )

        result_crit = calc2.calculate(
            attacker_atk=50,
            defender_def=30,
            crit_chance=100,  # Guaranteed crit
        )

        assert result_crit.damage >= result_normal.damage

    def test_all_multipliers_at_least_1x(self):
        """Test that all multipliers are at least 1.0x."""
        calc = DamageCalculator(rng_seed=42)

        # Test with no bonuses
        result = calc.calculate(
            attacker_atk=50,
            defender_def=30,
            boost_points=0,
            defender_is_broken=False,
            crit_chance=0,
        )

        assert result.multipliers["boost"] >= 1.0
        assert result.multipliers["type"] >= 1.0
        assert result.multipliers["critical"] >= 1.0
        assert result.multipliers["break"] >= 1.0

    def test_random_factor_always_in_range(self):
        """Test random factor is always in [0.85, 1.00] range."""
        calc = DamageCalculator(rng_seed=42)

        for _ in range(100):
            result = calc.calculate(attacker_atk=50, defender_def=30, crit_chance=0)

            assert 0.85 <= result.random_factor <= 1.00, (
                f"Random factor {result.random_factor} out of range"
            )

    def test_determinism_with_all_parameters(self):
        """Test determinism holds with all parameter combinations."""
        # Complex parameter set
        params = {
            "attacker_atk": 75,
            "defender_def": 45,
            "skill_power": 150,
            "boost_points": 2,
            "damage_type": DamageType.FIRE,
            "defender_weaknesses": [DamageType.FIRE, DamageType.ICE],
            "defender_is_broken": True,
            "crit_chance": 15,
        }

        calc1 = DamageCalculator(rng_seed=123)
        calc2 = DamageCalculator(rng_seed=123)

        result1 = calc1.calculate(**params)
        result2 = calc2.calculate(**params)

        assert result1.damage == result2.damage
        assert result1.is_critical == result2.is_critical
        assert result1.is_weakness == result2.is_weakness
        assert result1.random_factor == result2.random_factor

    def test_damage_result_has_all_required_fields(self):
        """Test DamageResult always has all required fields."""
        calc = DamageCalculator(rng_seed=42)

        result = calc.calculate(attacker_atk=50, defender_def=30)

        assert hasattr(result, "damage")
        assert hasattr(result, "is_critical")
        assert hasattr(result, "is_weakness")
        assert hasattr(result, "multipliers")
        assert hasattr(result, "random_factor")

        assert isinstance(result.damage, int)
        assert isinstance(result.is_critical, bool)
        assert isinstance(result.is_weakness, bool)
        assert isinstance(result.multipliers, dict)
        assert isinstance(result.random_factor, float)

    def test_expected_damage_always_positive(self):
        """Test expected damage is always positive."""
        calc = DamageCalculator(rng_seed=42)

        test_cases = [
            {"attacker_atk": 1, "defender_def": 1},
            {"attacker_atk": 0, "defender_def": 100},
            {"attacker_atk": 100, "defender_def": 0},
            {"attacker_atk": 50, "defender_def": 50},
        ]

        for params in test_cases:
            expected = calc.calculate_expected_damage(**params)
            assert expected >= 1, f"Expected damage {expected} < 1 for {params}"

    def test_expected_damage_in_valid_range(self):
        """Test expected damage is in valid range."""
        calc = DamageCalculator(rng_seed=42)

        for atk in [1, 10, 50, 100, 500]:
            for def_val in [1, 10, 50, 100, 500]:
                expected = calc.calculate_expected_damage(attacker_atk=atk, defender_def=def_val)
                assert 1 <= expected <= 9999, (
                    f"Expected {expected} out of range (ATK={atk}, DEF={def_val})"
                )
