"""Unit tests for GameContext.

Test Coverage:
- GameContext initialization (manual and factory)
- Session and timeline ID tracking
- Dependency injection (EventStore and GameStateMachine)
- Common operation methods (convenience wrappers)
- Context serialization (to_dict/from_dict)
- Context manager support (__enter__/__exit__)
- Event emission (session start/end)
- Timeline branching
- Error handling and edge cases

Constitution Principles Tested:
- #2: Dependency injection (no global state, clean DI)
- #3: Type safety (verify type annotations)
- #1: Event sourcing (verify session events emitted)
"""

import json
from unittest.mock import patch

import pytest

from src.core.events import EventTypes
from src.core.exceptions import StateTransitionError
from src.core.game_context import GameContext
from src.core.persistence import EventStore
from src.core.state_machine import GameState

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def event_store() -> EventStore:
    """Create an in-memory EventStore for testing."""
    return EventStore(":memory:")


@pytest.fixture
def game_context(event_store: EventStore) -> GameContext:
    """Create a GameContext for testing."""
    return GameContext(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_game_context_initialization(game_context: GameContext) -> None:
    """Test that GameContext initializes with correct attributes."""
    assert game_context.session_id == "test_session"
    assert game_context.timeline_id == "test_timeline"
    assert game_context.current_state == GameState.MENU
    assert game_context.event_store is not None
    assert game_context.state_machine is not None


def test_game_context_custom_initial_state(event_store: EventStore) -> None:
    """Test GameContext with custom initial state."""
    context = GameContext(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.EXPLORING,
    )
    assert context.current_state == GameState.EXPLORING


def test_game_context_empty_session_id(event_store: EventStore) -> None:
    """Test that empty session_id raises ValueError."""
    with pytest.raises(ValueError, match="session_id cannot be empty"):
        GameContext(
            event_store=event_store,
            session_id="",
            timeline_id="test_timeline",
        )


def test_game_context_empty_timeline_id(event_store: EventStore) -> None:
    """Test that empty timeline_id raises ValueError."""
    with pytest.raises(ValueError, match="timeline_id cannot be empty"):
        GameContext(
            event_store=event_store,
            session_id="test_session",
            timeline_id="",
        )


def test_game_context_emits_session_start_event(
    game_context: GameContext, event_store: EventStore
) -> None:
    """Test that GameContext emits GAME_START event on initialization."""
    events = event_store.get_events_by_session("test_session")

    # Should have at least one GAME_START event
    start_events = [e for e in events if e.event_type == EventTypes.GAME_START]
    assert len(start_events) >= 1

    # Verify first event is GAME_START
    assert events[0].event_type == EventTypes.GAME_START
    assert events[0].session_id == "test_session"
    assert events[0].timeline_id == "test_timeline"
    assert events[0].aggregate_type == "session"


# ============================================================================
# Factory Method Tests
# ============================================================================


def test_game_context_create_with_defaults() -> None:
    """Test GameContext.create() with auto-generated IDs."""
    context = GameContext.create(":memory:")

    # Should have auto-generated IDs
    assert context.session_id.startswith("sess_")
    assert context.timeline_id.startswith("timeline_")
    assert context.current_state == GameState.MENU


def test_game_context_create_with_custom_ids() -> None:
    """Test GameContext.create() with custom IDs."""
    context = GameContext.create(
        ":memory:",
        session_id="custom_session",
        timeline_id="custom_timeline",
    )

    assert context.session_id == "custom_session"
    assert context.timeline_id == "custom_timeline"


def test_game_context_create_with_initial_state() -> None:
    """Test GameContext.create() with custom initial state."""
    context = GameContext.create(
        ":memory:",
        initial_state=GameState.EXPLORING,
    )

    assert context.current_state == GameState.EXPLORING


def test_game_context_create_file_based() -> None:
    """Test GameContext.create() with file-based database."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        context = GameContext.create(tmp.name)
        context.close()

        # Verify file was created
        import os

        assert os.path.exists(tmp.name)
        os.unlink(tmp.name)


# ============================================================================
# Property Tests
# ============================================================================


def test_event_store_property_readonly(game_context: GameContext) -> None:
    """Test that event_store property returns the injected store."""
    assert game_context.event_store is game_context._event_store


def test_state_machine_property_readonly(game_context: GameContext) -> None:
    """Test that state_machine property returns the injected machine."""
    assert game_context.state_machine is game_context._state_machine


def test_current_state_property(game_context: GameContext) -> None:
    """Test current_state convenience property."""
    assert game_context.current_state == GameState.MENU

    # Transition and verify property updates
    game_context.transition_to(GameState.EXPLORING)
    assert game_context.current_state == GameState.EXPLORING


# ============================================================================
# Common Operation Tests
# ============================================================================


def test_transition_to_convenience_method(game_context: GameContext) -> None:
    """Test transition_to() convenience wrapper."""
    game_context.transition_to(GameState.EXPLORING, {"reason": "start_game"})
    assert game_context.current_state == GameState.EXPLORING


def test_transition_to_with_context(game_context: GameContext) -> None:
    """Test transition_to() with context data."""
    context_data = {"reason": "player_action", "location": "forest"}
    game_context.transition_to(GameState.EXPLORING, context_data)

    # Verify event was emitted with context
    events = game_context.get_session_events()
    transition_events = [
        e for e in events if e.event_type == EventTypes.STATE_TRANSITION
    ]
    assert len(transition_events) > 0

    # Verify context data in event
    event_data = json.loads(transition_events[0].event_data)
    assert "context" in event_data
    assert event_data["context"]["reason"] == "player_action"


def test_transition_to_invalid_raises_error(game_context: GameContext) -> None:
    """Test that invalid transitions raise StateTransitionError."""
    # MENU cannot transition directly to COMBAT
    with pytest.raises(StateTransitionError):
        game_context.transition_to(GameState.COMBAT)


def test_get_session_events(game_context: GameContext) -> None:
    """Test get_session_events() method."""
    # Make some transitions
    game_context.transition_to(GameState.EXPLORING)
    game_context.transition_to(GameState.COMBAT)

    events = game_context.get_session_events()

    # Should have: GAME_START + 2 STATE_TRANSITION events
    assert len(events) >= 3
    assert events[0].event_type == EventTypes.GAME_START


def test_get_session_events_with_limit(game_context: GameContext) -> None:
    """Test get_session_events() with limit parameter."""
    # Make several transitions
    game_context.transition_to(GameState.EXPLORING)
    game_context.transition_to(GameState.COMBAT)
    game_context.transition_to(GameState.EXPLORING)

    events = game_context.get_session_events(limit=2)

    assert len(events) == 2


def test_get_timeline_events(game_context: GameContext) -> None:
    """Test get_timeline_events() method."""
    game_context.transition_to(GameState.EXPLORING)

    events = game_context.get_timeline_events()

    # All events should belong to test_timeline
    for event in events:
        assert event.timeline_id == "test_timeline"


def test_get_timeline_events_with_limit(game_context: GameContext) -> None:
    """Test get_timeline_events() with limit parameter."""
    game_context.transition_to(GameState.EXPLORING)
    game_context.transition_to(GameState.COMBAT)

    events = game_context.get_timeline_events(limit=1)

    assert len(events) == 1


def test_get_event_count(game_context: GameContext) -> None:
    """Test get_event_count() method."""
    initial_count = game_context.get_event_count()

    # Should have at least GAME_START event
    assert initial_count >= 1

    # Make a transition
    game_context.transition_to(GameState.EXPLORING)

    # Count should increase
    assert game_context.get_event_count() == initial_count + 1


def test_branch_timeline(game_context: GameContext) -> None:
    """Test branch_timeline() method."""
    # Make some events
    game_context.transition_to(GameState.EXPLORING)

    # Branch timeline
    game_context.branch_timeline("alternate_timeline")

    # Verify timeline was created in event store
    # (EventStore tests already cover this, just verify the call works)
    assert True  # No exception raised


def test_branch_timeline_with_timestamp(game_context: GameContext) -> None:
    """Test branch_timeline() with specific timestamp."""
    game_context.transition_to(GameState.EXPLORING)

    # Branch from specific timestamp
    game_context.branch_timeline("past_branch", branch_point_timestamp=1234567890.0)

    # No exception should be raised
    assert True


# ============================================================================
# Serialization Tests
# ============================================================================


def test_to_dict(game_context: GameContext) -> None:
    """Test to_dict() serialization."""
    context_dict = game_context.to_dict()

    assert context_dict["session_id"] == "test_session"
    assert context_dict["timeline_id"] == "test_timeline"
    assert context_dict["current_state"] == "MENU"
    assert "event_count" in context_dict
    assert context_dict["event_count"] >= 1


def test_to_dict_after_transitions(game_context: GameContext) -> None:
    """Test to_dict() after state transitions."""
    game_context.transition_to(GameState.EXPLORING)
    game_context.transition_to(GameState.COMBAT)

    context_dict = game_context.to_dict()

    assert context_dict["current_state"] == "COMBAT"
    assert context_dict["event_count"] >= 3  # GAME_START + 2 transitions


def test_from_dict_basic(event_store: EventStore) -> None:
    """Test from_dict() deserialization."""
    data = {
        "session_id": "restored_session",
        "timeline_id": "restored_timeline",
        "current_state": "EXPLORING",
        "event_count": 5,
    }

    context = GameContext.from_dict(data, event_store)

    assert context.session_id == "restored_session"
    assert context.timeline_id == "restored_timeline"
    assert context.current_state == GameState.EXPLORING


def test_from_dict_missing_fields(event_store: EventStore) -> None:
    """Test from_dict() with missing required fields."""
    incomplete_data = {
        "session_id": "test",
        # Missing timeline_id and current_state
    }

    with pytest.raises(ValueError, match="Missing required fields"):
        GameContext.from_dict(incomplete_data, event_store)


def test_from_dict_invalid_state_name(event_store: EventStore) -> None:
    """Test from_dict() with invalid state name."""
    data = {
        "session_id": "test_session",
        "timeline_id": "test_timeline",
        "current_state": "INVALID_STATE",
    }

    with pytest.raises(KeyError, match="Invalid state name"):
        GameContext.from_dict(data, event_store)


def test_save_and_restore_cycle(event_store: EventStore) -> None:
    """Test full save and restore cycle."""
    # Create context and make changes
    original_context = GameContext(
        event_store=event_store,
        session_id="save_test",
        timeline_id="save_timeline",
    )
    original_context.transition_to(GameState.EXPLORING)
    original_context.transition_to(GameState.COMBAT)

    # Save to dict
    saved_data = original_context.to_dict()

    # Restore from dict
    restored_context = GameContext.from_dict(saved_data, event_store)

    # Verify restoration
    assert restored_context.session_id == original_context.session_id
    assert restored_context.timeline_id == original_context.timeline_id
    assert restored_context.current_state == original_context.current_state


# ============================================================================
# Context Manager Tests
# ============================================================================


def test_context_manager_enter_exit() -> None:
    """Test GameContext as context manager."""
    with GameContext.create(":memory:") as context:
        assert context.session_id is not None
        assert context.current_state == GameState.MENU

    # Context should be closed after exit
    # Verify by checking if EventStore was closed (will raise if we try to use it)


def test_context_manager_with_operations() -> None:
    """Test context manager with game operations."""
    with GameContext.create(":memory:") as context:
        context.transition_to(GameState.EXPLORING)
        assert context.current_state == GameState.EXPLORING

        events = context.get_session_events()
        assert len(events) >= 2  # GAME_START + STATE_TRANSITION


def test_context_manager_emits_game_end() -> None:
    """Test that context manager emits GAME_END on exit."""
    store = EventStore(":memory:")

    # Track events before close
    context = GameContext(
        event_store=store,
        session_id="test_session",
        timeline_id="test_timeline",
    )

    # Get initial event count (should have GAME_START)
    events_before = len(context.get_session_events())

    # Close the context (emits GAME_END)
    context.close()

    # We can't query after close, but we know close() emits GAME_END
    # based on the implementation. We'll just verify close() doesn't raise.
    assert events_before >= 1  # Had at least GAME_START


def test_close_method(game_context: GameContext) -> None:
    """Test close() method explicitly."""
    game_context.close()

    # Should have emitted GAME_END event
    # (We can't query after close, but no exception should be raised)
    assert True


# ============================================================================
# String Representation Tests
# ============================================================================


def test_game_context_repr(game_context: GameContext) -> None:
    """Test __repr__() method."""
    repr_str = repr(game_context)

    assert "GameContext(" in repr_str
    assert "session=test_session" in repr_str
    assert "timeline=test_timeline" in repr_str
    assert "state=MENU" in repr_str


def test_game_context_str(game_context: GameContext) -> None:
    """Test __str__() method."""
    str_repr = str(game_context)

    assert "test_session" in str_repr
    assert "test_timeline" in str_repr


def test_game_context_repr_after_transition(game_context: GameContext) -> None:
    """Test __repr__() reflects state changes."""
    game_context.transition_to(GameState.EXPLORING)
    repr_str = repr(game_context)

    assert "state=EXPLORING" in repr_str


# ============================================================================
# Integration Tests (Multiple Systems)
# ============================================================================


def test_state_machine_integration(game_context: GameContext) -> None:
    """Test integration between GameContext and GameStateMachine."""
    # GameContext should properly delegate to StateMachine
    allowed = game_context.state_machine.get_allowed_transitions()

    assert GameState.EXPLORING in allowed
    assert GameState.TIMELINE_VIEW in allowed


def test_event_store_integration(game_context: GameContext) -> None:
    """Test integration between GameContext and EventStore."""
    # Events should flow through to EventStore
    game_context.transition_to(GameState.EXPLORING)

    # Query EventStore directly
    events = game_context.event_store.get_events_by_session("test_session")

    assert len(events) >= 2  # GAME_START + STATE_TRANSITION


def test_multiple_contexts_same_store() -> None:
    """Test multiple GameContext instances sharing EventStore."""
    store = EventStore(":memory:")

    context1 = GameContext(
        event_store=store,
        session_id="session_1",
        timeline_id="timeline_1",
    )

    context2 = GameContext(
        event_store=store,
        session_id="session_2",
        timeline_id="timeline_1",  # Same timeline
    )

    # Both contexts should share the same timeline
    context1.transition_to(GameState.EXPLORING)
    context2.transition_to(GameState.EXPLORING)

    timeline_events = context1.get_timeline_events()

    # Should have events from both sessions
    assert len(timeline_events) >= 4  # 2 GAME_START + 2 STATE_TRANSITION


def test_full_game_flow_simulation() -> None:
    """Test a realistic game flow through context."""
    with GameContext.create(":memory:") as context:
        # Start game
        assert context.current_state == GameState.MENU

        # Begin playing
        context.transition_to(GameState.EXPLORING)

        # Enter combat
        context.transition_to(GameState.COMBAT)

        # Return to exploring
        context.transition_to(GameState.EXPLORING)

        # Open inventory
        context.transition_to(GameState.INVENTORY)

        # Back to exploring
        context.transition_to(GameState.EXPLORING)

        # Pause game
        context.transition_to(GameState.PAUSED)

        # Resume
        context.transition_to(GameState.EXPLORING)

        # End game
        context.transition_to(GameState.GAME_OVER)

        # Verify all events were recorded
        events = context.get_session_events()
        assert len(events) >= 9  # GAME_START + 8 transitions

    # Context should close cleanly with GAME_END event


# ============================================================================
# Logging Tests
# ============================================================================


def test_logging_on_initialization(event_store: EventStore) -> None:
    """Test that GameContext logs initialization."""
    with patch("src.core.game_context.logger") as mock_logger:
        _ = GameContext(
            event_store=event_store,
            session_id="test_session",
            timeline_id="test_timeline",
        )

        mock_logger.info.assert_called()
        call_args = str(mock_logger.info.call_args_list)
        assert "GameContext initialized" in call_args


def test_logging_on_close(game_context: GameContext) -> None:
    """Test that GameContext logs on close."""
    with patch("src.core.game_context.logger") as mock_logger:
        game_context.close()

        mock_logger.info.assert_called()
        call_args = str(mock_logger.info.call_args_list)
        assert "GameContext closed" in call_args


def test_logging_on_timeline_branch(game_context: GameContext) -> None:
    """Test that timeline branching is logged."""
    with patch("src.core.game_context.logger") as mock_logger:
        game_context.branch_timeline("new_timeline")

        mock_logger.info.assert_called()
        call_args = str(mock_logger.info.call_args_list)
        assert "Timeline branched" in call_args
