"""
Performance benchmarks for damage calculation.

Target: < 0.01ms (10 microseconds) per damage calculation
"""

import time

from src.core.damage import DamageCalculator
from src.entities import DamageType


class TestDamagePerformance:
    """Performance benchmarks for damage calculator."""

    def test_bench_basic_damage_calculation(self):
        """Benchmark: Basic damage calculation < 0.01ms."""
        calc = DamageCalculator(rng_seed=42)

        iterations = 10000
        start = time.perf_counter()

        for _ in range(iterations):
            calc.calculate(attacker_atk=50, defender_def=30)

        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000
        print(f"\n  Average time per calculation: {avg_time_ms:.6f}ms")

        assert avg_time_ms < 0.01, f"Too slow: {avg_time_ms:.6f}ms (target: < 0.01ms)"

    def test_bench_complex_damage_calculation(self):
        """Benchmark: Complex damage with all multipliers < 0.01ms."""
        calc = DamageCalculator(rng_seed=42)

        iterations = 10000
        start = time.perf_counter()

        for _ in range(iterations):
            calc.calculate(
                attacker_atk=75,
                defender_def=45,
                skill_power=150,
                boost_points=2,
                damage_type=DamageType.FIRE,
                defender_weaknesses=[DamageType.FIRE, DamageType.ICE],
                defender_is_broken=True,
                crit_chance=15,
            )

        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000
        print(f"\n  Average time per complex calculation: {avg_time_ms:.6f}ms")

        assert avg_time_ms < 0.01, f"Too slow: {avg_time_ms:.6f}ms (target: < 0.01ms)"

    def test_bench_expected_damage(self):
        """Benchmark: Expected damage calculation < 0.01ms."""
        calc = DamageCalculator(rng_seed=42)

        iterations = 10000
        start = time.perf_counter()

        for _ in range(iterations):
            calc.calculate_expected_damage(
                attacker_atk=50,
                defender_def=30,
                boost_points=2,
                damage_type=DamageType.FIRE,
                defender_weaknesses=[DamageType.FIRE],
                defender_is_broken=True,
            )

        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000
        print(f"\n  Average time per expected damage: {avg_time_ms:.6f}ms")

        assert avg_time_ms < 0.01, f"Too slow: {avg_time_ms:.6f}ms (target: < 0.01ms)"

    def test_bench_sequential_calculations(self):
        """Benchmark: 100 sequential calculations (simulating combat)."""
        calc = DamageCalculator(rng_seed=42)

        start = time.perf_counter()

        for _ in range(100):
            calc.calculate(attacker_atk=50, defender_def=30, crit_chance=5)

        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        avg_time_ms = total_time_ms / 100

        print(f"\n  Total time for 100 calculations: {total_time_ms:.3f}ms")
        print(f"\n  Average time per calculation: {avg_time_ms:.6f}ms")

        # 100 calculations should be under 1ms total
        assert total_time_ms < 1.0, f"Too slow: {total_time_ms:.3f}ms"
