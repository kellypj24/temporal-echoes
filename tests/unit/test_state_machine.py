"""Unit tests for GameStateMachine and GameState.

Test Coverage:
- GameState enum functionality
- GameStateMachine initialization
- Valid state transitions with event emission
- Invalid state transitions with error handling
- Helper methods (get_allowed_transitions, can_transition_to)
- Edge cases and error conditions

Constitution Principles Tested:
- #1: Event sourcing (verify events emitted on transitions)
- #2: Dependency injection (EventStore injected)
- #3: Type safety (verify type validation)
- #5: Error handling (specific exceptions)
- #11: Immutability (events emitted before state change)
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.core.events import EventTypes, GameEvent
from src.core.exceptions import StateTransitionError
from src.core.persistence import EventStore
from src.core.state_machine import GameState, GameStateMachine


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def event_store() -> EventStore:
    """Create an in-memory EventStore for testing."""
    return EventStore(":memory:")


@pytest.fixture
def state_machine(event_store: EventStore) -> GameStateMachine:
    """Create a GameStateMachine for testing."""
    return GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
    )


# ============================================================================
# GameState Enum Tests
# ============================================================================


def test_game_state_enum_values() -> None:
    """Test that GameState enum has all expected states."""
    expected_states = {
        "MENU",
        "EXPLORING",
        "COMBAT",
        "DIALOGUE",
        "INVENTORY",
        "TIMELINE_VIEW",
        "PAUSED",
        "GAME_OVER",
    }
    actual_states = {state.name for state in GameState}
    assert actual_states == expected_states


def test_game_state_str_representation() -> None:
    """Test that GameState.__str__ returns the state name."""
    assert str(GameState.MENU) == "MENU"
    assert str(GameState.EXPLORING) == "EXPLORING"
    assert str(GameState.COMBAT) == "COMBAT"


def test_game_state_enum_comparison() -> None:
    """Test that GameState enum values can be compared."""
    state1 = GameState.MENU
    state2 = GameState.MENU
    state3 = GameState.EXPLORING

    assert state1 == state2
    assert state1 != state3
    assert state1 is state2  # Enums are singletons


# ============================================================================
# GameStateMachine Initialization Tests
# ============================================================================


def test_state_machine_initialization(state_machine: GameStateMachine) -> None:
    """Test that GameStateMachine initializes with correct default state."""
    assert state_machine.current_state == GameState.MENU
    assert state_machine.session_id == "test_session"
    assert state_machine.timeline_id == "test_timeline"


def test_state_machine_custom_initial_state(event_store: EventStore) -> None:
    """Test that GameStateMachine can be initialized with a custom state."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.EXPLORING,
    )
    assert machine.current_state == GameState.EXPLORING


def test_state_machine_empty_session_id(event_store: EventStore) -> None:
    """Test that GameStateMachine raises ValueError for empty session_id."""
    with pytest.raises(ValueError, match="session_id cannot be empty"):
        GameStateMachine(
            event_store=event_store,
            session_id="",
            timeline_id="test_timeline",
        )


def test_state_machine_empty_timeline_id(event_store: EventStore) -> None:
    """Test that GameStateMachine raises ValueError for empty timeline_id."""
    with pytest.raises(ValueError, match="timeline_id cannot be empty"):
        GameStateMachine(
            event_store=event_store,
            session_id="test_session",
            timeline_id="",
        )


def test_state_machine_logging_on_init(event_store: EventStore) -> None:
    """Test that GameStateMachine logs initialization."""
    with patch("src.core.state_machine.logger") as mock_logger:
        machine = GameStateMachine(
            event_store=event_store,
            session_id="test_session",
            timeline_id="test_timeline",
        )
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "GameStateMachine initialized" in call_args
        assert "test_session" in call_args
        assert "test_timeline" in call_args


# ============================================================================
# Valid Transition Tests
# ============================================================================


def test_transition_menu_to_exploring(state_machine: GameStateMachine) -> None:
    """Test transition from MENU to EXPLORING."""
    assert state_machine.current_state == GameState.MENU
    state_machine.transition(GameState.EXPLORING, {"reason": "start_game"})
    assert state_machine.current_state == GameState.EXPLORING


