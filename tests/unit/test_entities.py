"""
Unit tests for combat entities.

Tests for Combatant, Player, and Enemy classes, including:
- Initialization and validation
- HP management and calculations
- Boost Point system (Player)
- Break System mechanics (Enemy)
- Damage application
"""

import pytest

from src.entities import DamageType
from tests.fixtures.entity_fixtures import (
    create_test_enemy,
    create_test_player,
)

# ============================================================================
# Player Tests
# ============================================================================


class TestPlayerInitialization:
    """Tests for Player initialization and validation."""

    def test_create_valid_player(self):
        """Test creating a valid player instance."""
        player = create_test_player()

        assert player.id == "player_1"
        assert player.name == "Hero"
        assert player.level == 10
        assert player.hp == 300
        assert player.max_hp == 300
        assert player.attack == 50
        assert player.defense == 30
        assert player.speed == 40
        assert player.boost_points == 0
        assert player.max_boost_points == 5

    def test_player_negative_hp_raises_error(self):
        """Test that negative HP raises ValueError."""
        with pytest.raises(ValueError, match="hp cannot be negative"):
            create_test_player(hp=-10)

    def test_player_hp_exceeds_max_raises_error(self):
        """Test that HP > max_hp raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed max_hp"):
            create_test_player(hp=400, max_hp=300)

    def test_player_negative_bp_raises_error(self):
        """Test that negative BP raises ValueError."""
        with pytest.raises(ValueError, match="boost_points cannot be negative"):
            create_test_player(boost_points=-1)

    def test_player_bp_exceeds_max_raises_error(self):
        """Test that BP > max_boost_points raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed max_boost_points"):
            create_test_player(boost_points=6, max_boost_points=5)


class TestPlayerProperties:
    """Tests for Player property calculations."""

    def test_hp_percent_full_health(self):
        """Test HP percentage at full health."""
        player = create_test_player(hp=300, max_hp=300)
        assert player.hp_percent == 100.0

    def test_hp_percent_half_health(self):
        """Test HP percentage at half health."""
        player = create_test_player(hp=150, max_hp=300)
        assert player.hp_percent == 50.0

    def test_hp_percent_near_death(self):
        """Test HP percentage near death."""
        player = create_test_player(hp=1, max_hp=300)
        assert player.hp_percent == pytest.approx(0.33, abs=0.01)

    def test_is_alive_with_hp(self):
        """Test is_alive returns True when HP > 0."""
        player = create_test_player(hp=100)
        assert player.is_alive is True

    def test_is_alive_at_zero_hp(self):
        """Test is_alive returns False when HP = 0."""
        player = create_test_player(hp=0)
        assert player.is_alive is False

    def test_str_representation(self):
        """Test string representation includes BP."""
        player = create_test_player(name="Alice", level=5, hp=100, max_hp=150, boost_points=3)
        result = str(player)
        assert "Alice" in result
        assert "Lv5" in result
        assert "100/150 HP" in result
        assert "3/5 BP" in result


class TestPlayerBoostPoints:
    """Tests for Boost Point system."""

    def test_gain_bp_default_amount(self):
        """Test gaining 1 BP (default)."""
        player = create_test_player(boost_points=2)
        gained = player.gain_bp()

        assert gained == 1
        assert player.boost_points == 3

    def test_gain_bp_custom_amount(self):
        """Test gaining custom BP amount."""
        player = create_test_player(boost_points=1)
        gained = player.gain_bp(amount=2)

        assert gained == 2
        assert player.boost_points == 3

    def test_gain_bp_capped_at_max(self):
        """Test BP gain is capped at max_boost_points."""
        player = create_test_player(boost_points=4, max_boost_points=5)
        gained = player.gain_bp(amount=3)

        assert gained == 1  # Only 1 BP gained due to cap
        assert player.boost_points == 5

    def test_gain_bp_negative_raises_error(self):
        """Test that negative BP gain raises ValueError."""
        player = create_test_player()
        with pytest.raises(ValueError, match="BP gain amount cannot be negative"):
            player.gain_bp(amount=-1)

    def test_spend_bp_zero(self):
        """Test spending 0 BP returns 1.0x multiplier."""
        player = create_test_player(boost_points=3)
        multiplier = player.spend_bp(0)

        assert multiplier == 1.0
        assert player.boost_points == 3  # No BP spent

    def test_spend_bp_one(self):
        """Test spending 1 BP returns 1.5x multiplier."""
        player = create_test_player(boost_points=3)
        multiplier = player.spend_bp(1)

        assert multiplier == 1.5
        assert player.boost_points == 2

    def test_spend_bp_two(self):
        """Test spending 2 BP returns 2.0x multiplier."""
        player = create_test_player(boost_points=3)
        multiplier = player.spend_bp(2)

        assert multiplier == 2.0
        assert player.boost_points == 1

    def test_spend_bp_three(self):
        """Test spending 3 BP returns 2.5x multiplier."""
        player = create_test_player(boost_points=3)
        multiplier = player.spend_bp(3)

        assert multiplier == 2.5
        assert player.boost_points == 0

    def test_spend_bp_insufficient_raises_error(self):
        """Test spending more BP than available raises ValueError."""
        player = create_test_player(boost_points=1)
        with pytest.raises(ValueError, match="Not enough BP"):
            player.spend_bp(2)

    def test_spend_bp_invalid_amount_raises_error(self):
        """Test spending invalid BP amount raises ValueError."""
        player = create_test_player(boost_points=5)

        with pytest.raises(ValueError, match="Can only spend 0-3 BP"):
            player.spend_bp(4)

        with pytest.raises(ValueError, match="Can only spend 0-3 BP"):
            player.spend_bp(-1)


