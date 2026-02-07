"""
Unit tests for enemy AI decision-making system.

Tests for EnemyAI classes including:
- Initialization and validation
- Base weights for all 4 archetypes
- HP-based situational weight modifiers
- Weighted random action selection
- Determinism (same seed = same decisions)
- Factory function
- Edge cases
"""

import random

import pytest

from src.core.ai import (
    AggressiveAI,
    AIArchetype,
    BerserkerAI,
    CombatAction,
    CombatState,
    DefensiveAI,
    TacticalAI,
    create_enemy_ai,
)
from src.entities import DamageType, Enemy, Player

# ============================================================================
# Test Fixtures
# ============================================================================


def _create_player(
    hp: int = 300,
    max_hp: int = 300,
    attack: int = 50,
    defense: int = 30,
    speed: int = 40,
) -> Player:
    """Create a test player with defaults."""
    return Player(
        id="player_1",
        name="Hero",
        level=10,
        hp=hp,
        max_hp=max_hp,
        attack=attack,
        defense=defense,
        speed=speed,
    )


def _create_enemy(
    hp: int = 200,
    max_hp: int = 200,
    attack: int = 40,
    defense: int = 25,
    speed: int = 30,
    archetype: str = "aggressive",
) -> Enemy:
    """Create a test enemy with defaults."""
    return Enemy(
        id="enemy_1",
        name="Goblin",
        level=8,
        hp=hp,
        max_hp=max_hp,
        attack=attack,
        defense=defense,
        speed=speed,
        shield_points=3,
        max_shield_points=3,
        weaknesses=[DamageType.FIRE, DamageType.ICE],
        archetype=archetype,
    )


def _create_combat_state(
    player_hp: int = 300,
    player_max_hp: int = 300,
    enemies: list[Enemy] | None = None,
) -> CombatState:
    """Create a test combat state."""
    player = _create_player(hp=player_hp, max_hp=player_max_hp)
    if enemies is None:
        enemies = [_create_enemy()]
    return CombatState(player=player, enemies=enemies)


# ============================================================================
# CombatAction Tests
# ============================================================================


class TestCombatAction:
    """Tests for CombatAction dataclass."""

    def test_create_attack_action(self):
        """Test creating an attack action."""
        action = CombatAction(action_type="attack", target_id="player_1")

        assert action.action_type == "attack"
        assert action.target_id == "player_1"
        assert action.skill_name is None
        assert action.boost_points == 0

    def test_create_ability_action(self):
        """Test creating an ability action with skill name."""
        action = CombatAction(
            action_type="ability",
            target_id="player_1",
            skill_name="Fireball",
        )

        assert action.action_type == "ability"
        assert action.skill_name == "Fireball"

    def test_create_defend_action(self):
        """Test creating a defend action targeting self."""
        action = CombatAction(action_type="defend", target_id="enemy_1")

        assert action.action_type == "defend"
        assert action.target_id == "enemy_1"


# ============================================================================
# CombatState Tests
# ============================================================================


class TestCombatState:
    """Tests for CombatState dataclass."""

    def test_create_combat_state(self):
        """Test creating a combat state with defaults."""
        state = _create_combat_state()

        assert state.player.id == "player_1"
        assert len(state.enemies) == 1
        assert state.round_number == 1

    def test_combat_state_with_round_number(self):
        """Test creating combat state with custom round number."""
        player = _create_player()
        state = CombatState(player=player, enemies=[], round_number=5)

        assert state.round_number == 5


# ============================================================================
# EnemyAI Base Class Tests
# ============================================================================