def test_transition_emits_event(
    state_machine: GameStateMachine, event_store: EventStore
) -> None:
    """Test that transitions emit events to the event store."""
    initial_count = event_store.get_event_count()

    state_machine.transition(GameState.EXPLORING, {"reason": "start_game"})

    # Verify event was emitted
    assert event_store.get_event_count() == initial_count + 1

    # Verify event details
    events = event_store.get_events_by_session("test_session")
    latest_event = events[-1]
    assert latest_event.event_type == EventTypes.STATE_TRANSITION
    assert latest_event.session_id == "test_session"
    assert latest_event.timeline_id == "test_timeline"
    assert latest_event.aggregate_type == "game_state"

    # Verify event data
    event_data = json.loads(latest_event.event_data)
    assert event_data["from"] == "MENU"
    assert event_data["to"] == "EXPLORING"


def test_transition_exploring_to_combat(event_store: EventStore) -> None:
    """Test transition from EXPLORING to COMBAT."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.EXPLORING,
    )

    machine.transition(GameState.COMBAT, {"enemy": "Goblin"})
    assert machine.current_state == GameState.COMBAT


def test_transition_exploring_to_dialogue(event_store: EventStore) -> None:
    """Test transition from EXPLORING to DIALOGUE."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.EXPLORING,
    )

    machine.transition(GameState.DIALOGUE, {"npc": "Village Elder"})
    assert machine.current_state == GameState.DIALOGUE


def test_transition_exploring_to_inventory(event_store: EventStore) -> None:
    """Test transition from EXPLORING to INVENTORY."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.EXPLORING,
    )

    machine.transition(GameState.INVENTORY)
    assert machine.current_state == GameState.INVENTORY


def test_transition_combat_to_exploring(event_store: EventStore) -> None:
    """Test transition from COMBAT to EXPLORING (victory)."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.COMBAT,
    )

    machine.transition(GameState.EXPLORING, {"result": "victory"})
    assert machine.current_state == GameState.EXPLORING


def test_transition_paused_to_exploring(event_store: EventStore) -> None:
    """Test transition from PAUSED to EXPLORING (resume)."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.PAUSED,
    )

    machine.transition(GameState.EXPLORING, {"action": "resume"})
    assert machine.current_state == GameState.EXPLORING


def test_transition_game_over_to_menu(event_store: EventStore) -> None:
    """Test transition from GAME_OVER to MENU (restart)."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.GAME_OVER,
    )

    machine.transition(GameState.MENU, {"action": "restart"})
    assert machine.current_state == GameState.MENU


def test_multiple_transitions(state_machine: GameStateMachine) -> None:
    """Test a sequence of valid transitions."""
    # MENU -> EXPLORING -> COMBAT -> EXPLORING -> PAUSED -> MENU
    state_machine.transition(GameState.EXPLORING)
    assert state_machine.current_state == GameState.EXPLORING

    state_machine.transition(GameState.COMBAT)
    assert state_machine.current_state == GameState.COMBAT

    state_machine.transition(GameState.EXPLORING)
    assert state_machine.current_state == GameState.EXPLORING

    state_machine.transition(GameState.PAUSED)
    assert state_machine.current_state == GameState.PAUSED

    state_machine.transition(GameState.MENU)
    assert state_machine.current_state == GameState.MENU


def test_transition_logs_info(state_machine: GameStateMachine) -> None:
    """Test that successful transitions log info messages."""
    with patch("src.core.state_machine.logger") as mock_logger:
        state_machine.transition(GameState.EXPLORING)

        # Should have called logger.info for the transition
        assert mock_logger.info.call_count >= 1
        call_args = str(mock_logger.info.call_args_list)
        assert "MENU" in call_args
        assert "EXPLORING" in call_args


# ============================================================================
# Invalid Transition Tests
# ============================================================================


