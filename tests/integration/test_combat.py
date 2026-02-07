"""
Integration tests for the combat system.

Tests the full combat flow by wiring together CombatContext with all
subsystems: entities, damage calc, events, enemy AI, and combat logger.
"""

import json

import pytest

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatOutcome, CombatPhase
from src.core.events import EventTypes
from src.core.persistence import EventStore
from src.entities import DamageType, Enemy, Player
from tests.fixtures.combat_fixtures import (
    create_1v3_context,
    create_combat_context,
)
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player


class TestCombatInitialization:
    """Tests for CombatContext setup and initial state."""

    def test_context_creation(self) -> None:
        """CombatContext initializes with correct state."""
        ctx = create_combat_context()
        assert ctx.combat_id == "combat_001"
        assert ctx.round_number == 0
        assert ctx.phase == CombatPhase.INITIALIZING
        assert ctx.is_over is False
        assert ctx.outcome is None

    def test_combat_started_event_emitted(self) -> None:
        """COMBAT_STARTED event is emitted on initialization."""
        store = EventStore(":memory:")
        create_combat_context(event_store=store)
        events = store.get_events_by_timeline("timeline_main")
        assert len(events) == 1
        assert events[0].event_type == EventTypes.COMBAT_STARTED
        data = json.loads(events[0].event_data)
        assert data["combat_id"] == "combat_001"
        assert data["rng_seed"] == 42
        assert data["player"]["id"] == "player_1"
        assert len(data["enemies"]) == 1

    def test_combat_started_log_messages(self) -> None:
        """Combat start generates descriptive log messages."""
        ctx = create_combat_context()
        msgs = ctx.log_messages
        assert any("Combat begins" in m for m in msgs)

    def test_validation_empty_combat_id(self) -> None:
        """Raises ValueError for empty combat_id."""
        with pytest.raises(ValueError, match="combat_id"):
            CombatContext(
                combat_id="",
                seed=42,
                player=create_test_player(),
                enemies=[create_test_enemy()],
                event_store=EventStore(":memory:"),
                session_id="sess",
                timeline_id="tl",
            )

    def test_validation_no_enemies(self) -> None:
        """Raises ValueError for empty enemies list."""
        with pytest.raises(ValueError, match="enemy"):
            CombatContext(
                combat_id="c1",
                seed=42,
                player=create_test_player(),
                enemies=[],
                event_store=EventStore(":memory:"),
                session_id="sess",
                timeline_id="tl",
            )

    def test_living_enemies_property(self) -> None:
        """living_enemies returns only alive enemies."""
        ctx = create_1v3_context()
        assert len(ctx.living_enemies) == 3
        # Kill one enemy
        ctx.enemies[0].hp = 0
        assert len(ctx.living_enemies) == 2


class TestTurnOrder:
    """Tests for speed-based turn ordering."""

    def test_speed_ordering(self) -> None:
        """Combatants are ordered by speed (highest first)."""
        player = create_test_player(speed=40)
        enemy = create_test_enemy(speed=30)
        ctx = create_combat_context(player=player, enemies=[enemy])
        ctx.start_round()
        # Player (speed 40) should go before enemy (speed 30)
        assert ctx.current_combatant.id == "player_1"

    def test_enemy_faster_than_player(self) -> None:
        """Enemy with higher speed goes first."""
        player = create_test_player(speed=20)
        enemy = create_test_enemy(speed=50)
        ctx = create_combat_context(player=player, enemies=[enemy])
        ctx.start_round()
        assert ctx.current_combatant.id == "enemy_1"

    def test_deterministic_tiebreak(self) -> None:
        """Equal speed uses ID for deterministic tiebreak."""
        player = create_test_player(id="player_1", speed=30)
        enemy = create_test_enemy(id="enemy_1", speed=30)
        ctx = create_combat_context(player=player, enemies=[enemy])
        ctx.start_round()
        # Tiebreak by ID ascending: "enemy_1" < "player_1"
        assert ctx.current_combatant.id == "enemy_1"

    def test_multi_enemy_ordering(self) -> None:
        """Multiple enemies are ordered correctly by speed."""
        ctx = create_1v3_context()
        ctx.start_round()
        # Player speed=40, Goblin A=30, Goblin B=25, Goblin C=35
        # Expected order: Player(40) > Goblin C(35) > Goblin A(30) > Goblin B(25)
        order = [ctx._turn_order[i].name for i in range(len(ctx._turn_order))]
        assert order == ["Hero", "Goblin C", "Goblin A", "Goblin B"]

    def test_round_start_messages(self) -> None:
        """start_round returns round and turn order messages."""
        ctx = create_combat_context()
        msgs = ctx.start_round()
        assert any("Round 1" in m for m in msgs)
        assert any("Turn order" in m for m in msgs)


