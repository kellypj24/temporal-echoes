"""
Unit tests for TemporalCharge resource on Combatant.

Covers validation, gain_charge (cap, actual returned, negative rejection),
spend_charge (insufficient, exact spend, negative rejection, edge cases).
"""

import pytest

from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player

# ============================================================================
# Validation tests (via __post_init__)
# ============================================================================


class TestTemporalChargeValidation:
    """Tests for temporal_charge and max_temporal_charge validation."""

    def test_default_temporal_charge_is_zero(self) -> None:
        """Player starts with 0 temporal_charge by default."""
        player = create_test_player()
        assert player.temporal_charge == 0

    def test_default_max_temporal_charge_is_three(self) -> None:
        """Default max_temporal_charge matches DESIGN cap of 3."""
        player = create_test_player()
        assert player.max_temporal_charge == 3

    def test_enemy_default_temporal_charge_is_zero(self) -> None:
        """Enemy starts with 0 temporal_charge by default."""
        enemy = create_test_enemy()
        assert enemy.temporal_charge == 0

    def test_negative_temporal_charge_raises_error(self) -> None:
        """temporal_charge cannot be negative."""
        with pytest.raises(ValueError, match="temporal_charge cannot be negative"):
            create_test_player(temporal_charge=-1)

    def test_zero_max_temporal_charge_raises_error(self) -> None:
        """max_temporal_charge must be > 0."""
        with pytest.raises(ValueError, match="max_temporal_charge must be positive"):
            create_test_player(max_temporal_charge=0)

    def test_negative_max_temporal_charge_raises_error(self) -> None:
        """max_temporal_charge cannot be negative."""
        with pytest.raises(ValueError, match="max_temporal_charge must be positive"):
            create_test_player(max_temporal_charge=-1)

    def test_temporal_charge_exceeds_max_raises_error(self) -> None:
        """temporal_charge cannot exceed max_temporal_charge."""
        with pytest.raises(ValueError, match="temporal_charge.*cannot exceed"):
            create_test_player(temporal_charge=4, max_temporal_charge=3)

    def test_temporal_charge_equal_to_max_is_valid(self) -> None:
        """temporal_charge == max_temporal_charge is allowed."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        assert player.temporal_charge == 3

    def test_custom_max_temporal_charge(self) -> None:
        """Custom max_temporal_charge is respected."""
        player = create_test_player(max_temporal_charge=5)
        assert player.max_temporal_charge == 5


# ============================================================================
# gain_charge tests
# ============================================================================


class TestGainCharge:
    """Tests for Combatant.gain_charge()."""

    def test_gain_charge_default_amount_returns_one(self) -> None:
        """Default gain_charge() returns 1 when below cap."""
        player = create_test_player()
        actual = player.gain_charge()
        assert actual == 1
        assert player.temporal_charge == 1

    def test_gain_charge_custom_amount(self) -> None:
        """gain_charge(2) adds 2 when space remains."""
        player = create_test_player()
        actual = player.gain_charge(2)
        assert actual == 2
        assert player.temporal_charge == 2

    def test_gain_charge_capped_at_max(self) -> None:
        """gain_charge does not exceed max_temporal_charge."""
        player = create_test_player(temporal_charge=2, max_temporal_charge=3)
        actual = player.gain_charge(5)
        assert actual == 1
        assert player.temporal_charge == 3

    def test_gain_charge_returns_zero_when_already_at_max(self) -> None:
        """gain_charge returns 0 when already at cap; no state change."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        actual = player.gain_charge(1)
        assert actual == 0
        assert player.temporal_charge == 3

    def test_gain_charge_zero_amount(self) -> None:
        """gain_charge(0) is a no-op and returns 0."""
        player = create_test_player(temporal_charge=1, max_temporal_charge=3)
        actual = player.gain_charge(0)
        assert actual == 0
        assert player.temporal_charge == 1

    def test_gain_charge_negative_raises_error(self) -> None:
        """Negative amount raises ValueError."""
        player = create_test_player()
        with pytest.raises(ValueError, match="Charge gain amount cannot be negative"):
            player.gain_charge(-1)

    def test_gain_charge_returns_actual_gained(self) -> None:
        """Return value is the delta, not the requested amount."""
        player = create_test_player(temporal_charge=2, max_temporal_charge=3)
        actual = player.gain_charge(10)
        assert actual == 1  # only 1 space left

    def test_gain_charge_enemy(self) -> None:
        """Enemies gain charge identically to the player (symmetric mechanic)."""
        enemy = create_test_enemy()
        actual = enemy.gain_charge(2)
        assert actual == 2
        assert enemy.temporal_charge == 2


# ============================================================================
# spend_charge tests
# ============================================================================


class TestSpendCharge:
    """Tests for Combatant.spend_charge()."""

    def test_spend_charge_reduces_by_amount(self) -> None:
        """spend_charge deducts the correct amount."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        player.spend_charge(2)
        assert player.temporal_charge == 1

    def test_spend_charge_exact_amount_reaches_zero(self) -> None:
        """Spending exactly current charge leaves 0."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        player.spend_charge(3)
        assert player.temporal_charge == 0

    def test_spend_charge_one_from_one(self) -> None:
        """Spending 1 from 1 reaches 0."""
        player = create_test_player(temporal_charge=1, max_temporal_charge=3)
        player.spend_charge(1)
        assert player.temporal_charge == 0

    def test_spend_charge_insufficient_raises_error(self) -> None:
        """Spending more than available raises ValueError."""
        player = create_test_player(temporal_charge=1, max_temporal_charge=3)
        with pytest.raises(ValueError, match="Not enough temporal charge"):
            player.spend_charge(2)

    def test_spend_charge_on_empty_raises_error(self) -> None:
        """Spending when charge is 0 raises ValueError."""
        player = create_test_player()
        with pytest.raises(ValueError, match="Not enough temporal charge"):
            player.spend_charge(1)

    def test_spend_charge_negative_raises_error(self) -> None:
        """Negative amount raises ValueError."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        with pytest.raises(ValueError, match="Charge spend amount cannot be negative"):
            player.spend_charge(-1)

    def test_spend_charge_zero_is_noop(self) -> None:
        """Spending 0 is valid and does not change state."""
        player = create_test_player(temporal_charge=2, max_temporal_charge=3)
        player.spend_charge(0)
        assert player.temporal_charge == 2

    def test_spend_charge_no_return_value(self) -> None:
        """spend_charge returns None (pure gate, unlike BP which returns multiplier)."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        result = player.spend_charge(1)
        assert result is None

    def test_spend_charge_enemy(self) -> None:
        """Enemies spend charge identically to the player (symmetric mechanic)."""
        enemy = create_test_enemy(temporal_charge=2, max_temporal_charge=3)
        enemy.spend_charge(2)
        assert enemy.temporal_charge == 0
