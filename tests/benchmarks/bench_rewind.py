"""
Performance benchmark for Phase 3 Step 3 single-turn rewind.

Constitution principle 14: 60 FPS target = <16ms frame time.
Rewind must complete in <16ms (median over 100 iterations) on an
in-memory SQLite store. This benchmark proves the frame budget holds.
"""

from __future__ import annotations

import statistics
import time

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatPhase
from src.core.persistence import EventStore
from tests.fixtures.combat_fixtures import create_combat_context
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player


def _build_rewindable_combat(i: int) -> CombatContext:
    """
    Create a CombatContext with one completed player turn, positioned
    for a rewind. Uses seed ``i`` for variety.

    Args:
        i: Iteration index used as the RNG seed.

    Returns:
        CombatContext at total_turns=1, AWAITING_PLAYER_INPUT, charge=1.
    """
    store = EventStore(":memory:")
    player = create_test_player(temporal_charge=3, max_temporal_charge=3)
    enemy = create_test_enemy()
    combat = create_combat_context(seed=i, player=player, enemies=[enemy], event_store=store)
    combat.start_round()
    combat.submit_player_action(CombatAction(action_type="attack", target_id="enemy_1"))
    combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
    combat.player.temporal_charge = 1
    return combat


class TestRewindBenchmark:
    """Frame-budget proof: rewind(turns=1) completes in <16ms median.

    Lives in tests/benchmarks/ as a bench_*.py file, so it is NOT collected
    by the default suite (just test). Run it via `just bench`. See the
    "Benchmarks vs tests" note in README / CLAUDE.md for the rationale.
    """

    def test_bench_rewind_under_16ms(self) -> None:
        """
        Benchmark: single-turn rewind median < 16ms over 100 iterations.

        Each iteration constructs a fresh CombatContext with one completed
        turn, then times rewind_to_turn(0). Median latency must satisfy the
        60 FPS frame budget (Constitution principle 14).
        """
        iterations = 100
        timings: list[float] = []

        for i in range(iterations):
            combat = _build_rewindable_combat(i)
            target = combat._total_turns - 1

            t0 = time.perf_counter()
            combat.rewind_to_turn(target)
            t1 = time.perf_counter()

            timings.append((t1 - t0) * 1000)  # convert to ms

        median_ms = statistics.median(timings)
        p95_ms = sorted(timings)[int(iterations * 0.95)]

        print(f"\n  Rewind median: {median_ms:.3f}ms  p95: {p95_ms:.3f}ms")
        assert median_ms < 16.0, f"Rewind median {median_ms:.3f}ms exceeds 16ms frame budget"
