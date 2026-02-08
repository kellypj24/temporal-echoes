"""
Performance benchmarks for combat system.

Targets:
- AI decision: < 0.1ms per decision
- Full combat: < 100ms per combat
"""

import random
import time
from typing import Any

from src.core.ai import AIArchetype, CombatAction, CombatState, create_enemy_ai
from src.core.combat import CombatContext, CombatPhase
from src.core.persistence import EventStore
from src.entities import DamageType, Enemy, Player


def _make_player(**kwargs: Any) -> Player:
    defaults: dict[str, Any] = {
        "id": "player_1",
        "name": "Hero",
        "level": 10,
        "hp": 300,
        "max_hp": 300,
        "attack": 50,
        "defense": 30,
        "speed": 40,
    }
    defaults.update(kwargs)
    return Player(**defaults)


def _make_enemy(**kwargs: Any) -> Enemy:
    defaults: dict[str, Any] = {
        "id": "enemy_1",
        "name": "Goblin",
        "level": 8,
        "hp": 200,
        "max_hp": 200,
        "attack": 40,
        "defense": 25,
        "speed": 30,
        "shield_points": 3,
        "max_shield_points": 3,
        "weaknesses": [DamageType.FIRE, DamageType.ICE],
        "archetype": "aggressive",
    }
    defaults.update(kwargs)
    return Enemy(**defaults)


class TestCombatBenchmarks:
    """Performance benchmarks for combat subsystems."""

    def test_bench_ai_decision(self) -> None:
        """Benchmark: AI decision < 0.1ms average over 10K iterations."""
        enemy = _make_enemy()
        rng = random.Random(42)
        ai = create_enemy_ai(enemy, AIArchetype.AGGRESSIVE, rng)

        player = _make_player()
        state = CombatState(player=player, enemies=[enemy], round_number=1)

        iterations = 10_000
        start = time.perf_counter()

        for _ in range(iterations):
            ai.select_action(state)

        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / iterations) * 1000

        print(f"\n  AI decision avg: {avg_ms:.6f}ms")
        assert avg_ms < 0.1, f"Too slow: {avg_ms:.6f}ms (target: < 0.1ms)"

    def test_bench_full_combat(self) -> None:
        """Benchmark: Full combat < 100ms average over 100 combats."""
        iterations = 100
        start = time.perf_counter()

        for i in range(iterations):
            player = _make_player(attack=60, speed=50)
            enemy = _make_enemy(hp=100, max_hp=100, speed=30)
            store = EventStore(":memory:")
            ctx = CombatContext(
                combat_id=f"bench_{i}",
                seed=i,
                player=player,
                enemies=[enemy],
                event_store=store,
                session_id="bench_sess",
                timeline_id="bench_tl",
            )

            for _ in range(50):
                if ctx.is_over:
                    break
                ctx.start_round()
                while not ctx.is_over and ctx.phase != CombatPhase.ROUND_END:
                    current = ctx.current_combatant
                    if isinstance(current, Player):
                        action = CombatAction(
                            action_type="attack",
                            target_id=enemy.id,
                        )
                        ctx.submit_player_action(action)
                    elif isinstance(current, Enemy):
                        ctx.execute_enemy_turn(current)
                    ctx.advance_turn()
                    if ctx.is_over:
                        break

        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / iterations) * 1000

        print(f"\n  Full combat avg: {avg_ms:.3f}ms")
        assert avg_ms < 100, f"Too slow: {avg_ms:.3f}ms (target: < 100ms)"

    def test_bench_ai_decision_all_archetypes(self) -> None:
        """Benchmark: All 4 AI archetypes decide within 0.1ms."""
        archetypes = [
            AIArchetype.AGGRESSIVE,
            AIArchetype.DEFENSIVE,
            AIArchetype.TACTICAL,
            AIArchetype.BERSERKER,
        ]

        for archetype in archetypes:
            enemy = _make_enemy()
            rng = random.Random(42)
            ai = create_enemy_ai(enemy, archetype, rng)

            player = _make_player()
            state = CombatState(player=player, enemies=[enemy], round_number=1)

            iterations = 5_000
            start = time.perf_counter()
            for _ in range(iterations):
                ai.select_action(state)
            elapsed = time.perf_counter() - start
            avg_ms = (elapsed / iterations) * 1000

            print(f"\n  {archetype.name} AI avg: {avg_ms:.6f}ms")
            assert avg_ms < 0.1, f"{archetype.name} too slow: {avg_ms:.6f}ms (target: < 0.1ms)"