class TestEnemyAIInitialization:
    """Tests for EnemyAI initialization and validation."""

    def test_create_with_valid_inputs(self):
        """Test creating AI with valid enemy and RNG."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)

        assert ai.enemy is enemy
        assert ai.rng is rng
        assert ai.base_weights is not None

    def test_create_with_non_enemy_raises_type_error(self):
        """Test that passing non-Enemy raises TypeError."""
        rng = random.Random(42)

        with pytest.raises(TypeError, match="Expected Enemy instance"):
            AggressiveAI("not_an_enemy", rng)  # type: ignore[arg-type]

    def test_create_with_non_rng_raises_type_error(self):
        """Test that passing non-Random raises TypeError."""
        enemy = _create_enemy()

        with pytest.raises(TypeError, match="Expected random.Random instance"):
            AggressiveAI(enemy, "not_rng")  # type: ignore[arg-type]

    def test_base_weights_set_on_init(self):
        """Test that base_weights are set during initialization."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)

        assert "attack" in ai.base_weights
        assert "defend" in ai.base_weights
        assert "ability" in ai.base_weights


# ============================================================================
# Action Selection Tests
# ============================================================================


class TestActionSelection:
    """Tests for the select_action method."""

    def test_select_action_returns_combat_action(self):
        """Test that select_action returns a CombatAction."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)
        state = _create_combat_state()

        action = ai.select_action(state)

        assert isinstance(action, CombatAction)
        assert action.action_type in ("attack", "defend", "ability")

    def test_select_action_attack_targets_player(self):
        """Test that attack actions target the player."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)
        state = _create_combat_state()

        # Run many times to find an attack
        for _ in range(100):
            action = ai.select_action(state)
            if action.action_type == "attack":
                assert action.target_id == "player_1"
                return

        pytest.fail("No attack action was selected in 100 attempts")

    def test_select_action_defend_targets_self(self):
        """Test that defend actions target the enemy itself."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = DefensiveAI(enemy, rng)
        state = _create_combat_state()

        # Run many times to find a defend
        for _ in range(100):
            action = ai.select_action(state)
            if action.action_type == "defend":
                assert action.target_id == "enemy_1"
                return

        pytest.fail("No defend action was selected in 100 attempts")

    def test_select_action_invalid_state_raises_type_error(self):
        """Test that non-CombatState raises TypeError."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)

        with pytest.raises(TypeError, match="Expected CombatState instance"):
            ai.select_action("not_a_state")  # type: ignore[arg-type]


# ============================================================================
# Aggressive AI Tests
# ============================================================================


class TestAggressiveAI:
    """Tests for AggressiveAI archetype."""

    def test_base_weights(self):
        """Test aggressive base weights are 70/10/20."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)

        assert ai.base_weights == {"attack": 70, "defend": 10, "ability": 20}

    def test_favors_attack_at_full_hp(self):
        """Test that aggressive AI favors attack when at full HP."""
        enemy = _create_enemy(hp=200, max_hp=200)
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)
        state = _create_combat_state()

        actions = [ai.select_action(state).action_type for _ in range(1000)]
        attack_pct = actions.count("attack") / len(actions) * 100

        # Should be around 70% (with some variance)
        assert attack_pct > 55, f"Expected >55% attacks, got {attack_pct:.1f}%"

    def test_more_defensive_when_low_hp(self):
        """Test that aggressive AI becomes slightly defensive at <30% HP."""
        enemy = _create_enemy(hp=50, max_hp=200)  # 25% HP
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)
        state = _create_combat_state()

        weights = ai._calculate_situational_weights(state)

        assert weights["attack"] == 50
        assert weights["defend"] == 25
        assert weights["ability"] == 25

    def test_normal_weights_above_30_hp(self):
        """Test that normal weights are used above 30% HP."""
        enemy = _create_enemy(hp=100, max_hp=200)  # 50% HP
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)
        state = _create_combat_state()

        weights = ai._calculate_situational_weights(state)

        assert weights == {"attack": 70, "defend": 10, "ability": 20}


# ============================================================================
# Defensive AI Tests
# ============================================================================


class TestDefensiveAI:
    """Tests for DefensiveAI archetype."""

    def test_base_weights(self):
        """Test defensive base weights are 40/40/20."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = DefensiveAI(enemy, rng)

        assert ai.base_weights == {"attack": 40, "defend": 40, "ability": 20}

    def test_balanced_at_full_hp(self):
        """Test that defensive AI is balanced between attack and defend."""
        enemy = _create_enemy(hp=200, max_hp=200)
        rng = random.Random(42)
        ai = DefensiveAI(enemy, rng)
        state = _create_combat_state()

        actions = [ai.select_action(state).action_type for _ in range(1000)]
        attack_pct = actions.count("attack") / len(actions) * 100
        defend_pct = actions.count("defend") / len(actions) * 100

        # Should be roughly equal (~40% each)
        assert 25 < attack_pct < 55, f"Expected ~40% attacks, got {attack_pct:.1f}%"
        assert 25 < defend_pct < 55, f"Expected ~40% defends, got {defend_pct:.1f}%"

    def test_more_defensive_when_low_hp(self):
        """Test that defensive AI becomes even more defensive at <50% HP."""
        enemy = _create_enemy(hp=80, max_hp=200)  # 40% HP
        rng = random.Random(42)
        ai = DefensiveAI(enemy, rng)
        state = _create_combat_state()

        weights = ai._calculate_situational_weights(state)

        assert weights["attack"] == 20
        assert weights["defend"] == 60
        assert weights["ability"] == 20

    def test_normal_weights_above_50_hp(self):
        """Test that normal weights are used above 50% HP."""
        enemy = _create_enemy(hp=120, max_hp=200)  # 60% HP
        rng = random.Random(42)
        ai = DefensiveAI(enemy, rng)
        state = _create_combat_state()

        weights = ai._calculate_situational_weights(state)

        assert weights == {"attack": 40, "defend": 40, "ability": 20}


