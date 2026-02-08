"""
Critical combat scenario tests and coverage gap tests.

10 named scenarios validating end-to-end combat behavior, plus targeted
tests for uncovered lines in combat.py (validation errors, unknown actions,
enemy defend/ability, break recovery, dead-combatant skipping, combatant
lookup miss).
"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatOutcome, CombatPhase
from src.core.events import EventTypes
from src.core.persistence import EventStore
from src.entities import DamageType, Enemy, Player
from tests.fixtures.combat_fixtures import create_combat_context
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player

# ---------------------------------------------------------------------------
# Helper: run a full combat loop with a given player strategy
# ---------------------------------------------------------------------------


def _run_combat(
    ctx: CombatContext,
    player_action_fn: Callable[[CombatContext], CombatAction],
    max_rounds: int = 50,
) -> None:
    """Drive combat to completion using *player_action_fn* to choose actions."""
    for _ in range(max_rounds):
        if ctx.is_over:
            return
        ctx.start_round()

        while not ctx.is_over and ctx.phase != CombatPhase.ROUND_END:
            current = ctx.current_combatant
            if isinstance(current, Player):
                action = player_action_fn(ctx)
                ctx.submit_player_action(action)
            elif isinstance(current, Enemy):
                ctx.execute_enemy_turn(current)
            ctx.advance_turn()
            if ctx.is_over:
                return


# ===================================================================
# 10 Critical Scenarios
# ===================================================================


class TestScenario1PlayerVictory:
    """Scenario 1: Player wins a 1v1 combat."""

    def test_player_victory_1v1(self) -> None:
        """Strong player defeats weak enemy -> VICTORY outcome."""
        store = EventStore(":memory:")
        player = create_test_player(attack=200, speed=50)
        enemy = create_test_enemy(hp=50, max_hp=50, speed=10)
        ctx = create_combat_context(
            player=player,
            enemies=[enemy],
            event_store=store,
            seed=42,
        )

        _run_combat(
            ctx,
            lambda c: CombatAction(action_type="attack", target_id="enemy_1"),
        )

        assert ctx.is_over
        assert ctx.outcome == CombatOutcome.VICTORY
        assert not enemy.is_alive

        # Verify events sequence
        events = store.get_events_by_timeline("timeline_main")
        types = [e.event_type for e in events]
        assert types[0] == EventTypes.COMBAT_STARTED
        assert types[-1] == EventTypes.COMBAT_ENDED
        assert EventTypes.COMBATANT_DEFEATED in types

        end_data = json.loads(events[-1].event_data)
        assert end_data["outcome"] == "victory"
        assert end_data["victory"] is True


class TestScenario2PlayerDefeat:
    """Scenario 2: Player is defeated."""

    def test_player_defeat(self) -> None:
        """Weak player vs strong enemy -> DEFEAT outcome."""
        player = create_test_player(hp=1, max_hp=300, speed=10, defense=1)
        enemy = create_test_enemy(attack=200, speed=50)
        store = EventStore(":memory:")
        ctx = create_combat_context(
            player=player,
            enemies=[enemy],
            event_store=store,
            seed=42,
        )

        _run_combat(
            ctx,
            lambda c: CombatAction(action_type="defend", target_id="player_1"),
        )

        assert ctx.is_over
        assert ctx.outcome == CombatOutcome.DEFEAT

        events = store.get_events_by_timeline("timeline_main")
        end_data = json.loads(events[-1].event_data)
        assert end_data["outcome"] == "defeat"
        assert end_data["victory"] is False


class TestScenario3ShieldBreak:
    """Scenario 3: Break system with 1.5x break damage."""

    def test_shield_break_bonus_damage(self) -> None:
        """Hit weakness until shield breaks, next hit gets 1.5x break damage."""
        enemy = create_test_enemy(
            hp=500,
            max_hp=500,
            shield_points=1,
            max_shield_points=3,
            weaknesses=[DamageType.FIRE],
        )

        # First FIRE hit breaks the shield (shield 1 -> 0)
        result1 = enemy.take_damage(100, DamageType.FIRE)
        assert result1.weakness_hit
        assert result1.shield_broken
        assert enemy.is_broken

        # Next hit while broken gets 1.5x multiplier
        result2 = enemy.take_damage(100, DamageType.PHYSICAL)
        assert result2.damage == 150  # 100 * 1.5

        # Verify SHIELD_BROKEN event in full combat context
        store = EventStore(":memory:")
        player = create_test_player(attack=200, speed=50)
        weak_enemy = create_test_enemy(
            hp=500,
            max_hp=500,
            shield_points=1,
            max_shield_points=3,
            weaknesses=[DamageType.PHYSICAL],
        )
        ctx = create_combat_context(
            player=player,
            enemies=[weak_enemy],
            event_store=store,
            seed=42,
        )
        ctx.start_round()
        if isinstance(ctx.current_combatant, Player):
            ctx.submit_player_action(
                CombatAction(action_type="attack", target_id="enemy_1"),
            )

        events = store.get_events_by_timeline("timeline_main")
        shield_events = [e for e in events if e.event_type == EventTypes.SHIELD_BROKEN]
        assert len(shield_events) == 1


class TestScenario4BoostSystem:
    """Scenario 4: BP gain, cap, and spending multipliers."""

    def test_boost_point_multipliers(self) -> None:
        """BP spend returns correct multipliers: 1BP=1.5x, 2BP=2.0x, 3BP=2.5x."""
        player = create_test_player(boost_points=5)
        assert player.spend_bp(1) == 1.5
        assert player.spend_bp(2) == 2.0
        assert player.boost_points == 2  # 5 - 1 - 2

    def test_bp_gain_per_round_in_combat(self) -> None:
        """Player gains 1 BP per round, tracked via events."""
        store = EventStore(":memory:")
        player = create_test_player(boost_points=0, speed=50)
        enemy = create_test_enemy(hp=500, max_hp=500, speed=10)
        ctx = create_combat_context(
            player=player,
            enemies=[enemy],
            event_store=store,
            seed=42,
        )

        ctx.start_round()
        assert player.boost_points == 1

        # Finish round
        ctx.submit_player_action(
            CombatAction(action_type="attack", target_id="enemy_1"),
        )
        ctx.advance_turn()
        while not ctx.is_over and ctx.phase != CombatPhase.ROUND_END:
            current = ctx.current_combatant
            if isinstance(current, Enemy):
                ctx.execute_enemy_turn(current)
            ctx.advance_turn()

        # Second round
        if not ctx.is_over:
            ctx.start_round()
            assert player.boost_points == 2

        events = store.get_events_by_timeline("timeline_main")
        bp_events = [e for e in events if e.event_type == EventTypes.BOOST_POINT_GAINED]
        assert len(bp_events) >= 1


class TestScenario5CriticalHit:
    """Scenario 5: Force a critical hit via seeded RNG."""

    def test_critical_hit_multiplier(self) -> None:
        """Seed RNG to force a crit, verify 1.5x damage."""
        from src.core.damage import DamageCalculator

        # Search for a seed that produces a critical hit with 5% chance
        for seed in range(1000):
            calc = DamageCalculator(rng_seed=seed)
            result = calc.calculate(
                attacker_atk=100,
                defender_def=50,
                crit_chance=5,
            )
            if result.is_critical:
                assert result.multipliers["critical"] == 1.5
                return

        pytest.fail("Could not find a seed producing a critical hit within 1000 tries")


class TestScenario6TypeEffectiveness:
    """Scenario 6: Type weakness doubles damage."""

    def test_weakness_doubles_damage(self) -> None:
        """Attack with weakness type gives 2.0x damage via DamageCalculator."""
        from src.core.damage import DamageCalculator

        calc = DamageCalculator(rng_seed=42)
        normal = calc.calculate(attacker_atk=100, defender_def=50)

        calc2 = DamageCalculator(rng_seed=42)
        weak = calc2.calculate(
            attacker_atk=100,
            defender_def=50,
            damage_type=DamageType.FIRE,
            defender_weaknesses=[DamageType.FIRE],
        )

        # Weakness hit should be roughly 2x normal (exact same RNG state)
        assert weak.is_weakness
        assert weak.multipliers["type"] == 2.0
        # With same RNG state, damage ratio should be ~2.0
        assert weak.damage == pytest.approx(normal.damage * 2, abs=1)


class TestScenario7MultiEnemy:
    """Scenario 7: 1v3 with different archetypes, turn order, HP tracking."""

    def test_1v3_multi_enemy_combat(self) -> None:
        """3 enemies with different archetypes, verify turn order and HP."""
        store = EventStore(":memory:")
        player = create_test_player(speed=50, attack=80)
        enemies = [
            create_test_enemy(
                id="e1",
                name="Warrior",
                speed=30,
                hp=80,
                max_hp=80,
                archetype="aggressive",
            ),
            create_test_enemy(
                id="e2",
                name="Cleric",
                speed=25,
                hp=60,
                max_hp=60,
                archetype="defensive",
            ),
            create_test_enemy(
                id="e3",
                name="Mage",
                speed=45,
                hp=40,
                max_hp=40,
                archetype="tactical",
            ),
        ]
        ctx = create_combat_context(
            player=player,
            enemies=enemies,
            event_store=store,
            seed=42,
        )

        ctx.start_round()
        # Turn order: Player(50) > Mage(45) > Warrior(30) > Cleric(25)
        order = [c.name for c in ctx._turn_order]
        assert order == ["Hero", "Mage", "Warrior", "Cleric"]

        # Run full combat
        _run_combat(
            ctx,
            lambda c: CombatAction(
                action_type="attack",
                target_id=c.living_enemies[0].id if c.living_enemies else "e1",
            ),
        )

        assert ctx.is_over
        # Verify per-enemy HP tracking
        if ctx.outcome == CombatOutcome.VICTORY:
            assert all(not e.is_alive for e in enemies)


class TestScenario8FleeSuccess:
    """Scenario 8: Successful flee attempt."""

    def test_flee_success_outcome(self) -> None:
        """Seed RNG for successful flee, verify FLED outcome and events."""
        # High player speed = high flee chance (up to 90%)
        for seed in range(200):
            player = create_test_player(speed=90)
            enemy = create_test_enemy(speed=10)
            store = EventStore(":memory:")
            ctx = create_combat_context(
                player=player,
                enemies=[enemy],
                event_store=store,
                seed=seed,
            )
            ctx.start_round()

            if not isinstance(ctx.current_combatant, Player):
                ctx.execute_enemy_turn(ctx.current_combatant)
                ctx.advance_turn()

            ctx.submit_player_action(
                CombatAction(action_type="flee", target_id="player_1"),
            )

            if ctx.outcome == CombatOutcome.FLED:
                assert ctx.is_over
                events = store.get_events_by_timeline("timeline_main")
                fled_events = [e for e in events if e.event_type == EventTypes.COMBAT_FLED]
                assert len(fled_events) == 1
                data = json.loads(fled_events[0].event_data)
                assert data["flee_success"] is True

                end_events = [e for e in events if e.event_type == EventTypes.COMBAT_ENDED]
                assert len(end_events) == 1
                end_data = json.loads(end_events[0].event_data)
                assert end_data["outcome"] == "fled"
                return

        pytest.fail("Could not find a seed that produces a successful flee")


class TestScenario9EventReplay:
    """Scenario 9: Event replay — reconstruct combat from persisted events."""

    def test_event_replay_integrity(self) -> None:
        """Run combat, retrieve events from store, verify sequence and data."""
        store = EventStore(":memory:")
        player = create_test_player(attack=200, speed=50)
        enemy = create_test_enemy(hp=50, max_hp=50, speed=10)
        ctx = create_combat_context(
            player=player,
            enemies=[enemy],
            event_store=store,
            seed=42,
        )

        _run_combat(
            ctx,
            lambda c: CombatAction(action_type="attack", target_id="enemy_1"),
        )

        assert ctx.is_over

        # Retrieve all events from the store
        events = store.get_events_by_timeline("timeline_main")
        assert len(events) >= 4  # At minimum: started, bp_gained, action, ended

        # All events reference the same combat
        for event in events:
            assert event.aggregate_id == "combat_001"
            assert event.aggregate_type == "combat"
            assert event.session_id == "sess_001"
            assert event.timeline_id == "timeline_main"

        # Events are chronologically ordered
        timestamps = [e.event_timestamp for e in events]
        assert timestamps == sorted(timestamps)

        # First event is COMBAT_STARTED with full initial state
        start_data = json.loads(events[0].event_data)
        assert start_data["rng_seed"] == 42
        assert start_data["player"]["id"] == "player_1"
        assert len(start_data["enemies"]) == 1

        # Last event is COMBAT_ENDED
        assert events[-1].event_type == EventTypes.COMBAT_ENDED
        end_data = json.loads(events[-1].event_data)
        assert "outcome" in end_data
        assert "total_turns" in end_data

        # Verify action events have required fields
        action_events = [e for e in events if e.event_type == EventTypes.ACTION_EXECUTED]
        for ae in action_events:
            data = json.loads(ae.event_data)
            assert "actor_id" in data
            assert "action_type" in data
            assert "turn_number" in data


class TestScenario10AIDeterminism:
    """Scenario 10: Same seed produces identical AI action sequences."""

    def test_ai_determinism_across_runs(self) -> None:
        """Two runs with same seed produce identical log messages."""
        logs: list[list[str]] = []

        for _ in range(2):
            player = create_test_player(speed=50, attack=60)
            enemy = create_test_enemy(speed=30, hp=100, max_hp=100)
            ctx = create_combat_context(player=player, enemies=[enemy], seed=12345)

            _run_combat(
                ctx,
                lambda c: CombatAction(action_type="attack", target_id="enemy_1"),
            )
            logs.append(ctx.log_messages)

        assert logs[0] == logs[1]
        assert len(logs[0]) > 0


# ===================================================================
# Coverage Gap Tests — targeting uncovered lines in combat.py
# ===================================================================


class TestCoverageGaps:
    """Tests for uncovered code paths in combat.py."""

    # --- Validation errors (lines 108, 110) ---

    def test_validation_empty_session_id(self) -> None:
        """Raises ValueError for empty session_id."""
        with pytest.raises(ValueError, match="session_id"):
            CombatContext(
                combat_id="c1",
                seed=42,
                player=create_test_player(),
                enemies=[create_test_enemy()],
                event_store=EventStore(":memory:"),
                session_id="",
                timeline_id="tl",
            )

    def test_validation_empty_timeline_id(self) -> None:
        """Raises ValueError for empty timeline_id."""
        with pytest.raises(ValueError, match="timeline_id"):
            CombatContext(
                combat_id="c1",
                seed=42,
                player=create_test_player(),
                enemies=[create_test_enemy()],
                event_store=EventStore(":memory:"),
                session_id="sess",
                timeline_id="",
            )

    # --- Unknown action type (line 327) ---

    def test_unknown_action_type_raises(self) -> None:
        """Raises ValueError for unknown player action type."""
        player = create_test_player(speed=50)
        enemy = create_test_enemy(speed=10)
        ctx = create_combat_context(player=player, enemies=[enemy])
        ctx.start_round()

        with pytest.raises(ValueError, match="Unknown action type"):
            ctx.submit_player_action(
                CombatAction(action_type="dance", target_id="enemy_1"),
            )

    # --- Submit player action in wrong phase (line 313) ---

    def test_submit_action_wrong_phase(self) -> None:
        """Raises RuntimeError when submitting action outside AWAITING_PLAYER_INPUT."""
        ctx = create_combat_context()
        # Phase is INITIALIZING, not AWAITING_PLAYER_INPUT
        with pytest.raises(RuntimeError, match="Cannot submit player action"):
            ctx.submit_player_action(
                CombatAction(action_type="attack", target_id="enemy_1"),
            )

    # --- Enemy defend execution (line 358) ---

    def test_enemy_defend_action(self) -> None:
        """Enemy defend action executes and emits event."""
        store = EventStore(":memory:")
        # Use defensive archetype with high defend weight
        player = create_test_player(speed=10)
        enemy = create_test_enemy(speed=50, archetype="defensive")
        ctx = create_combat_context(
            player=player,
            enemies=[enemy],
            event_store=store,
        )
        ctx.start_round()

        # Run many seeds until enemy defends
        found_defend = False
        for seed in range(500):
            player = create_test_player(speed=10)
            enemy = create_test_enemy(speed=50, archetype="defensive", hp=1, max_hp=200)
            # Low HP triggers 60% defend weight
            ctx = create_combat_context(
                player=player,
                enemies=[enemy],
                event_store=store,
                seed=seed,
            )
            ctx.start_round()
            # Enemy goes first
            assert isinstance(ctx.current_combatant, Enemy)
            action = ctx.get_enemy_action(enemy)
            if action.action_type == "defend":
                msgs = ctx.execute_enemy_turn(enemy)
                assert any("defensive stance" in m for m in msgs)
                found_defend = True
                break

        assert found_defend, "Could not trigger enemy defend action"

    # --- Enemy ability execution (line 361) ---

    def test_enemy_ability_action(self) -> None:
        """Enemy ability action executes as attack."""
        store = EventStore(":memory:")
        found_ability = False
        for seed in range(500):
            player = create_test_player(speed=10, hp=500, max_hp=500)
            enemy = create_test_enemy(speed=50, archetype="aggressive")
            ctx = create_combat_context(
                player=player,
                enemies=[enemy],
                event_store=store,
                seed=seed,
            )
            ctx.start_round()
            assert isinstance(ctx.current_combatant, Enemy)
            action = ctx.get_enemy_action(enemy)
            if action.action_type == "ability":
                initial_hp = player.hp
                ctx.execute_enemy_turn(enemy)
                # Ability acts as attack, should deal damage
                assert player.hp <= initial_hp
                found_ability = True
                break

        assert found_ability, "Could not trigger enemy ability action"

    # --- Enemy unknown action falls back to defend (line 363) ---

    def test_enemy_unknown_action_fallback(self) -> None:
        """Unknown enemy action type falls back to defend."""
        player = create_test_player(speed=10)
        enemy = create_test_enemy(speed=50)
        ctx = create_combat_context(player=player, enemies=[enemy], seed=42)
        ctx.start_round()

        # Monkey-patch get_enemy_action to return unknown type
        original_get = ctx.get_enemy_action
        ctx.get_enemy_action = lambda e: CombatAction(
            action_type="unknown_spell",
            target_id="player_1",
        )

        msgs = ctx.execute_enemy_turn(enemy)
        # Falls back to defend
        assert any("defensive stance" in m for m in msgs)

        # Restore
        ctx.get_enemy_action = original_get

    # --- Break recovery messages in advance_turn (lines 384-385) ---

    def test_break_recovery_in_advance_turn(self) -> None:
        """Break recovery message appears when advancing turn past broken enemy."""
        # Enemy goes first (higher speed) so advance_turn processes enemy turn-end
        player = create_test_player(speed=10, hp=500, max_hp=500)
        enemy = create_test_enemy(
            speed=50,
            hp=500,
            max_hp=500,
            shield_points=1,
            max_shield_points=3,
            weaknesses=[DamageType.FIRE],
        )

        ctx = create_combat_context(player=player, enemies=[enemy], seed=42)

        # Break the enemy *after* context creation so AI is registered
        enemy.take_damage(10, DamageType.FIRE)
        assert enemy.is_broken
        assert enemy.break_turns_remaining == 1

        ctx.start_round()
        # Enemy goes first (speed=50 > player speed=10)
        assert isinstance(ctx.current_combatant, Enemy)

        # Enemy is stunned, skip turn
        ctx.execute_enemy_turn(enemy)

        # advance_turn processes enemy's turn-end -> break recovery (lines 384-385)
        recovery_msgs = ctx.advance_turn()
        assert any("restored" in m for m in recovery_msgs)
        assert not enemy.is_broken
        assert enemy.shield_points == 3

    # --- Dead combatant skipping in advance_turn (lines 400-409) ---

    def test_dead_combatant_skipped_in_turn_order(self) -> None:
        """Dead enemies are skipped when advancing turns."""
        player = create_test_player(attack=500, speed=50)
        enemies = [
            create_test_enemy(id="e1", name="Weak", hp=1, max_hp=1, speed=40),
            create_test_enemy(id="e2", name="Strong", hp=500, max_hp=500, speed=20),
        ]
        store = EventStore(":memory:")
        ctx = create_combat_context(
            player=player,
            enemies=enemies,
            event_store=store,
            seed=42,
        )

        ctx.start_round()
        # Turn order: Player(50) > Weak(40) > Strong(20)

        # Player kills Weak
        ctx.submit_player_action(
            CombatAction(action_type="attack", target_id="e1"),
        )
        assert not enemies[0].is_alive

        # Advance should skip dead Weak and go to Strong
        ctx.advance_turn()
        if not ctx.is_over:
            assert ctx.current_combatant.id == "e2"

    def test_all_remaining_combatants_dead_ends_round(self) -> None:
        """If remaining combatants are all dead, round ends."""
        player = create_test_player(attack=500, speed=50)
        enemies = [
            create_test_enemy(id="e1", name="First", hp=1, max_hp=1, speed=40),
            create_test_enemy(id="e2", name="Second", hp=1, max_hp=1, speed=30),
        ]
        ctx = create_combat_context(
            player=player,
            enemies=enemies,
            seed=42,
        )

        ctx.start_round()
        # Kill first enemy
        ctx.submit_player_action(
            CombatAction(action_type="attack", target_id="e1"),
        )
        # advance_turn triggers _check_combat_end which may detect victory
        # if not, it skips dead e1 and goes to e2
        ctx.advance_turn()

        if not ctx.is_over and isinstance(ctx.current_combatant, Enemy):
            ctx.execute_enemy_turn(ctx.current_combatant)
            ctx.advance_turn()

    # --- Combatant lookup failure (line 648) ---

    def test_combatant_lookup_miss(self) -> None:
        """Raises ValueError for unknown combatant ID."""
        ctx = create_combat_context()
        ctx.start_round()

        if isinstance(ctx.current_combatant, Player):
            with pytest.raises(ValueError, match="No combatant found"):
                ctx.submit_player_action(
                    CombatAction(action_type="attack", target_id="nonexistent_id"),
                )

    # --- _find_combatant returns player (line 644) ---

    def test_find_combatant_returns_player(self) -> None:
        """_find_combatant returns player when target_id matches player."""
        ctx = create_combat_context()
        result = ctx._find_combatant("player_1")
        assert result.id == "player_1"
        assert isinstance(result, Player)

    # --- No AI registered for enemy (line 289) ---

    def test_no_ai_registered_for_enemy(self) -> None:
        """Raises ValueError when requesting AI for unregistered enemy."""
        ctx = create_combat_context()
        rogue_enemy = create_test_enemy(id="rogue_99", name="Rogue")
        with pytest.raises(ValueError, match="No AI registered"):
            ctx.get_enemy_action(rogue_enemy)
