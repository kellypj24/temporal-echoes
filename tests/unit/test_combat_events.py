"""
Unit tests for combat event builder.

Tests for CombatEventBuilder class including:
- Event creation with correct schemas
- Validation of required fields
- JSON payload correctness
- Integration with Phase 1 EventStore
- Event retrieval by combat_id
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.core.combat_events import CombatEventBuilder
from src.core.events import EventTypes
from src.core.persistence import EventStore

# ============================================================================
# Initialization Tests
# ============================================================================


class TestCombatEventBuilderInitialization:
    """Tests for CombatEventBuilder initialization."""

    def test_create_with_valid_params(self):
        """Test creating builder with valid parameters."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        assert builder.session_id == "sess_001"
        assert builder.timeline_id == "main"
        assert builder.combat_id == "combat_001"

    def test_empty_session_id_raises_error(self):
        """Test empty session_id raises ValueError."""
        with pytest.raises(ValueError, match="session_id is required"):
            CombatEventBuilder(session_id="", timeline_id="main", combat_id="combat_001")

    def test_empty_timeline_id_raises_error(self):
        """Test empty timeline_id raises ValueError."""
        with pytest.raises(ValueError, match="timeline_id is required"):
            CombatEventBuilder(session_id="sess_001", timeline_id="", combat_id="combat_001")

    def test_empty_combat_id_raises_error(self):
        """Test empty combat_id raises ValueError."""
        with pytest.raises(ValueError, match="combat_id is required"):
            CombatEventBuilder(session_id="sess_001", timeline_id="main", combat_id="")


# ============================================================================
# CombatStarted Event Tests
# ============================================================================


class TestCombatStartedEvent:
    """Tests for combat_started() event creation."""

    def test_create_basic_combat_started(self):
        """Test creating basic CombatStarted event."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.combat_started(
            rng_seed=42,
            player={"id": "player_1", "hp": 300},
            enemies=[{"id": "enemy_1", "hp": 200}],
        )

        assert event.event_type == EventTypes.COMBAT_STARTED
        assert event.aggregate_id == "combat_001"
        assert event.aggregate_type == "combat"
        assert event.session_id == "sess_001"
        assert event.timeline_id == "main"

        data = json.loads(event.event_data)
        assert data["combat_id"] == "combat_001"
        assert data["rng_seed"] == 42
        assert data["player"]["id"] == "player_1"
        assert len(data["enemies"]) == 1

    def test_combat_started_with_location(self):
        """Test CombatStarted event with optional location."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.combat_started(
            rng_seed=42,
            player={"id": "player_1"},
            enemies=[{"id": "enemy_1"}],
            location="Forest Path",
        )

        data = json.loads(event.event_data)
        assert data["location"] == "Forest Path"

    def test_combat_started_with_kwargs(self):
        """Test CombatStarted with additional kwargs."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.combat_started(
            rng_seed=42,
            player={"id": "player_1"},
            enemies=[{"id": "enemy_1"}],
            combat_type="boss",
            difficulty="hard",
        )

        data = json.loads(event.event_data)
        assert data["combat_type"] == "boss"
        assert data["difficulty"] == "hard"


# ============================================================================
# CombatEnded Event Tests
# ============================================================================


class TestCombatEndedEvent:
    """Tests for combat_ended() event creation."""

    def test_create_basic_combat_ended(self):
        """Test creating basic CombatEnded event."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.combat_ended(outcome="victory", victory=True, total_turns=12)

        assert event.event_type == EventTypes.COMBAT_ENDED
        assert event.aggregate_id == "combat_001"

        data = json.loads(event.event_data)
        assert data["outcome"] == "victory"
        assert data["victory"] is True
        assert data["total_turns"] == 12

    def test_combat_ended_with_rewards(self):
        """Test CombatEnded event with rewards."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.combat_ended(
            outcome="victory",
            victory=True,
            total_turns=15,
            rewards={"exp": 150, "gold": 50},
        )

        data = json.loads(event.event_data)
        assert data["rewards"]["exp"] == 150
        assert data["rewards"]["gold"] == 50

    def test_combat_ended_with_duration(self):
        """Test CombatEnded with duration."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.combat_ended(
            outcome="victory", victory=True, total_turns=10, duration_ms=45000.5
        )

        data = json.loads(event.event_data)
        assert data["duration_ms"] == 45000.5