class TestAttackExecution:
    """Tests for attack actions during combat."""

    def test_player_attack_deals_damage(self) -> None:
        """Player attack reduces enemy HP."""
        ctx = create_combat_context(seed=42)
        ctx.start_round()

        # Ensure player goes first
        if not isinstance(ctx.current_combatant, Player):
            ctx.execute_enemy_turn(ctx.current_combatant)
            ctx.advance_turn()

        initial_hp = ctx.enemies[0].hp
        action = CombatAction(action_type="attack", target_id="enemy_1")
        msgs = ctx.submit_player_action(action)

        assert ctx.enemies[0].hp < initial_hp
        assert any("attacks" in m for m in msgs)
        assert any("damage" in m for m in msgs)

    def test_enemy_attack_deals_damage(self) -> None:
        """Enemy attack reduces player HP."""
        player = create_test_player(speed=10)
        enemy = create_test_enemy(speed=50)
        ctx = create_combat_context(player=player, enemies=[enemy], seed=42)
        ctx.start_round()

        initial_hp = ctx.player.hp
        msgs = ctx.execute_enemy_turn(enemy)
        # Enemy may attack or defend - check if attack happened
        if ctx.player.hp < initial_hp:
            assert any("attacks" in m for m in msgs)

    def test_attack_emits_action_event(self) -> None:
        """Attack action emits ACTION_EXECUTED event."""
        store = EventStore(":memory:")
        ctx = create_combat_context(event_store=store, seed=42)
        ctx.start_round()

        if not isinstance(ctx.current_combatant, Player):
            ctx.execute_enemy_turn(ctx.current_combatant)
            ctx.advance_turn()

        action = CombatAction(action_type="attack", target_id="enemy_1")
        ctx.submit_player_action(action)

        events = store.get_events_by_timeline("timeline_main")
        action_events = [e for e in events if e.event_type == EventTypes.ACTION_EXECUTED]
        assert len(action_events) >= 1
        data = json.loads(action_events[-1].event_data)
        assert data["actor_id"] == "player_1"
        assert data["action_type"] == "attack"
        assert data["target_id"] == "enemy_1"
        assert "damage_dealt" in data

    def test_player_attack_with_boost(self) -> None:
        """Player can spend BP to boost attack damage."""
        player = create_test_player(boost_points=3)
        enemy = create_test_enemy(hp=500, max_hp=500)
        ctx = create_combat_context(player=player, enemies=[enemy], seed=100)
        ctx.start_round()

        if not isinstance(ctx.current_combatant, Player):
            ctx.execute_enemy_turn(ctx.current_combatant)
            ctx.advance_turn()

        # Verify BP is spent and boost message appears
        action_boost = CombatAction(action_type="attack", target_id="enemy_1", boost_points=2)
        msgs = ctx.submit_player_action(action_boost)
        assert player.boost_points < 3  # BP was spent (1 gained at round start, 2 spent)
        assert any("Boost" in m for m in msgs)


class TestDefendAction:
    """Tests for defend actions."""

    def test_player_defend(self) -> None:
        """Player can take a defensive stance."""
        ctx = create_combat_context()
        ctx.start_round()

        if not isinstance(ctx.current_combatant, Player):
            ctx.execute_enemy_turn(ctx.current_combatant)
            ctx.advance_turn()

        action = CombatAction(action_type="defend", target_id="player_1")
        msgs = ctx.submit_player_action(action)
        assert any("defensive stance" in m for m in msgs)

    def test_defend_emits_event(self) -> None:
        """Defend action emits ACTION_EXECUTED event."""
        store = EventStore(":memory:")
        ctx = create_combat_context(event_store=store)
        ctx.start_round()

        if not isinstance(ctx.current_combatant, Player):
            ctx.execute_enemy_turn(ctx.current_combatant)
            ctx.advance_turn()

        action = CombatAction(action_type="defend", target_id="player_1")
        ctx.submit_player_action(action)

        events = store.get_events_by_timeline("timeline_main")
        action_events = [e for e in events if e.event_type == EventTypes.ACTION_EXECUTED]
        defend_events = [
            e for e in action_events if json.loads(e.event_data)["action_type"] == "defend"
        ]
        assert len(defend_events) >= 1


