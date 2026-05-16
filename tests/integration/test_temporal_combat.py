"""
Integration tests for TemporalSystem wiring in CombatContext.

Verifies:
- CombatContext exposes temporal_system property
- Combatants start with temporal_charge = 0
- start_round emits CHARGE_REGENERATED events for player and living enemies
- Charges cap correctly across multiple rounds
- Dead enemies do not receive charge regen
"""

import json

from src.core.combat import CombatPhase
from src.core.events import EventTypes
from src.core.persistence import EventStore
from src.core.temporal import TemporalSystem
from tests.fixtures.combat_fixtures import create_1v3_context, create_combat_context
from tests.fixtures.entity_fixtures import create_test_player

# ============================================================================
# temporal_system property
# ============================================================================


class TestCombatContextTemporalSystem:
    """Tests for CombatContext.temporal_system exposure."""

    def test_temporal_system_property_returns_temporal_system(self) -> None:
        """CombatContext.temporal_system is a TemporalSystem instance."""
        ctx = create_combat_context()
        assert isinstance(ctx.temporal_system, TemporalSystem)

    def test_temporal_system_is_same_instance_across_calls(self) -> None:
        """temporal_system property returns the same object each time."""
        ctx = create_combat_context()
        assert ctx.temporal_system is ctx.temporal_system


# ============================================================================
# Initial charge state
# ============================================================================


class TestInitialChargeState:
    """Combatants start each combat with temporal_charge = 0."""

    def test_player_starts_with_zero_charge(self) -> None:
        """Player temporal_charge is 0 at combat start."""
        ctx = create_combat_context()
        assert ctx.player.temporal_charge == 0

    def test_enemy_starts_with_zero_charge(self) -> None:
        """Enemy temporal_charge is 0 at combat start."""
        ctx = create_combat_context()
        assert ctx.enemies[0].temporal_charge == 0

    def test_multiple_enemies_start_with_zero_charge(self) -> None:
        """All enemies have 0 charge at combat start in a 1v3."""
        ctx = create_1v3_context()
        for enemy in ctx.enemies:
            assert enemy.temporal_charge == 0


# ============================================================================
# Per-round regen via start_round
# ============================================================================


class TestRoundStartChargeRegen:
    """Tests for charge regeneration triggered by start_round()."""

    def test_start_round_increases_player_charge(self) -> None:
        """Player gains 1 charge at round start."""
        ctx = create_combat_context()
        ctx.start_round()
        assert ctx.player.temporal_charge == 1

    def test_start_round_increases_enemy_charge(self) -> None:
        """Living enemy gains 1 charge at round start."""
        ctx = create_combat_context()
        ctx.start_round()
        assert ctx.enemies[0].temporal_charge == 1

    def test_start_round_emits_player_charge_regenerated_event(self) -> None:
        """CHARGE_REGENERATED event is emitted for the player."""
        store = EventStore(":memory:")
        ctx = create_combat_context(event_store=store)
        ctx.start_round()
        events = store.get_events_by_timeline("timeline_main")
        regen_events = [e for e in events if e.event_type == EventTypes.CHARGE_REGENERATED]
        assert any(json.loads(e.event_data)["actor_id"] == "player_1" for e in regen_events)

    def test_start_round_emits_enemy_charge_regenerated_event(self) -> None:
        """CHARGE_REGENERATED event is emitted for each living enemy."""
        store = EventStore(":memory:")
        ctx = create_combat_context(event_store=store)
        ctx.start_round()
        events = store.get_events_by_timeline("timeline_main")
        regen_events = [e for e in events if e.event_type == EventTypes.CHARGE_REGENERATED]
        assert any(json.loads(e.event_data)["actor_id"] == "enemy_1" for e in regen_events)

    def test_start_round_emits_regen_for_all_living_enemies(self) -> None:
        """CHARGE_REGENERATED is emitted for each living enemy in a 1v3."""
        store = EventStore(":memory:")
        ctx = create_1v3_context(event_store=store)
        ctx.start_round()
        events = store.get_events_by_timeline("timeline_main")
        regen_events = [e for e in events if e.event_type == EventTypes.CHARGE_REGENERATED]
        actor_ids = {json.loads(e.event_data)["actor_id"] for e in regen_events}
        # Player + 3 enemies = 4 regen events
        assert "player_1" in actor_ids
        assert "enemy_1" in actor_ids
        assert "enemy_2" in actor_ids
        assert "enemy_3" in actor_ids

    def test_no_regen_event_for_dead_enemy(self) -> None:
        """Dead enemy does not receive a charge regen event."""
        store = EventStore(":memory:")
        ctx = create_1v3_context(event_store=store)
        # Kill enemy_1 before round starts
        ctx.enemies[0].hp = 0
        ctx.start_round()
        events = store.get_events_by_timeline("timeline_main")
        regen_events = [e for e in events if e.event_type == EventTypes.CHARGE_REGENERATED]
        actor_ids = {json.loads(e.event_data)["actor_id"] for e in regen_events}
        assert "enemy_1" not in actor_ids

    def test_charge_caps_at_max_across_rounds(self) -> None:
        """Charge does not exceed max_temporal_charge after many rounds."""
        ctx = create_combat_context()
        # Run 5 rounds — max is 3, so charge should cap at 3
        for _ in range(5):
            ctx.start_round()
            # Drain phase to allow next round
            ctx._phase = ctx._phase  # no-op; just don't advance turns

        assert ctx.player.temporal_charge <= ctx.player.max_temporal_charge
        assert ctx.player.temporal_charge == 3

    def test_no_regen_event_when_charge_already_at_max(self) -> None:
        """No CHARGE_REGENERATED event for a combatant already at cap."""
        store = EventStore(":memory:")
        # Player starts at max charge
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        ctx = create_combat_context(player=player, event_store=store)
        ctx.start_round()
        events = store.get_events_by_timeline("timeline_main")
        regen_events = [e for e in events if e.event_type == EventTypes.CHARGE_REGENERATED]
        player_regen = [
            e for e in regen_events if json.loads(e.event_data)["actor_id"] == "player_1"
        ]
        assert len(player_regen) == 0

    def test_second_round_continues_to_accumulate_charge(self) -> None:
        """Charge increments over multiple rounds until capped."""
        ctx = create_combat_context()
        ctx.start_round()
        assert ctx.player.temporal_charge == 1
        # Simulate enough state to call start_round again
        ctx._phase = CombatPhase.ROUND_START
        ctx.start_round()
        assert ctx.player.temporal_charge == 2