# ============================================================================
# TurnStarted Event Tests
# ============================================================================


class TestTurnStartedEvent:
    """Tests for turn_started() event creation."""

    def test_create_turn_started(self):
        """Test creating TurnStarted event."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.turn_started(turn_number=1, active_combatant_id="player_1")

        assert event.event_type == EventTypes.TURN_STARTED
        assert event.aggregate_id == "combat_001"

        data = json.loads(event.event_data)
        assert data["turn_number"] == 1
        assert data["active_combatant_id"] == "player_1"


# ============================================================================
# ActionExecuted Event Tests
# ============================================================================


class TestActionExecutedEvent:
    """Tests for action_executed() event creation."""

    def test_create_basic_attack_action(self):
        """Test creating basic attack ActionExecuted event."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.action_executed(
            turn_number=1,
            actor_id="player_1",
            action_type="attack",
            target_id="enemy_1",
            damage_dealt=75,
        )

        assert event.event_type == EventTypes.ACTION_EXECUTED
        assert event.aggregate_id == "combat_001"

        data = json.loads(event.event_data)
        assert data["turn_number"] == 1
        assert data["actor_id"] == "player_1"
        assert data["action_type"] == "attack"
        assert data["target_id"] == "enemy_1"
        assert data["damage_dealt"] == 75

    def test_action_with_boost_points(self):
        """Test ActionExecuted with boost points spent."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.action_executed(
            turn_number=2,
            actor_id="player_1",
            action_type="attack",
            target_id="enemy_1",
            damage_dealt=150,
            boost_points_spent=2,
        )

        data = json.loads(event.event_data)
        assert data["boost_points_spent"] == 2

    def test_action_with_critical_and_weakness(self):
        """Test ActionExecuted with critical hit and weakness."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.action_executed(
            turn_number=3,
            actor_id="player_1",
            action_type="attack",
            target_id="enemy_1",
            damage_dealt=200,
            was_critical=True,
            was_weakness=True,
        )

        data = json.loads(event.event_data)
        assert data["was_critical"] is True
        assert data["was_weakness"] is True

    def test_action_with_healing(self):
        """Test ActionExecuted with healing."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.action_executed(
            turn_number=4,
            actor_id="player_1",
            action_type="item",
            healing_done=100,
        )

        data = json.loads(event.event_data)
        assert data["action_type"] == "item"
        assert data["healing_done"] == 100

    def test_action_with_kwargs(self):
        """Test ActionExecuted with additional kwargs."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.action_executed(
            turn_number=5,
            actor_id="player_1",
            action_type="ability",
            target_id="enemy_1",
            damage_dealt=125,
            skill_name="Fireball",
            damage_type="FIRE",
            multipliers={"boost": 1.5, "type": 2.0},
        )

        data = json.loads(event.event_data)
        assert data["skill_name"] == "Fireball"
        assert data["damage_type"] == "FIRE"
        assert data["multipliers"]["boost"] == 1.5


# ============================================================================
# ShieldBroken Event Tests
# ============================================================================