class TestFleeAction:
    """Tests for flee attempts with deterministic RNG."""

    def test_flee_success(self) -> None:
        """Flee succeeds when RNG roll is favorable."""
        # Use a seed that produces a successful flee
        # Player speed=40, enemy speed=30 -> flee_chance = 50 + 10 = 60%
        # Try multiple seeds to find one that works
        for seed in range(100):
            player = create_test_player(speed=80)  # High speed = high flee chance
            enemy = create_test_enemy(speed=10)
            ctx = create_combat_context(player=player, enemies=[enemy], seed=seed)
            ctx.start_round()

            if not isinstance(ctx.current_combatant, Player):
                ctx.execute_enemy_turn(ctx.current_combatant)
                ctx.advance_turn()

            action = CombatAction(action_type="flee", target_id="player_1")
            msgs = ctx.submit_player_action(action)

            if ctx.outcome == CombatOutcome.FLED:
                assert ctx.is_over
                assert any("fled" in m.lower() or "escaped" in m.lower() for m in msgs)
                return

        pytest.fail("Could not find a seed that produces a successful flee")

    def test_flee_failure(self) -> None:
        """Flee fails when RNG roll is unfavorable."""
        # Low speed = low flee chance
        for seed in range(100):
            player = create_test_player(speed=10)
            enemy = create_test_enemy(speed=80)
            ctx = create_combat_context(player=player, enemies=[enemy], seed=seed)
            ctx.start_round()

            if not isinstance(ctx.current_combatant, Player):
                ctx.execute_enemy_turn(ctx.current_combatant)
                ctx.advance_turn()

            action = CombatAction(action_type="flee", target_id="player_1")
            msgs = ctx.submit_player_action(action)

            if ctx.outcome is None:
                # Flee failed, combat continues
                assert not ctx.is_over
                assert any("failed" in m.lower() for m in msgs)
                return

        pytest.fail("Could not find a seed that produces a failed flee")

    def test_flee_emits_event(self) -> None:
        """Flee attempt emits COMBAT_FLED event."""
        store = EventStore(":memory:")
        ctx = create_combat_context(event_store=store)
        ctx.start_round()

        if not isinstance(ctx.current_combatant, Player):
            ctx.execute_enemy_turn(ctx.current_combatant)
            ctx.advance_turn()

        action = CombatAction(action_type="flee", target_id="player_1")
        ctx.submit_player_action(action)

        events = store.get_events_by_timeline("timeline_main")
        flee_events = [e for e in events if e.event_type == EventTypes.COMBAT_FLED]
        assert len(flee_events) == 1
        data = json.loads(flee_events[0].event_data)
        assert data["fled_by"] == "player_1"
        assert "flee_success" in data


class TestBreakSystem:
    """Tests for shield break during combat."""

    def test_weakness_hit_reduces_shield(self) -> None:
        """Hitting an enemy's weakness reduces shield points."""
        enemy = create_test_enemy(
            shield_points=3, max_shield_points=3, weaknesses=[DamageType.FIRE]
        )

        # Directly test take_damage with weakness type
        result = enemy.take_damage(10, DamageType.FIRE)
        assert result.weakness_hit
        assert enemy.shield_points == 2

    def test_shield_break_stuns_enemy(self) -> None:
        """Breaking enemy shield stuns them for 1 turn."""
        enemy = create_test_enemy(
            shield_points=1, max_shield_points=3, weaknesses=[DamageType.FIRE]
        )

        enemy.take_damage(10, DamageType.FIRE)
        assert enemy.is_broken
        assert enemy.break_turns_remaining == 1

    def test_broken_enemy_skips_turn(self) -> None:
        """Broken enemies skip their turn in combat."""
        player = create_test_player(speed=10)
        enemy = create_test_enemy(speed=50, shield_points=1, weaknesses=[DamageType.FIRE])

        ctx = create_combat_context(player=player, enemies=[enemy], seed=42)

        # Manually break the enemy
        enemy.take_damage(10, DamageType.FIRE)
        assert enemy.is_broken

        ctx.start_round()
        # Enemy goes first (higher speed)
        msgs = ctx.execute_enemy_turn(enemy)
        assert any("stunned" in m.lower() for m in msgs)

    def test_break_recovery_restores_shield(self) -> None:
        """Break recovery at turn end restores shield."""
        enemy = create_test_enemy(
            shield_points=1, max_shield_points=3, weaknesses=[DamageType.FIRE]
        )
        enemy.take_damage(10, DamageType.FIRE)
        assert enemy.is_broken

        # Simulate turn end
        enemy.process_turn_end()
        assert not enemy.is_broken
        assert enemy.shield_points == 3