def test_invalid_transition_raises_error(state_machine: GameStateMachine) -> None:
    """Test that invalid transitions raise StateTransitionError."""
    # MENU cannot transition directly to COMBAT
    with pytest.raises(StateTransitionError) as exc_info:
        state_machine.transition(GameState.COMBAT)

    assert exc_info.value.from_state == "MENU"
    assert exc_info.value.to_state == "COMBAT"
    assert "Invalid transition: MENU -> COMBAT" in str(exc_info.value)


def test_invalid_transition_state_unchanged(state_machine: GameStateMachine) -> None:
    """Test that state remains unchanged after invalid transition."""
    assert state_machine.current_state == GameState.MENU

    with pytest.raises(StateTransitionError):
        state_machine.transition(GameState.COMBAT)

    # State should still be MENU
    assert state_machine.current_state == GameState.MENU


def test_invalid_transition_no_event_emitted(
    state_machine: GameStateMachine, event_store: EventStore
) -> None:
    """Test that invalid transitions do not emit events."""
    initial_count = event_store.get_event_count()

    with pytest.raises(StateTransitionError):
        state_machine.transition(GameState.COMBAT)

    # Event count should be unchanged
    assert event_store.get_event_count() == initial_count


def test_transition_inventory_to_combat_invalid(event_store: EventStore) -> None:
    """Test that INVENTORY cannot transition to COMBAT directly."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.INVENTORY,
    )

    with pytest.raises(StateTransitionError) as exc_info:
        machine.transition(GameState.COMBAT)

    assert exc_info.value.from_state == "INVENTORY"
    assert exc_info.value.to_state == "COMBAT"


def test_transition_game_over_to_exploring_invalid(event_store: EventStore) -> None:
    """Test that GAME_OVER cannot transition to EXPLORING directly."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.GAME_OVER,
    )

    with pytest.raises(StateTransitionError) as exc_info:
        machine.transition(GameState.EXPLORING)

    assert exc_info.value.from_state == "GAME_OVER"
    assert exc_info.value.to_state == "EXPLORING"


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_transition_to_same_state_noop(state_machine: GameStateMachine) -> None:
    """Test that transitioning to the same state is a no-op."""
    assert state_machine.current_state == GameState.MENU

    # Transition to MENU (already in MENU)
    with patch("src.core.state_machine.logger") as mock_logger:
        state_machine.transition(GameState.MENU)

        # Should log debug message
        mock_logger.debug.assert_called_once()
        assert "Already in state" in str(mock_logger.debug.call_args)

    # State should still be MENU
    assert state_machine.current_state == GameState.MENU


def test_transition_to_same_state_no_event(
    state_machine: GameStateMachine, event_store: EventStore
) -> None:
    """Test that no event is emitted for same-state transitions."""
    initial_count = event_store.get_event_count()

    state_machine.transition(GameState.MENU)

    # No event should be emitted
    assert event_store.get_event_count() == initial_count


def test_transition_invalid_type() -> None:
    """Test that transition with non-GameState type raises ValueError."""
    store = EventStore(":memory:")
    machine = GameStateMachine(
        event_store=store,
        session_id="test_session",
        timeline_id="test_timeline",
    )

    with pytest.raises(ValueError, match="to_state must be GameState enum"):
        machine.transition("EXPLORING")  # type: ignore


def test_transition_with_none_context(state_machine: GameStateMachine) -> None:
    """Test that transitions work with None context (default)."""
    state_machine.transition(GameState.EXPLORING, context=None)
    assert state_machine.current_state == GameState.EXPLORING


def test_transition_with_empty_context(state_machine: GameStateMachine) -> None:
    """Test that transitions work with empty context dict."""
    state_machine.transition(GameState.EXPLORING, context={})
    assert state_machine.current_state == GameState.EXPLORING


def test_transition_with_complex_context(
    state_machine: GameStateMachine, event_store: EventStore
) -> None:
    """Test that transitions handle complex context data."""
    complex_context = {
        "reason": "player_action",
        "player_level": 5,
        "location": {"x": 100, "y": 200},
        "items": ["sword", "shield"],
    }

    state_machine.transition(GameState.EXPLORING, context=complex_context)

    # Verify context is preserved in event
    events = event_store.get_events_by_session("test_session")
    latest_event = events[-1]
    event_data = json.loads(latest_event.event_data)

    # Context should be in the event_data
    assert "context" in event_data