class TestShieldBrokenEvent:
    """Tests for shield_broken() event creation."""

    def test_create_shield_broken(self):
        """Test creating ShieldBroken event."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.shield_broken(
            turn_number=3,
            combatant_id="enemy_1",
            broke_by="player_1",
            damage_type="FIRE",
        )

        assert event.event_type == EventTypes.SHIELD_BROKEN
        assert event.aggregate_id == "combat_001"

        data = json.loads(event.event_data)
        assert data["turn_number"] == 3
        assert data["combatant_id"] == "enemy_1"
        assert data["broke_by"] == "player_1"
        assert data["damage_type"] == "FIRE"


# ============================================================================
# BoostPointGained Event Tests
# ============================================================================


class TestBoostPointGainedEvent:
    """Tests for boost_point_gained() event creation."""

    def test_create_boost_point_gained(self):
        """Test creating BoostPointGained event."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.boost_point_gained(turn_number=2, combatant_id="player_1", new_total=3)

        assert event.event_type == EventTypes.BOOST_POINT_GAINED
        assert event.aggregate_id == "combat_001"

        data = json.loads(event.event_data)
        assert data["turn_number"] == 2
        assert data["combatant_id"] == "player_1"
        assert data["new_total"] == 3

    def test_boost_point_gained_with_amount(self):
        """Test BoostPointGained with amount_gained."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.boost_point_gained(
            turn_number=2, combatant_id="player_1", new_total=3, amount_gained=1
        )

        data = json.loads(event.event_data)
        assert data["amount_gained"] == 1


# ============================================================================
# CombatantDefeated Event Tests
# ============================================================================


class TestCombatantDefeatedEvent:
    """Tests for combatant_defeated() event creation."""

    def test_create_combatant_defeated(self):
        """Test creating CombatantDefeated event."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.combatant_defeated(
            turn_number=8,
            combatant_id="enemy_1",
            defeated_by="player_1",
            final_damage=45,
        )

        assert event.event_type == EventTypes.COMBATANT_DEFEATED
        assert event.aggregate_id == "combat_001"

        data = json.loads(event.event_data)
        assert data["turn_number"] == 8
        assert data["combatant_id"] == "enemy_1"
        assert data["defeated_by"] == "player_1"
        assert data["final_damage"] == 45


# ============================================================================
# CombatFled Event Tests
# ============================================================================


class TestCombatFledEvent:
    """Tests for combat_fled() event creation."""

    def test_create_combat_fled_success(self):
        """Test creating CombatFled event (success)."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.combat_fled(turn_number=5, flee_success=True, fled_by="player_1")

        assert event.event_type == EventTypes.COMBAT_FLED
        assert event.aggregate_id == "combat_001"

        data = json.loads(event.event_data)
        assert data["turn_number"] == 5
        assert data["flee_success"] is True
        assert data["fled_by"] == "player_1"

    def test_create_combat_fled_failure(self):
        """Test creating CombatFled event (failure)."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.combat_fled(
            turn_number=3, flee_success=False, fled_by="player_1", flee_chance=0.5
        )

        data = json.loads(event.event_data)
        assert data["flee_success"] is False
        assert data["flee_chance"] == 0.5


# ============================================================================
# EventStore Integration Tests
# ============================================================================


