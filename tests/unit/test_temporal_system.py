"""
Unit tests for TemporalSystem skeleton.

Covers:
- spend() emits CHARGE_SPENT with correct payload and mutates actor
- regenerate() emits CHARGE_REGENERATED only when actually gained > 0
- regenerate() does not emit when actor is at max charge
- rewind, echo_cast, and counter_stop are all implemented as of Step 6 —
  see test_temporal.py / test_echo.py / test_counter_stop.py. There is no
  public counter_stop() API (Phase 3 Step 6 locked semantic 11: it only
  exists as a response inside the Counter-Stop window), so no stub or
  seam test remains in this file.
"""

import json

import pytest

from src.core.combat_events import CombatEventBuilder
from src.core.events import EventTypes
from src.core.persistence import EventStore
from src.core.temporal import TemporalSystem
from tests.fixtures.entity_fixtures import create_test_player

# ============================================================================
# Helpers
# ============================================================================


def make_system(
    session_id: str = "sess_001",
    timeline_id: str = "main",
    combat_id: str = "combat_001",
) -> tuple[TemporalSystem, EventStore, CombatEventBuilder]:
    """Create a TemporalSystem with in-memory store and builder."""
    store = EventStore(":memory:")
    builder = CombatEventBuilder(
        session_id=session_id,
        timeline_id=timeline_id,
        combat_id=combat_id,
    )
    system = TemporalSystem(event_store=store, event_builder=builder)
    return system, store, builder


# ============================================================================
# spend() tests
# ============================================================================


class TestTemporalSystemSpend:
    """Tests for TemporalSystem.spend()."""

    def test_spend_emits_charge_spent_event(self) -> None:
        """spend() emits a CHARGE_SPENT event to the store."""
        system, store, _ = make_system()
        player = create_test_player(temporal_charge=2)
        system.spend(actor=player, amount=1, ability="rewind", turn_number=3)
        events = store.get_events_by_timeline("main")
        charge_events = [e for e in events if e.event_type == EventTypes.CHARGE_SPENT]
        assert len(charge_events) == 1

    def test_spend_event_payload_is_correct(self) -> None:
        """CHARGE_SPENT event carries actor_id, amount, ability, turn_number."""
        system, store, _ = make_system()
        player = create_test_player(temporal_charge=3)
        system.spend(actor=player, amount=2, ability="rewind", turn_number=5)
        events = store.get_events_by_timeline("main")
        event = next(e for e in events if e.event_type == EventTypes.CHARGE_SPENT)
        data = json.loads(event.event_data)
        assert data["actor_id"] == "player_1"
        assert data["amount"] == 2
        assert data["ability"] == "rewind"
        assert data["turn_number"] == 5

    def test_spend_event_carries_combat_id(self) -> None:
        """CHARGE_SPENT event aggregate_id is the combat_id."""
        system, store, _ = make_system(combat_id="fight_99")
        player = create_test_player(temporal_charge=1)
        system.spend(actor=player, amount=1, ability="rewind", turn_number=1)
        events = store.get_events_by_timeline("main")
        event = next(e for e in events if e.event_type == EventTypes.CHARGE_SPENT)
        assert event.aggregate_id == "fight_99"

    def test_spend_reduces_actor_charge(self) -> None:
        """spend() calls actor.spend_charge so temporal_charge is decremented."""
        system, _, _ = make_system()
        player = create_test_player(temporal_charge=3)
        system.spend(actor=player, amount=2, ability="rewind", turn_number=1)
        assert player.temporal_charge == 1

    def test_spend_insufficient_charge_raises_error(self) -> None:
        """spend() propagates ValueError from spend_charge when charge is low."""
        system, store, _ = make_system()
        player = create_test_player(temporal_charge=1)
        with pytest.raises(ValueError, match="Not enough temporal charge"):
            system.spend(actor=player, amount=2, ability="rewind", turn_number=1)

    def test_spend_insufficient_charge_still_emits_event(self) -> None:
        """CHARGE_SPENT event is emitted before spend_charge validation fires."""
        # The event is emitted before the actor mutation, so insufficient charge
        # will emit the event then raise. This is the Step 3 ordering convention.
        system, store, _ = make_system()
        player = create_test_player(temporal_charge=1)
        with pytest.raises(ValueError):
            system.spend(actor=player, amount=2, ability="rewind", turn_number=1)
        events = store.get_events_by_timeline("main")
        assert any(e.event_type == EventTypes.CHARGE_SPENT for e in events)

    def test_spend_event_branch_id_from_builder(self) -> None:
        """CHARGE_SPENT event carries branch_id from the builder."""
        system, store, builder = make_system()
        builder.set_branch(2)
        player = create_test_player(temporal_charge=3)
        system.spend(actor=player, amount=1, ability="rewind", turn_number=1)
        events = store.get_events_by_timeline("main")
        event = next(e for e in events if e.event_type == EventTypes.CHARGE_SPENT)
        assert event.branch_id == 2