class TestPlayerDamage:
    """Tests for Player damage application."""

    def test_take_damage_normal(self):
        """Test taking normal damage."""
        player = create_test_player(hp=300)
        result = player.take_damage(50, DamageType.PHYSICAL)

        assert result.damage == 50
        assert player.hp == 250
        assert result.weakness_hit is False
        assert result.shield_broken is False

    def test_take_damage_reduces_to_zero(self):
        """Test damage reduces HP to 0 but not below."""
        player = create_test_player(hp=30)
        result = player.take_damage(50, DamageType.FIRE)

        assert result.damage == 30  # Only dealt actual HP
        assert player.hp == 0
        assert player.is_alive is False

    def test_take_damage_negative_raises_error(self):
        """Test negative damage raises ValueError."""
        player = create_test_player()
        with pytest.raises(ValueError, match="Damage cannot be negative"):
            player.take_damage(-10, DamageType.PHYSICAL)


class TestPlayerHealing:
    """Tests for Player healing mechanics."""

    def test_heal_normal(self):
        """Test normal healing."""
        player = create_test_player(hp=200, max_hp=300)
        healed = player.heal(50)

        assert healed == 50
        assert player.hp == 250

    def test_heal_capped_at_max(self):
        """Test healing is capped at max_hp."""
        player = create_test_player(hp=280, max_hp=300)
        healed = player.heal(50)

        assert healed == 20  # Only healed to cap
        assert player.hp == 300

    def test_heal_negative_raises_error(self):
        """Test negative healing raises ValueError."""
        player = create_test_player()
        with pytest.raises(ValueError, match="Heal amount cannot be negative"):
            player.heal(-10)


# ============================================================================
# Enemy Tests
# ============================================================================


class TestEnemyInitialization:
    """Tests for Enemy initialization and validation."""

    def test_create_valid_enemy(self):
        """Test creating a valid enemy instance."""
        enemy = create_test_enemy()

        assert enemy.id == "enemy_1"
        assert enemy.name == "Goblin"
        assert enemy.level == 8
        assert enemy.hp == 200
        assert enemy.max_hp == 200
        assert enemy.shield_points == 3
        assert enemy.max_shield_points == 3
        assert enemy.weaknesses == [DamageType.FIRE, DamageType.ICE]
        assert enemy.is_broken is False
        assert enemy.break_turns_remaining == 0

    def test_enemy_negative_shield_raises_error(self):
        """Test that negative shield_points raises ValueError."""
        with pytest.raises(ValueError, match="shield_points cannot be negative"):
            create_test_enemy(shield_points=-1)

    def test_enemy_shield_exceeds_max_raises_error(self):
        """Test that shield > max_shield raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed max_shield_points"):
            create_test_enemy(shield_points=5, max_shield_points=3)


class TestEnemyProperties:
    """Tests for Enemy property calculations."""

    def test_str_representation_normal(self):
        """Test string representation with shield."""
        enemy = create_test_enemy(
            name="Orc", level=10, hp=150, max_hp=200, shield_points=3, max_shield_points=5
        )
        result = str(enemy)
        assert "Orc" in result
        assert "Lv10" in result
        assert "150/200 HP" in result
        assert "3/5 Shield" in result

    def test_str_representation_broken(self):
        """Test string representation when broken."""
        enemy = create_test_enemy(is_broken=True)
        result = str(enemy)
        assert "BROKEN" in result


class TestEnemyBreakSystem:
    """Tests for Break System mechanics."""

    def test_take_damage_normal_no_weakness(self):
        """Test damage without hitting weakness."""
        enemy = create_test_enemy(hp=200, shield_points=3, weaknesses=[DamageType.FIRE])
        result = enemy.take_damage(50, DamageType.PHYSICAL)

        assert result.damage == 50
        assert enemy.hp == 150
        assert result.weakness_hit is False
        assert result.shield_broken is False
        assert enemy.shield_points == 3  # Shield unchanged
        assert enemy.is_broken is False

    def test_take_damage_weakness_reduces_shield(self):
        """Test hitting weakness reduces shield."""
        enemy = create_test_enemy(hp=200, shield_points=3, weaknesses=[DamageType.FIRE])
        result = enemy.take_damage(50, DamageType.FIRE)

        assert result.damage == 50
        assert enemy.hp == 150
        assert result.weakness_hit is True
        assert result.shield_broken is False
        assert enemy.shield_points == 2  # Shield reduced by 1

    def test_take_damage_breaks_shield(self):
        """Test breaking shield triggers break state."""
        enemy = create_test_enemy(hp=200, shield_points=1, weaknesses=[DamageType.ICE])
        result = enemy.take_damage(50, DamageType.ICE)

        assert result.damage == 50
        assert result.weakness_hit is True
        assert result.shield_broken is True
        assert enemy.shield_points == 0
        assert enemy.is_broken is True
        assert enemy.break_turns_remaining == 1

    def test_take_damage_while_broken_bonus_damage(self):
        """Test taking damage while broken applies 1.5x multiplier."""
        enemy = create_test_enemy(hp=200)
        enemy.trigger_break()  # Manually break

        result = enemy.take_damage(100, DamageType.PHYSICAL)

        assert result.damage == 150  # 100 * 1.5
        assert enemy.hp == 50
        assert result.multipliers["break"] == 1.5

    def test_weakness_while_broken_no_shield_damage(self):
        """Test hitting weakness while broken doesn't reduce shield further."""
        enemy = create_test_enemy(hp=200, shield_points=3, weaknesses=[DamageType.FIRE])
        enemy.trigger_break()

        initial_shield = enemy.shield_points
        result = enemy.take_damage(50, DamageType.FIRE)

        assert result.weakness_hit is True
        assert enemy.shield_points == initial_shield  # No further reduction
        assert result.shield_broken is False  # Already broken

    def test_trigger_break(self):
        """Test manually triggering break."""
        enemy = create_test_enemy(shield_points=3)
        enemy.trigger_break()

        assert enemy.is_broken is True
        assert enemy.break_turns_remaining == 1
        assert enemy.shield_points == 0

    def test_process_turn_end_reduces_break_turns(self):
        """Test process_turn_end reduces break turns."""
        enemy = create_test_enemy()
        enemy.trigger_break()

        status = enemy.process_turn_end()

        assert enemy.break_turns_remaining == 0
        assert enemy.is_broken is False
        assert enemy.shield_points == 3  # Shield restored
        assert "shield has been restored" in status.lower()

    def test_process_turn_end_no_break_returns_none(self):
        """Test process_turn_end returns None when not broken."""
        enemy = create_test_enemy()
        status = enemy.process_turn_end()

        assert status is None