class TestEventStoreIntegration:
    """Integration tests with Phase 1 EventStore."""

    def test_store_and_retrieve_combat_events(self):
        """Test storing and retrieving combat events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_combat_events.db"
            store = EventStore(str(db_path))

            builder = CombatEventBuilder(
                session_id="sess_001", timeline_id="main", combat_id="combat_001"
            )

            # Create and store multiple events
            events = [
                builder.combat_started(
                    rng_seed=42,
                    player={"id": "player_1", "hp": 300},
                    enemies=[{"id": "enemy_1", "hp": 200}],
                ),
                builder.turn_started(turn_number=1, active_combatant_id="player_1"),
                builder.action_executed(
                    turn_number=1,
                    actor_id="player_1",
                    action_type="attack",
                    target_id="enemy_1",
                    damage_dealt=75,
                ),
                builder.combat_ended(outcome="victory", victory=True, total_turns=5),
            ]

            for event in events:
                store.append_event(event)

            # Retrieve all events from session and filter by aggregate_id (combat_id)
            # Note: EventStore doesn't have get_events_by_aggregate yet (Phase 1 limitation)
            all_events = store.get_events_by_session("sess_001")
            retrieved = [e for e in all_events if e.aggregate_id == "combat_001"]

            assert len(retrieved) == 4
            assert retrieved[0].event_type == EventTypes.COMBAT_STARTED
            assert retrieved[1].event_type == EventTypes.TURN_STARTED
            assert retrieved[2].event_type == EventTypes.ACTION_EXECUTED
            assert retrieved[3].event_type == EventTypes.COMBAT_ENDED

    def test_events_are_immutable(self):
        """Test that combat events are immutable."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        event = builder.combat_started(
            rng_seed=42,
            player={"id": "player_1"},
            enemies=[{"id": "enemy_1"}],
        )

        # Events are frozen dataclasses - should raise FrozenInstanceError
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            event.event_type = "SomethingElse"

    def test_multiple_combats_in_same_session(self):
        """Test storing events from multiple combats in same session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_multi_combat.db"
            store = EventStore(str(db_path))

            # Combat 1
            builder1 = CombatEventBuilder(
                session_id="sess_001", timeline_id="main", combat_id="combat_001"
            )
            store.append_event(
                builder1.combat_started(
                    rng_seed=42,
                    player={"id": "player_1"},
                    enemies=[{"id": "enemy_1"}],
                )
            )
            store.append_event(
                builder1.combat_ended(outcome="victory", victory=True, total_turns=5)
            )

            # Combat 2
            builder2 = CombatEventBuilder(
                session_id="sess_001", timeline_id="main", combat_id="combat_002"
            )
            store.append_event(
                builder2.combat_started(
                    rng_seed=99,
                    player={"id": "player_1"},
                    enemies=[{"id": "enemy_2"}],
                )
            )
            store.append_event(
                builder2.combat_ended(outcome="defeat", victory=False, total_turns=3)
            )

            # Retrieve by session
            session_events = store.get_events_by_session("sess_001")
            assert len(session_events) == 4

            # Filter by combat_id (aggregate_id)
            # Note: EventStore doesn't have get_events_by_aggregate yet (Phase 1 limitation)
            combat1_events = [e for e in session_events if e.aggregate_id == "combat_001"]
            combat2_events = [e for e in session_events if e.aggregate_id == "combat_002"]

            assert len(combat1_events) == 2
            assert len(combat2_events) == 2

            # Verify data
            combat1_data = json.loads(combat1_events[0].event_data)
            combat2_data = json.loads(combat2_events[0].event_data)

            assert combat1_data["rng_seed"] == 42
            assert combat2_data["rng_seed"] == 99


# ============================================================================
# Event Sequence Tests
# ============================================================================


class TestEventSequences:
    """Tests for realistic combat event sequences."""

    def test_full_combat_sequence(self):
        """Test creating a full combat sequence."""
        builder = CombatEventBuilder(
            session_id="sess_001", timeline_id="main", combat_id="combat_001"
        )

        # Full combat sequence
        events = [
            builder.combat_started(
                rng_seed=42,
                player={"id": "player_1", "hp": 300, "boost_points": 0},
                enemies=[{"id": "enemy_1", "hp": 200, "shields": 3}],
            ),
            builder.turn_started(turn_number=1, active_combatant_id="player_1"),
            builder.action_executed(
                turn_number=1,
                actor_id="player_1",
                action_type="attack",
                target_id="enemy_1",
                damage_dealt=50,
            ),
            builder.boost_point_gained(turn_number=1, combatant_id="player_1", new_total=1),
            builder.turn_started(turn_number=2, active_combatant_id="enemy_1"),
            builder.action_executed(
                turn_number=2,
                actor_id="enemy_1",
                action_type="attack",
                target_id="player_1",
                damage_dealt=40,
            ),
            builder.turn_started(turn_number=3, active_combatant_id="player_1"),
            builder.action_executed(
                turn_number=3,
                actor_id="player_1",
                action_type="attack",
                target_id="enemy_1",
                damage_dealt=100,
                was_weakness=True,
            ),
            builder.shield_broken(
                turn_number=3,
                combatant_id="enemy_1",
                broke_by="player_1",
                damage_type="FIRE",
            ),
            builder.combatant_defeated(
                turn_number=3,
                combatant_id="enemy_1",
                defeated_by="player_1",
                final_damage=100,
            ),
            builder.combat_ended(
                outcome="victory",
                victory=True,
                total_turns=3,
                rewards={"exp": 150, "gold": 50},
            ),
        ]

        # All events should be valid
        assert len(events) == 11
        assert all(event.aggregate_id == "combat_001" for event in events)

        # Verify all event types are valid EventTypes
        valid_event_types = {
            EventTypes.COMBAT_STARTED,
            EventTypes.COMBAT_ENDED,
            EventTypes.TURN_STARTED,
            EventTypes.ACTION_EXECUTED,
            EventTypes.SHIELD_BROKEN,
            EventTypes.BOOST_POINT_GAINED,
            EventTypes.COMBATANT_DEFEATED,
        }
        assert all(event.event_type in valid_event_types for event in events)