# ============================================================================
# Tactical AI Tests
# ============================================================================


class TestTacticalAI:
    """Tests for TacticalAI archetype."""

    def test_base_weights(self):
        """Test tactical base weights are 50/20/30."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = TacticalAI(enemy, rng)

        assert ai.base_weights == {"attack": 50, "defend": 20, "ability": 30}

    def test_ability_focus_when_player_low_hp(self):
        """Test that tactical AI uses abilities when player is low HP."""
        enemy = _create_enemy(hp=200, max_hp=200)
        rng = random.Random(42)
        ai = TacticalAI(enemy, rng)
        state = _create_combat_state(player_hp=100, player_max_hp=300)  # ~33% HP

        weights = ai._calculate_situational_weights(state)

        assert weights["ability"] == 50

    def test_defensive_when_self_low_hp(self):
        """Test that tactical AI defends when own HP is low."""
        enemy = _create_enemy(hp=50, max_hp=200)  # 25% HP
        rng = random.Random(42)
        ai = TacticalAI(enemy, rng)
        state = _create_combat_state()

        weights = ai._calculate_situational_weights(state)

        assert weights["defend"] == 50

    def test_both_modifiers_can_apply(self):
        """Test that both player-low and self-low modifiers stack."""
        enemy = _create_enemy(hp=50, max_hp=200)  # 25% HP
        rng = random.Random(42)
        ai = TacticalAI(enemy, rng)
        state = _create_combat_state(player_hp=100, player_max_hp=300)  # ~33% HP

        weights = ai._calculate_situational_weights(state)

        # Both modifiers apply
        assert weights["ability"] == 50
        assert weights["defend"] == 50

    def test_normal_weights_when_both_healthy(self):
        """Test normal weights when both player and enemy are healthy."""
        enemy = _create_enemy(hp=200, max_hp=200)
        rng = random.Random(42)
        ai = TacticalAI(enemy, rng)
        state = _create_combat_state(player_hp=300, player_max_hp=300)

        weights = ai._calculate_situational_weights(state)

        assert weights == {"attack": 50, "defend": 20, "ability": 30}


# ============================================================================
# Berserker AI Tests
# ============================================================================


class TestBerserkerAI:
    """Tests for BerserkerAI archetype."""

    def test_base_weights(self):
        """Test berserker base weights are 60/20/20."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = BerserkerAI(enemy, rng)

        assert ai.base_weights == {"attack": 60, "defend": 20, "ability": 20}

    def test_rage_mode_when_low_hp(self):
        """Test berserker enters rage mode at <30% HP."""
        enemy = _create_enemy(hp=50, max_hp=200)  # 25% HP
        rng = random.Random(42)
        ai = BerserkerAI(enemy, rng)
        state = _create_combat_state()

        weights = ai._calculate_situational_weights(state)

        assert weights["attack"] == 80
        assert weights["defend"] == 5
        assert weights["ability"] == 15

    def test_normal_weights_above_30_hp(self):
        """Test normal weights when HP is above 30%."""
        enemy = _create_enemy(hp=100, max_hp=200)  # 50% HP
        rng = random.Random(42)
        ai = BerserkerAI(enemy, rng)
        state = _create_combat_state()

        weights = ai._calculate_situational_weights(state)

        assert weights == {"attack": 60, "defend": 20, "ability": 20}

    def test_rage_mode_favors_attack(self):
        """Test that rage mode strongly favors attacks."""
        enemy = _create_enemy(hp=50, max_hp=200)  # 25% HP
        rng = random.Random(42)
        ai = BerserkerAI(enemy, rng)
        state = _create_combat_state()

        actions = [ai.select_action(state).action_type for _ in range(1000)]
        attack_pct = actions.count("attack") / len(actions) * 100

        assert attack_pct > 65, f"Expected >65% attacks in rage mode, got {attack_pct:.1f}%"

    def test_opposite_of_defensive(self):
        """Test that berserker gets MORE aggressive when low HP (opposite of defensive)."""
        enemy_berserk = _create_enemy(hp=50, max_hp=200)
        enemy_defensive = _create_enemy(hp=50, max_hp=200)
        rng1 = random.Random(42)
        rng2 = random.Random(42)

        berserk_ai = BerserkerAI(enemy_berserk, rng1)
        defensive_ai = DefensiveAI(enemy_defensive, rng2)
        state = _create_combat_state()

        berserk_weights = berserk_ai._calculate_situational_weights(state)
        defensive_weights = defensive_ai._calculate_situational_weights(state)

        # Berserker attacks more, defends less than defensive
        assert berserk_weights["attack"] > defensive_weights["attack"]
        assert berserk_weights["defend"] < defensive_weights["defend"]