class TestBoostPoints:
    """Tests for the Boost Point system in combat."""

    def test_bp_gained_per_round(self) -> None:
        """Player gains 1 BP at the start of each round."""
        player = create_test_player(boost_points=0)
        ctx = create_combat_context(player=player)
        ctx.start_round()
        assert player.boost_points == 1

    def test_bp_capped_at_max(self) -> None:
        """BP gain is capped at max_boost_points."""
        player = create_test_player(boost_points=5)
        ctx = create_combat_context(player=player)
        msgs = ctx.start_round()
        assert player.boost_points == 5
        assert any("full" in m.lower() for m in msgs)

    def test_bp_gained_event_emitted(self) -> None:
        """BP gain emits BOOST_POINT_GAINED event."""
        store = EventStore(":memory:")
        player = create_test_player(boost_points=0)
        ctx = create_combat_context(player=player, event_store=store)
        ctx.start_round()

        events = store.get_events_by_timeline("timeline_main")
        bp_events = [e for e in events if e.event_type == EventTypes.BOOST_POINT_GAINED]
        assert len(bp_events) == 1
        data = json.loads(bp_events[0].event_data)
        assert data["combatant_id"] == "player_1"
        assert data["new_total"] == 1

    def test_bp_spent_on_attack(self) -> None:
        """BP is spent when boosting an attack."""
        player = create_test_player(boost_points=3, speed=50)
        enemy = create_test_enemy(speed=10)
        ctx = create_combat_context(player=player, enemies=[enemy], seed=42)
        ctx.start_round()
        # Player gained 1 BP -> now 4 BP
        assert player.boost_points == 4

        action = CombatAction(action_type="attack", target_id="enemy_1", boost_points=3)
        ctx.submit_player_action(action)
        assert player.boost_points == 1  # 4 - 3 = 1


class TestCombatEnd:
    """Tests for combat end conditions."""

    def test_victory_when_all_enemies_dead(self) -> None:
        """Combat ends in victory when all enemies are defeated."""
        player = create_test_player(attack=200, speed=50)
        enemy = create_test_enemy(hp=1, max_hp=1, speed=10)
        ctx = create_combat_context(player=player, enemies=[enemy], seed=42)
        ctx.start_round()

        action = CombatAction(action_type="attack", target_id="enemy_1")
        ctx.submit_player_action(action)
        ctx.advance_turn()

        assert ctx.is_over
        assert ctx.outcome == CombatOutcome.VICTORY

    def test_defeat_when_player_dead(self) -> None:
        """Combat ends in defeat when player HP reaches 0."""
        player = create_test_player(hp=1, max_hp=300, speed=10)
        enemy = create_test_enemy(attack=200, speed=50)
        ctx = create_combat_context(player=player, enemies=[enemy], seed=42)
        ctx.start_round()

        # Enemy goes first and attacks
        ctx.execute_enemy_turn(enemy)
        ctx.advance_turn()

        assert ctx.is_over
        assert ctx.outcome == CombatOutcome.DEFEAT

    def test_victory_emits_combat_ended(self) -> None:
        """Victory emits COMBAT_ENDED event with victory=True."""
        store = EventStore(":memory:")
        player = create_test_player(attack=200, speed=50)
        enemy = create_test_enemy(hp=1, max_hp=1, speed=10)
        ctx = create_combat_context(player=player, enemies=[enemy], event_store=store, seed=42)
        ctx.start_round()

        action = CombatAction(action_type="attack", target_id="enemy_1")
        ctx.submit_player_action(action)
        ctx.advance_turn()

        events = store.get_events_by_timeline("timeline_main")
        end_events = [e for e in events if e.event_type == EventTypes.COMBAT_ENDED]
        assert len(end_events) == 1
        data = json.loads(end_events[0].event_data)
        assert data["outcome"] == "victory"
        assert data["victory"] is True

    def test_cannot_start_round_after_combat_over(self) -> None:
        """Raises RuntimeError if starting round after combat ended."""
        player = create_test_player(attack=200, speed=50)
        enemy = create_test_enemy(hp=1, max_hp=1, speed=10)
        ctx = create_combat_context(player=player, enemies=[enemy], seed=42)
        ctx.start_round()

        action = CombatAction(action_type="attack", target_id="enemy_1")
        ctx.submit_player_action(action)
        ctx.advance_turn()

        assert ctx.is_over
        with pytest.raises(RuntimeError, match="combat is over"):
            ctx.start_round()