class TestEnemyDamageEdgeCases:
    """Tests for edge cases in enemy damage handling."""

    def test_damage_exceeding_hp(self):
        """Test damage exceeding HP caps at current HP."""
        enemy = create_test_enemy(hp=50)
        result = enemy.take_damage(200, DamageType.PHYSICAL)

        assert result.damage == 50  # Only dealt actual HP
        assert enemy.hp == 0
        assert enemy.is_alive is False

    def test_damage_negative_raises_error(self):
        """Test negative damage raises ValueError."""
        enemy = create_test_enemy()
        with pytest.raises(ValueError, match="Damage cannot be negative"):
            enemy.take_damage(-10, DamageType.PHYSICAL)

    def test_multiple_weakness_hits_break_progression(self):
        """Test multiple weakness hits until break."""
        enemy = create_test_enemy(
            hp=300, max_hp=300, shield_points=3, weaknesses=[DamageType.LIGHTNING]
        )

        # Hit 1: Shield 3 -> 2
        result1 = enemy.take_damage(30, DamageType.LIGHTNING)
        assert result1.shield_broken is False
        assert enemy.shield_points == 2

        # Hit 2: Shield 2 -> 1
        result2 = enemy.take_damage(30, DamageType.LIGHTNING)
        assert result2.shield_broken is False
        assert enemy.shield_points == 1

        # Hit 3: Shield 1 -> 0 (BREAK)
        result3 = enemy.take_damage(30, DamageType.LIGHTNING)
        assert result3.shield_broken is True
        assert enemy.is_broken is True


# ============================================================================
# Combatant Base Class Tests
# ============================================================================


class TestCombatantHealing:
    """Tests for Combatant healing (via Player/Enemy)."""

    def test_enemy_healing(self):
        """Test enemy healing works."""
        enemy = create_test_enemy(hp=100, max_hp=200)
        healed = enemy.heal(50)

        assert healed == 50
        assert enemy.hp == 150


# ============================================================================
# Integration Tests
# ============================================================================


class TestCombatIntegration:
    """Integration tests for combat entity interactions."""

    def test_player_vs_enemy_basic_combat(self):
        """Test basic player vs enemy combat flow."""
        player = create_test_player(hp=300, attack=50, boost_points=2)
        enemy = create_test_enemy(hp=200, shield_points=2, weaknesses=[DamageType.FIRE])

        # Player spends 1 BP for 1.5x damage
        boost_mult = player.spend_bp(1)
        assert boost_mult == 1.5
        assert player.boost_points == 1

        # Player attacks with fire (hits weakness)
        enemy_result = enemy.take_damage(75, DamageType.FIRE)  # 50 * 1.5
        assert enemy_result.weakness_hit is True
        assert enemy.shield_points == 1
        assert enemy.hp == 125

        # Enemy counter-attacks
        player.take_damage(40, DamageType.PHYSICAL)
        assert player.hp == 260

        # Player gains BP
        player.gain_bp()
        assert player.boost_points == 2

        assert player.is_alive
        assert enemy.is_alive