# ============================================================================
# regenerate() tests
# ============================================================================


class TestTemporalSystemRegenerate:
    """Tests for TemporalSystem.regenerate()."""

    def test_regenerate_emits_charge_regenerated_event(self) -> None:
        """regenerate() emits CHARGE_REGENERATED when charge is actually gained."""
        system, store, _ = make_system()
        player = create_test_player(temporal_charge=0)
        system.regenerate(actor=player, amount=1, turn_number=0)
        events = store.get_events_by_timeline("main")
        regen_events = [e for e in events if e.event_type == EventTypes.CHARGE_REGENERATED]
        assert len(regen_events) == 1

    def test_regenerate_event_payload_is_correct(self) -> None:
        """CHARGE_REGENERATED event carries actor_id, amount, new_total."""
        system, store, _ = make_system()
        player = create_test_player(temporal_charge=1)
        system.regenerate(actor=player, amount=1, turn_number=2)
        events = store.get_events_by_timeline("main")
        event = next(e for e in events if e.event_type == EventTypes.CHARGE_REGENERATED)
        data = json.loads(event.event_data)
        assert data["actor_id"] == "player_1"
        assert data["amount"] == 1
        assert data["new_total"] == 2
        assert data["turn_number"] == 2

    def test_regenerate_no_event_when_already_at_max(self) -> None:
        """No CHARGE_REGENERATED event is emitted when actor is at cap."""
        system, store, _ = make_system()
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        system.regenerate(actor=player, amount=1, turn_number=0)
        events = store.get_events_by_timeline("main")
        regen_events = [e for e in events if e.event_type == EventTypes.CHARGE_REGENERATED]
        assert len(regen_events) == 0

    def test_regenerate_returns_actual_gained(self) -> None:
        """regenerate() returns the delta, not the requested amount."""
        system, _, _ = make_system()
        player = create_test_player(temporal_charge=2, max_temporal_charge=3)
        result = system.regenerate(actor=player, amount=5, turn_number=0)
        assert result == 1  # only 1 space left

    def test_regenerate_returns_zero_at_max(self) -> None:
        """regenerate() returns 0 when already at cap."""
        system, _, _ = make_system()
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        result = system.regenerate(actor=player, amount=1, turn_number=0)
        assert result == 0

    def test_regenerate_mutates_actor_charge(self) -> None:
        """regenerate() increases actor.temporal_charge."""
        system, _, _ = make_system()
        player = create_test_player(temporal_charge=0)
        system.regenerate(actor=player, amount=1, turn_number=0)
        assert player.temporal_charge == 1

    def test_regenerate_partial_gain_when_capped(self) -> None:
        """regenerate() emits event with partial actual amount when capped."""
        system, store, _ = make_system()
        player = create_test_player(temporal_charge=2, max_temporal_charge=3)
        system.regenerate(actor=player, amount=5, turn_number=0)
        events = store.get_events_by_timeline("main")
        event = next(e for e in events if e.event_type == EventTypes.CHARGE_REGENERATED)
        data = json.loads(event.event_data)
        assert data["amount"] == 1  # actual gained, not requested 5
        assert data["new_total"] == 3

    def test_regenerate_negative_amount_raises_error(self) -> None:
        """Negative amount propagates ValueError from gain_charge."""
        system, _, _ = make_system()
        player = create_test_player()
        with pytest.raises(ValueError, match="Charge gain amount cannot be negative"):
            system.regenerate(actor=player, amount=-1, turn_number=0)