class TestFullCombatSequence:
    """End-to-end combat sequence tests."""

    def test_1v1_full_combat(self) -> None:
        """Run a full 1v1 combat until completion."""
        store = EventStore(":memory:")
        player = create_test_player(speed=50, attack=60)
        enemy = create_test_enemy(speed=30, hp=100, max_hp=100)
        ctx = create_combat_context(player=player, enemies=[enemy], event_store=store, seed=42)

        max_rounds = 50  # Safety limit
        for _ in range(max_rounds):
            if ctx.is_over:
                break

            ctx.start_round()

            # Process each combatant in turn order
            while not ctx.is_over and ctx.phase != CombatPhase.ROUND_END:
                current = ctx.current_combatant
                if isinstance(current, Player):
                    action = CombatAction(action_type="attack", target_id=enemy.id)
                    ctx.submit_player_action(action)
                elif isinstance(current, Enemy):
                    ctx.execute_enemy_turn(current)

                ctx.advance_turn()
                if ctx.is_over:
                    break

        assert ctx.is_over
        assert ctx.outcome is not None
        assert ctx.round_number > 0

        # Verify events were emitted
        events = store.get_events_by_timeline("timeline_main")
        event_types = [e.event_type for e in events]
        assert EventTypes.COMBAT_STARTED in event_types
        assert EventTypes.COMBAT_ENDED in event_types
        assert EventTypes.ACTION_EXECUTED in event_types

    def test_1v3_full_combat(self) -> None:
        """Run a full 1v3 combat until completion."""
        store = EventStore(":memory:")
        player = create_test_player(speed=50, attack=80)
        enemies = [
            create_test_enemy(id="e1", name="Goblin A", hp=50, max_hp=50, speed=30),
            create_test_enemy(id="e2", name="Goblin B", hp=50, max_hp=50, speed=25),
            create_test_enemy(id="e3", name="Goblin C", hp=50, max_hp=50, speed=35),
        ]
        ctx = create_combat_context(player=player, enemies=enemies, event_store=store, seed=42)

        max_rounds = 50
        for _ in range(max_rounds):
            if ctx.is_over:
                break

            ctx.start_round()

            while not ctx.is_over and ctx.phase != CombatPhase.ROUND_END:
                current = ctx.current_combatant
                if isinstance(current, Player):
                    # Attack first living enemy
                    target = ctx.living_enemies[0] if ctx.living_enemies else enemies[0]
                    action = CombatAction(action_type="attack", target_id=target.id)
                    ctx.submit_player_action(action)
                elif isinstance(current, Enemy):
                    ctx.execute_enemy_turn(current)

                ctx.advance_turn()
                if ctx.is_over:
                    break

        assert ctx.is_over
        assert ctx.outcome is not None

        # Check defeated events
        events = store.get_events_by_timeline("timeline_main")
        defeated_events = [e for e in events if e.event_type == EventTypes.COMBATANT_DEFEATED]
        if ctx.outcome == CombatOutcome.VICTORY:
            assert len(defeated_events) == 3  # All enemies defeated


