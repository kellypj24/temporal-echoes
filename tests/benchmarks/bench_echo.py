"""
Performance benchmark for Phase 3 Step 5 Echo Cast.

Constitution principle 14: 60 FPS target = <16ms frame time. An echo act is
a dict lookup + one take_damage + 1-3 event appends — no RNG, no replay, no
extra store reads. This benchmark proves cast + a full 3-act lifetime
completes well inside the frame budget on an in-memory SQLite store.
"""

from __future__ import annotations

import statistics
import time

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatPhase
from src.core.persistence import EventStore
from tests.fixtures.combat_fixtures import create_combat_context
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player


def _build_castable_combat(i: int) -> CombatContext:
    """
    Build a CombatContext with 3 recorded player attacks and enough banked
    charge for a full 3-turn echo cast, positioned for a direct cast call.

    Args:
        i: Iteration index used as the RNG seed.

    Returns:
        CombatContext with a 3-entry player action history and 2 charge.
    """
    store = EventStore(":memory:")
    player = create_test_player(
        hp=100_000, max_hp=100_000, temporal_charge=0, max_temporal_charge=5, attack=50
    )
    enemy = create_test_enemy(hp=100_000, max_hp=100_000, defense=25)
    combat = create_combat_context(seed=i, player=player, enemies=[enemy], event_store=store)

    combat.start_round()
    for _ in range(3):
        combat.submit_player_action(CombatAction(action_type="attack", target_id="enemy_1"))
        combat.advance_turn()
        if combat.phase == CombatPhase.EXECUTING_TURN:
            combat.execute_enemy_turn(combat.current_combatant)
            combat.advance_turn()
        if combat.phase in (CombatPhase.ROUND_START, CombatPhase.ROUND_END):
            combat.start_round()

    combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
    combat.player.temporal_charge = 2
    return combat


class TestEchoBenchmark:
    """Frame-budget proof: cast + full 3-act lifetime completes in <16ms median.

    Lives in tests/benchmarks/ as a bench_*.py file, so it is NOT collected
    by the default suite (just test). Run it via `just bench`.
    """

    def test_bench_echo_cast_and_lifetime_under_16ms(self) -> None:
        """
        Benchmark: echo_cast(turns=3) + 3 execute_echo_turn acts, median
        < 16ms over 100 iterations.

        Each iteration constructs a fresh CombatContext with a 3-entry
        history, casts a 3-turn echo, then drives all 3 acts to expiry.
        """
        iterations = 100
        timings: list[float] = []

        for i in range(iterations):
            combat = _build_castable_combat(i)

            t0 = time.perf_counter()
            combat._temporal.echo_cast(combat, combat.player, turns=3)
            for _ in range(3):
                combat._temporal.execute_echo_turn(combat, combat.player)
            t1 = time.perf_counter()

            timings.append((t1 - t0) * 1000)  # convert to ms

        median_ms = statistics.median(timings)
        p95_ms = sorted(timings)[int(iterations * 0.95)]

        print(f"\n  Echo cast+lifetime median: {median_ms:.3f}ms  p95: {p95_ms:.3f}ms")
        assert median_ms < 16.0, (
            f"Echo cast+lifetime median {median_ms:.3f}ms exceeds 16ms frame budget"
        )