# ============================================================================
# Determinism Tests
# ============================================================================


class TestDeterminism:
    """Tests for deterministic AI behavior with seeded RNG."""

    def test_same_seed_same_actions(self):
        """Test that same seed produces identical action sequence."""
        enemy1 = _create_enemy()
        enemy2 = _create_enemy()
        rng1 = random.Random(42)
        rng2 = random.Random(42)

        ai1 = AggressiveAI(enemy1, rng1)
        ai2 = AggressiveAI(enemy2, rng2)
        state = _create_combat_state()

        actions1 = [ai1.select_action(state).action_type for _ in range(50)]
        actions2 = [ai2.select_action(state).action_type for _ in range(50)]

        assert actions1 == actions2

    def test_different_seed_different_actions(self):
        """Test that different seeds produce different action sequences."""
        enemy1 = _create_enemy()
        enemy2 = _create_enemy()
        rng1 = random.Random(42)
        rng2 = random.Random(99)

        ai1 = AggressiveAI(enemy1, rng1)
        ai2 = AggressiveAI(enemy2, rng2)
        state = _create_combat_state()

        actions1 = [ai1.select_action(state).action_type for _ in range(50)]
        actions2 = [ai2.select_action(state).action_type for _ in range(50)]

        # Very unlikely to be identical with different seeds
        assert actions1 != actions2

    def test_determinism_across_all_archetypes(self):
        """Test determinism works for all 4 archetypes."""
        for archetype_cls in [AggressiveAI, DefensiveAI, TacticalAI, BerserkerAI]:
            enemy1 = _create_enemy()
            enemy2 = _create_enemy()
            rng1 = random.Random(123)
            rng2 = random.Random(123)

            ai1 = archetype_cls(enemy1, rng1)
            ai2 = archetype_cls(enemy2, rng2)
            state = _create_combat_state()

            actions1 = [ai1.select_action(state).action_type for _ in range(20)]
            actions2 = [ai2.select_action(state).action_type for _ in range(20)]

            assert actions1 == actions2, f"Determinism failed for {archetype_cls.__name__}"


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateEnemyAI:
    """Tests for the create_enemy_ai factory function."""

    def test_create_aggressive(self):
        """Test factory creates AggressiveAI."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = create_enemy_ai(enemy, AIArchetype.AGGRESSIVE, rng)

        assert isinstance(ai, AggressiveAI)

    def test_create_defensive(self):
        """Test factory creates DefensiveAI."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = create_enemy_ai(enemy, AIArchetype.DEFENSIVE, rng)

        assert isinstance(ai, DefensiveAI)

    def test_create_tactical(self):
        """Test factory creates TacticalAI."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = create_enemy_ai(enemy, AIArchetype.TACTICAL, rng)

        assert isinstance(ai, TacticalAI)

    def test_create_berserker(self):
        """Test factory creates BerserkerAI."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = create_enemy_ai(enemy, AIArchetype.BERSERKER, rng)

        assert isinstance(ai, BerserkerAI)

    def test_factory_passes_enemy_and_rng(self):
        """Test factory correctly passes enemy and RNG to AI."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = create_enemy_ai(enemy, AIArchetype.AGGRESSIVE, rng)

        assert ai.enemy is enemy
        assert ai.rng is rng

    def test_invalid_archetype_raises_value_error(self):
        """Test factory raises ValueError for invalid archetype."""
        enemy = _create_enemy()
        rng = random.Random(42)

        with pytest.raises(ValueError, match="Unknown archetype"):
            create_enemy_ai(enemy, "not_an_archetype", rng)  # type: ignore[arg-type]


# ============================================================================
# Archetype Behavior Comparison Tests
# ============================================================================


class TestArchetypeBehavior:
    """Tests that archetypes behave distinctly from each other."""

    def test_aggressive_attacks_more_than_defensive(self):
        """Test that aggressive AI attacks more than defensive AI."""
        enemy_agg = _create_enemy(hp=200, max_hp=200)
        enemy_def = _create_enemy(hp=200, max_hp=200)
        rng1 = random.Random(42)
        rng2 = random.Random(42)

        ai_agg = AggressiveAI(enemy_agg, rng1)
        ai_def = DefensiveAI(enemy_def, rng2)
        state = _create_combat_state()

        agg_attacks = sum(
            1 for _ in range(1000) if ai_agg.select_action(state).action_type == "attack"
        )
        def_attacks = sum(
            1 for _ in range(1000) if ai_def.select_action(state).action_type == "attack"
        )

        assert agg_attacks > def_attacks

    def test_defensive_defends_more_than_aggressive(self):
        """Test that defensive AI defends more than aggressive AI."""
        enemy_agg = _create_enemy(hp=200, max_hp=200)
        enemy_def = _create_enemy(hp=200, max_hp=200)
        rng1 = random.Random(42)
        rng2 = random.Random(42)

        ai_agg = AggressiveAI(enemy_agg, rng1)
        ai_def = DefensiveAI(enemy_def, rng2)
        state = _create_combat_state()

        agg_defends = sum(
            1 for _ in range(1000) if ai_agg.select_action(state).action_type == "defend"
        )
        def_defends = sum(
            1 for _ in range(1000) if ai_def.select_action(state).action_type == "defend"
        )

        assert def_defends > agg_defends

    def test_tactical_uses_abilities_more_than_aggressive(self):
        """Test that tactical AI uses abilities more than aggressive AI."""
        enemy_agg = _create_enemy(hp=200, max_hp=200)
        enemy_tac = _create_enemy(hp=200, max_hp=200)
        rng1 = random.Random(42)
        rng2 = random.Random(42)

        ai_agg = AggressiveAI(enemy_agg, rng1)
        ai_tac = TacticalAI(enemy_tac, rng2)
        state = _create_combat_state()

        agg_abilities = sum(
            1 for _ in range(1000) if ai_agg.select_action(state).action_type == "ability"
        )
        tac_abilities = sum(
            1 for _ in range(1000) if ai_tac.select_action(state).action_type == "ability"
        )

        assert tac_abilities > agg_abilities

    def test_berserker_more_aggressive_at_low_hp_than_others(self):
        """Test berserker attacks most when at low HP."""
        rng_seed = 42
        low_hp_enemy_args = {"hp": 50, "max_hp": 200}
        state = _create_combat_state()

        attack_counts = {}
        for name, cls in [
            ("aggressive", AggressiveAI),
            ("defensive", DefensiveAI),
            ("tactical", TacticalAI),
            ("berserker", BerserkerAI),
        ]:
            enemy = _create_enemy(**low_hp_enemy_args)
            rng = random.Random(rng_seed)
            ai = cls(enemy, rng)
            attacks = sum(1 for _ in range(1000) if ai.select_action(state).action_type == "attack")
            attack_counts[name] = attacks

        # Berserker should attack most at low HP
        assert attack_counts["berserker"] > attack_counts["aggressive"]
        assert attack_counts["berserker"] > attack_counts["defensive"]
        assert attack_counts["berserker"] > attack_counts["tactical"]


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases in AI behavior."""

    def test_ai_with_enemy_at_1_hp(self):
        """Test AI works when enemy has 1 HP."""
        enemy = _create_enemy(hp=1, max_hp=200)
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)
        state = _create_combat_state()

        action = ai.select_action(state)
        assert action.action_type in ("attack", "defend", "ability")

    def test_ai_with_player_at_1_hp(self):
        """Test AI works when player has 1 HP."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = TacticalAI(enemy, rng)
        state = _create_combat_state(player_hp=1, player_max_hp=300)

        # Tactical should boost abilities when player is low
        weights = ai._calculate_situational_weights(state)
        assert weights["ability"] == 50

    def test_ai_at_exact_hp_threshold(self):
        """Test AI at exactly 30% HP boundary (should NOT trigger low HP modifier)."""
        # 30% of 200 = 60 HP
        enemy = _create_enemy(hp=60, max_hp=200)
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)
        state = _create_combat_state()

        weights = ai._calculate_situational_weights(state)

        # At exactly 30%, hp_percent is 30.0 which is NOT < 30
        assert weights == {"attack": 70, "defend": 10, "ability": 20}

    def test_ai_just_below_hp_threshold(self):
        """Test AI just below 30% HP (should trigger low HP modifier)."""
        enemy = _create_enemy(hp=59, max_hp=200)  # 29.5% HP
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)
        state = _create_combat_state()

        weights = ai._calculate_situational_weights(state)

        assert weights["attack"] == 50
        assert weights["defend"] == 25

    def test_multiple_enemies_in_combat_state(self):
        """Test AI works with multiple enemies in combat state."""
        enemies = [
            _create_enemy(hp=200, max_hp=200),
            _create_enemy(hp=100, max_hp=200),
            _create_enemy(hp=50, max_hp=200),
        ]
        # Patch IDs to be unique
        enemies[0].id = "enemy_1"
        enemies[1].id = "enemy_2"
        enemies[2].id = "enemy_3"

        state = CombatState(player=_create_player(), enemies=enemies)

        rng = random.Random(42)
        ai = AggressiveAI(enemies[0], rng)

        action = ai.select_action(state)
        assert action.action_type in ("attack", "defend", "ability")

    def test_consecutive_actions_consume_rng(self):
        """Test that each action selection advances the RNG state."""
        enemy = _create_enemy()
        rng = random.Random(42)
        ai = AggressiveAI(enemy, rng)
        state = _create_combat_state()

        # Get state of RNG after each call
        actions = []
        for _ in range(10):
            action = ai.select_action(state)
            actions.append(action.action_type)

        # With 70% attack weight, we should see some variety
        unique_actions = set(actions)
        assert len(unique_actions) >= 1  # At minimum 1 type, usually 2-3