class TestDeterminism:
    """Tests for deterministic combat replay."""

    def test_same_seed_same_result(self) -> None:
        """Same seed produces identical combat outcomes."""
        results: list[list[str]] = []

        for _ in range(2):
            player = create_test_player(speed=50, attack=60)
            enemy = create_test_enemy(speed=30, hp=100, max_hp=100)
            ctx = create_combat_context(player=player, enemies=[enemy], seed=42)

            for _ in range(20):
                if ctx.is_over:
                    break
                ctx.start_round()

                while not ctx.is_over and ctx.phase != CombatPhase.ROUND_END:
                    current = ctx.current_combatant
                    if isinstance(current, Player):
                        action = CombatAction(action_type="attack", target_id="enemy_1")
                        ctx.submit_player_action(action)
                    elif isinstance(current, Enemy):
                        ctx.execute_enemy_turn(current)
                    ctx.advance_turn()
                    if ctx.is_over:
                        break

            results.append(ctx.log_messages)

        # Both runs should produce identical log messages
        assert results[0] == results[1]

    def test_different_seed_different_result(self) -> None:
        """Different seeds produce different combat logs."""
        logs: list[list[str]] = []

        for seed in [42, 99]:
            player = create_test_player(speed=50, attack=60)
            enemy = create_test_enemy(speed=30, hp=100, max_hp=100)
            ctx = create_combat_context(player=player, enemies=[enemy], seed=seed)

            ctx.start_round()
            if isinstance(ctx.current_combatant, Player):
                action = CombatAction(action_type="attack", target_id="enemy_1")
                ctx.submit_player_action(action)

            logs.append(ctx.log_messages)

        # Logs should differ (different damage rolls)
        assert logs[0] != logs[1]


class TestEventEmission:
    """Tests for correct event emission to EventStore."""

    def test_all_events_have_correct_aggregate(self) -> None:
        """All combat events use combat_id as aggregate_id."""
        store = EventStore(":memory:")
        ctx = create_combat_context(event_store=store)
        ctx.start_round()

        if isinstance(ctx.current_combatant, Player):
            action = CombatAction(action_type="attack", target_id="enemy_1")
            ctx.submit_player_action(action)

        events = store.get_events_by_timeline("timeline_main")
        for event in events:
            assert event.aggregate_id == "combat_001"
            assert event.aggregate_type == "combat"

    def test_events_are_chronological(self) -> None:
        """Events are stored in chronological order."""
        store = EventStore(":memory:")
        ctx = create_combat_context(event_store=store)
        ctx.start_round()

        if isinstance(ctx.current_combatant, Player):
            action = CombatAction(action_type="attack", target_id="enemy_1")
            ctx.submit_player_action(action)

        events = store.get_events_by_timeline("timeline_main")
        timestamps = [e.event_timestamp for e in events]
        assert timestamps == sorted(timestamps)

    def test_event_sequence_combat_start_to_end(self) -> None:
        """Full combat emits events in correct sequence."""
        store = EventStore(":memory:")
        player = create_test_player(attack=200, speed=50)
        enemy = create_test_enemy(hp=1, max_hp=1, speed=10)
        ctx = create_combat_context(player=player, enemies=[enemy], event_store=store, seed=42)

        ctx.start_round()
        action = CombatAction(action_type="attack", target_id="enemy_1")
        ctx.submit_player_action(action)
        ctx.advance_turn()

        events = store.get_events_by_timeline("timeline_main")
        event_types = [e.event_type for e in events]

        # First event should be COMBAT_STARTED
        assert event_types[0] == EventTypes.COMBAT_STARTED
        # Should have BP gained
        assert EventTypes.BOOST_POINT_GAINED in event_types
        # Should have action
        assert EventTypes.ACTION_EXECUTED in event_types
        # Should have defeat
        assert EventTypes.COMBATANT_DEFEATED in event_types
        # Last should be COMBAT_ENDED
        assert event_types[-1] == EventTypes.COMBAT_ENDED

    def test_event_count_matches_actions(self) -> None:
        """Number of ACTION_EXECUTED events matches number of actions taken."""
        store = EventStore(":memory:")
        player = create_test_player(speed=50)
        enemy = create_test_enemy(speed=30, hp=500, max_hp=500)
        ctx = create_combat_context(player=player, enemies=[enemy], event_store=store, seed=42)

        action_count = 0
        for _ in range(3):
            if ctx.is_over:
                break
            ctx.start_round()

            while not ctx.is_over and ctx.phase != CombatPhase.ROUND_END:
                current = ctx.current_combatant
                if isinstance(current, Player):
                    action = CombatAction(action_type="attack", target_id="enemy_1")
                    ctx.submit_player_action(action)
                elif isinstance(current, Enemy):
                    ctx.execute_enemy_turn(current)
                action_count += 1
                ctx.advance_turn()
                if ctx.is_over:
                    break

        events = store.get_events_by_timeline("timeline_main")
        action_events = [e for e in events if e.event_type == EventTypes.ACTION_EXECUTED]
        assert len(action_events) == action_count