# ============================================================================
# Helper Method Tests
# ============================================================================


def test_get_allowed_transitions_from_menu(state_machine: GameStateMachine) -> None:
    """Test get_allowed_transitions from MENU state."""
    allowed = state_machine.get_allowed_transitions()

    expected = {
        GameState.EXPLORING,
        GameState.TIMELINE_VIEW,
        GameState.GAME_OVER,
    }
    assert allowed == expected


def test_get_allowed_transitions_from_exploring(event_store: EventStore) -> None:
    """Test get_allowed_transitions from EXPLORING state."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="test_timeline",
        initial_state=GameState.EXPLORING,
    )

    allowed = machine.get_allowed_transitions()

    expected = {
        GameState.COMBAT,
        GameState.DIALOGUE,
        GameState.INVENTORY,
        GameState.TIMELINE_VIEW,
        GameState.PAUSED,
        GameState.MENU,
        GameState.GAME_OVER,
    }
    assert allowed == expected


def test_get_allowed_transitions_returns_copy(state_machine: GameStateMachine) -> None:
    """Test that get_allowed_transitions returns a copy, not a reference."""
    allowed1 = state_machine.get_allowed_transitions()
    allowed2 = state_machine.get_allowed_transitions()

    # Should be equal but not the same object
    assert allowed1 == allowed2
    assert allowed1 is not allowed2

    # Modifying one should not affect the other
    allowed1.add(GameState.COMBAT)  # Invalid, but testing isolation
    assert allowed2 != allowed1


def test_can_transition_to_valid(state_machine: GameStateMachine) -> None:
    """Test can_transition_to for valid transitions."""
    assert state_machine.can_transition_to(GameState.EXPLORING) is True
    assert state_machine.can_transition_to(GameState.TIMELINE_VIEW) is True
    assert state_machine.can_transition_to(GameState.GAME_OVER) is True


def test_can_transition_to_invalid(state_machine: GameStateMachine) -> None:
    """Test can_transition_to for invalid transitions."""
    assert state_machine.can_transition_to(GameState.COMBAT) is False
    assert state_machine.can_transition_to(GameState.DIALOGUE) is False
    assert state_machine.can_transition_to(GameState.INVENTORY) is False
    assert state_machine.can_transition_to(GameState.PAUSED) is False


def test_can_transition_to_no_exception(state_machine: GameStateMachine) -> None:
    """Test that can_transition_to does not raise exceptions."""
    # Should return False without raising
    result = state_machine.can_transition_to(GameState.COMBAT)
    assert result is False


# ============================================================================
# String Representation Tests
# ============================================================================


def test_state_machine_repr(state_machine: GameStateMachine) -> None:
    """Test __repr__ returns developer-friendly representation."""
    repr_str = repr(state_machine)

    assert "GameStateMachine(" in repr_str
    assert "state=MENU" in repr_str
    assert "session=test_session" in repr_str
    assert "timeline=test_timeline" in repr_str


def test_state_machine_str(state_machine: GameStateMachine) -> None:
    """Test __str__ returns user-friendly representation."""
    str_repr = str(state_machine)

    assert "State: MENU" in str_repr


def test_state_machine_str_after_transition(state_machine: GameStateMachine) -> None:
    """Test __str__ reflects current state after transition."""
    state_machine.transition(GameState.EXPLORING)
    str_repr = str(state_machine)

    assert "State: EXPLORING" in str_repr


# ============================================================================
# Transition Graph Completeness Tests
# ============================================================================


def test_all_states_have_transitions() -> None:
    """Test that all states (except GAME_OVER edge case) have defined transitions."""
    all_states = set(GameState)
    defined_states = set(GameStateMachine.ALLOWED_TRANSITIONS.keys())

    # All states should have transitions defined
    assert all_states == defined_states


def test_all_transitions_are_valid_states() -> None:
    """Test that all transitions point to valid GameState values."""
    all_states = set(GameState)

    for _from_state, to_states in GameStateMachine.ALLOWED_TRANSITIONS.items():
        for to_state in to_states:
            assert to_state in all_states


def test_menu_is_reachable_from_all_states() -> None:
    """Test that MENU is reachable from most states (game design principle)."""
    # States that should be able to reach MENU
    states_with_menu_access = [
        GameState.EXPLORING,
        GameState.PAUSED,
        GameState.GAME_OVER,
        GameState.TIMELINE_VIEW,
    ]

    for state in states_with_menu_access:
        transitions = GameStateMachine.ALLOWED_TRANSITIONS[state]
        assert (
            GameState.MENU in transitions
        ), f"{state.name} should allow transition to MENU"


def test_game_over_is_reachable() -> None:
    """Test that GAME_OVER is reachable from gameplay states."""
    # States that should be able to reach GAME_OVER
    states_with_game_over = [
        GameState.MENU,
        GameState.EXPLORING,
        GameState.COMBAT,
    ]

    for state in states_with_game_over:
        transitions = GameStateMachine.ALLOWED_TRANSITIONS[state]
        assert (
            GameState.GAME_OVER in transitions
        ), f"{state.name} should allow transition to GAME_OVER"


def test_exploring_is_central_hub() -> None:
    """Test that EXPLORING state has the most transitions (hub state)."""
    exploring_transitions = len(
        GameStateMachine.ALLOWED_TRANSITIONS[GameState.EXPLORING]
    )

    for state, transitions in GameStateMachine.ALLOWED_TRANSITIONS.items():
        if state != GameState.EXPLORING:
            assert (
                len(transitions) <= exploring_transitions
            ), f"EXPLORING should be the hub state with most transitions"


# ============================================================================
# Event Sourcing Integration Tests
# ============================================================================


def test_event_emission_before_state_change(
    state_machine: GameStateMachine, event_store: EventStore
) -> None:
    """Test that events are emitted BEFORE state changes (Constitution #11)."""
    # This is a critical test for event sourcing correctness
    # If we query the event store during transition, the event should exist
    # before the state is updated

    # We'll use a mock to intercept the append_event call
    original_append = event_store.append_event

    state_captured_at_event = None

    def capture_state_at_event(event: GameEvent) -> None:
        nonlocal state_captured_at_event
        state_captured_at_event = state_machine.current_state
        original_append(event)

    event_store.append_event = capture_state_at_event  # type: ignore

    # Perform transition
    state_machine.transition(GameState.EXPLORING)

    # The state at the time of event emission should be MENU (old state)
    assert state_captured_at_event == GameState.MENU

    # But now the state should be EXPLORING (new state)
    assert state_machine.current_state == GameState.EXPLORING


def test_multiple_transitions_emit_separate_events(
    state_machine: GameStateMachine, event_store: EventStore
) -> None:
    """Test that each transition emits a separate event."""
    initial_count = event_store.get_event_count()

    # Perform 3 transitions
    state_machine.transition(GameState.EXPLORING)
    state_machine.transition(GameState.COMBAT)
    state_machine.transition(GameState.EXPLORING)

    # Should have 3 new events
    assert event_store.get_event_count() == initial_count + 3


def test_event_aggregate_id_format(
    state_machine: GameStateMachine, event_store: EventStore
) -> None:
    """Test that state transition events have correct aggregate_id format."""
    state_machine.transition(GameState.EXPLORING)

    events = event_store.get_events_by_session("test_session")
    latest_event = events[-1]

    assert latest_event.aggregate_id == "game_test_session"
    assert latest_event.aggregate_type == "game_state"


def test_event_timeline_tracking(event_store: EventStore) -> None:
    """Test that events track timeline_id for timeline branching support."""
    machine = GameStateMachine(
        event_store=event_store,
        session_id="test_session",
        timeline_id="timeline_alpha",
    )

    machine.transition(GameState.EXPLORING)

    events = event_store.get_events_by_timeline("timeline_alpha")
    assert len(events) == 1
    assert events[0].timeline_id == "timeline_alpha"
