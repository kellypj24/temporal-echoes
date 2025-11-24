"""Unit tests for GameStateMachine and GameState."""

import pytest

from src.core.events import EventTypes
from src.core.exceptions import StateTransitionError
from src.core.persistence import EventStore
from src.core.state_machine import GameState, GameStateMachine


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def in_memory_store() -> EventStore:
    """Provide an in-memory EventStore for testing."""
    return EventStore(":memory:")


@pytest.fixture
def state_machine(in_memory_store: EventStore) -> GameStateMachine:
    """Provide a GameStateMachine initialized at MENU state."""
    return GameStateMachine(
        event_store=in_memory_store,
        session_id="test_session_001",
        timeline_id="test_timeline_main",
    )


# ============================================================================
# Test: GameState Enum
# ============================================================================


def test_game_state_enum_values() -> None:
    """Test that all GameState enum values are defined correctly."""
    assert GameState.MENU.value == 1
    assert GameState.EXPLORING.value == 2
    assert GameState.COMBAT.value == 3
    assert GameState.DIALOGUE.value == 4
    assert GameState.INVENTORY.value == 5
    assert GameState.TIMELINE_VIEW.value == 6
    assert GameState.PAUSED.value == 7
    assert GameState.GAME_OVER.value == 8


def test_game_state_enum_names() -> None:
    """Test that GameState enum names match expected values."""
    assert GameState.MENU.name == "MENU"
    assert GameState.EXPLORING.name == "EXPLORING"
    assert GameState.COMBAT.name == "COMBAT"
    assert GameState.DIALOGUE.name == "DIALOGUE"
    assert GameState.INVENTORY.name == "INVENTORY"
    assert GameState.TIMELINE_VIEW.name == "TIMELINE_VIEW"
    assert GameState.PAUSED.name == "PAUSED"
    assert GameState.GAME_OVER.name == "GAME_OVER"


def test_game_state_str_representation() -> None:
    """Test that GameState __str__ returns the state name."""
    assert str(GameState.MENU) == "MENU"
    assert str(GameState.EXPLORING) == "EXPLORING"
    assert str(GameState.COMBAT) == "COMBAT"


def test_game_state_count() -> None:
    """Test that we have exactly 8 game states."""
    assert len(GameState) == 8


# ============================================================================
# Test: Initialization
# ============================================================================


def test_state_machine_initialization_default(in_memory_store: EventStore) -> None:
    """Test GameStateMachine initializes with default MENU state."""
    machine = GameStateMachine(
        event_store=in_memory_store,
        session_id="session_001",
        timeline_id="timeline_main",
    )

    assert machine.current_state == GameState.MENU
    assert machine.session_id == "session_001"
    assert machine.timeline_id == "timeline_main"


def test_state_machine_initialization_custom_state(
    in_memory_store: EventStore,
) -> None:
    """Test GameStateMachine initializes with custom initial state."""
    machine = GameStateMachine(
        event_store=in_memory_store,
        session_id="session_002",
        timeline_id="timeline_alt",
        initial_state=GameState.EXPLORING,
    )

    assert machine.current_state == GameState.EXPLORING
    assert machine.session_id == "session_002"
    assert machine.timeline_id == "timeline_alt"


def test_state_machine_initialization_empty_session_id(
    in_memory_store: EventStore,
) -> None:
    """Test that empty session_id raises ValueError."""
    with pytest.raises(ValueError, match="session_id cannot be empty"):
        GameStateMachine(
            event_store=in_memory_store,
            session_id="",
            timeline_id="timeline_main",
        )


def test_state_machine_initialization_empty_timeline_id(
    in_memory_store: EventStore,
) -> None:
    """Test that empty timeline_id raises ValueError."""
    with pytest.raises(ValueError, match="timeline_id cannot be empty"):
        GameStateMachine(
            event_store=in_memory_store,
            session_id="session_001",
            timeline_id="",
        )


def test_state_machine_current_state_is_readonly(state_machine: GameStateMachine) -> None:
    """Test that current_state is a read-only property."""
    # Should not be able to set current_state directly
    with pytest.raises(AttributeError):
        state_machine.current_state = GameState.EXPLORING  # type: ignore


# ============================================================================
# Test: Valid Transitions (from MENU)
# ============================================================================


def test_transition_menu_to_exploring(state_machine: GameStateMachine) -> None:
    """Test valid transition: MENU -> EXPLORING."""
    assert state_machine.current_state == GameState.MENU

    state_machine.transition(GameState.EXPLORING, {"reason": "start_game"})

    assert state_machine.current_state == GameState.EXPLORING


def test_transition_menu_to_timeline_view(state_machine: GameStateMachine) -> None:
    """Test valid transition: MENU -> TIMELINE_VIEW."""
    assert state_machine.current_state == GameState.MENU

    state_machine.transition(GameState.TIMELINE_VIEW, {"reason": "view_timeline"})

    assert state_machine.current_state == GameState.TIMELINE_VIEW


def test_transition_menu_to_game_over(state_machine: GameStateMachine) -> None:
    """Test valid transition: MENU -> GAME_OVER."""
    assert state_machine.current_state == GameState.MENU

    state_machine.transition(GameState.GAME_OVER, {"reason": "quit"})

    assert state_machine.current_state == GameState.GAME_OVER


# ============================================================================
# Test: Valid Transitions (from EXPLORING)
# ============================================================================


def test_transition_exploring_to_combat(state_machine: GameStateMachine) -> None:
    """Test valid transition: EXPLORING -> COMBAT."""
    state_machine.transition(GameState.EXPLORING)
    assert state_machine.current_state == GameState.EXPLORING

    state_machine.transition(GameState.COMBAT, {"enemy": "Goblin"})

    assert state_machine.current_state == GameState.COMBAT


def test_transition_exploring_to_dialogue(state_machine: GameStateMachine) -> None:
    """Test valid transition: EXPLORING -> DIALOGUE."""
    state_machine.transition(GameState.EXPLORING)

    state_machine.transition(GameState.DIALOGUE, {"npc": "Elder"})

    assert state_machine.current_state == GameState.DIALOGUE


def test_transition_exploring_to_inventory(state_machine: GameStateMachine) -> None:
    """Test valid transition: EXPLORING -> INVENTORY."""
    state_machine.transition(GameState.EXPLORING)

    state_machine.transition(GameState.INVENTORY)

    assert state_machine.current_state == GameState.INVENTORY


def test_transition_exploring_to_paused(state_machine: GameStateMachine) -> None:
    """Test valid transition: EXPLORING -> PAUSED."""
    state_machine.transition(GameState.EXPLORING)

    state_machine.transition(GameState.PAUSED)

    assert state_machine.current_state == GameState.PAUSED


def test_transition_exploring_to_menu(state_machine: GameStateMachine) -> None:
    """Test valid transition: EXPLORING -> MENU."""
    state_machine.transition(GameState.EXPLORING)

    state_machine.transition(GameState.MENU, {"reason": "return_to_menu"})

    assert state_machine.current_state == GameState.MENU


# ============================================================================
# Test: Valid Transitions (from COMBAT)
# ============================================================================


def test_transition_combat_to_exploring(state_machine: GameStateMachine) -> None:
    """Test valid transition: COMBAT -> EXPLORING."""
    state_machine.transition(GameState.EXPLORING)
    state_machine.transition(GameState.COMBAT)

    state_machine.transition(GameState.EXPLORING, {"result": "victory"})

    assert state_machine.current_state == GameState.EXPLORING


def test_transition_combat_to_inventory(state_machine: GameStateMachine) -> None:
    """Test valid transition: COMBAT -> INVENTORY."""
    state_machine.transition(GameState.EXPLORING)
    state_machine.transition(GameState.COMBAT)

    state_machine.transition(GameState.INVENTORY, {"action": "use_potion"})

    assert state_machine.current_state == GameState.INVENTORY


def test_transition_combat_to_game_over(state_machine: GameStateMachine) -> None:
    """Test valid transition: COMBAT -> GAME_OVER."""
    state_machine.transition(GameState.EXPLORING)
    state_machine.transition(GameState.COMBAT)

    state_machine.transition(GameState.GAME_OVER, {"result": "defeat"})

    assert state_machine.current_state == GameState.GAME_OVER


# ============================================================================
# Test: Valid Transitions (from DIALOGUE)
# ============================================================================


def test_transition_dialogue_to_exploring(state_machine: GameStateMachine) -> None:
    """Test valid transition: DIALOGUE -> EXPLORING."""
    state_machine.transition(GameState.EXPLORING)
    state_machine.transition(GameState.DIALOGUE)

    state_machine.transition(GameState.EXPLORING, {"action": "end_conversation"})

    assert state_machine.current_state == GameState.EXPLORING


def test_transition_dialogue_to_combat(state_machine: GameStateMachine) -> None:
    """Test valid transition: DIALOGUE -> COMBAT."""
    state_machine.transition(GameState.EXPLORING)
    state_machine.transition(GameState.DIALOGUE)

    state_machine.transition(GameState.COMBAT, {"trigger": "hostile_npc"})

    assert state_machine.current_state == GameState.COMBAT


# ============================================================================
# Test: Invalid Transitions
# ============================================================================


def test_invalid_transition_menu_to_combat(state_machine: GameStateMachine) -> None:
    """Test invalid transition: MENU -> COMBAT (not allowed)."""
    assert state_machine.current_state == GameState.MENU

    with pytest.raises(StateTransitionError) as exc_info:
        state_machine.transition(GameState.COMBAT)

    assert "Invalid transition: MENU -> COMBAT" in str(exc_info.value)
    assert exc_info.value.from_state == "MENU"
    assert exc_info.value.to_state == "COMBAT"

    # State should remain unchanged after failed transition
    assert state_machine.current_state == GameState.MENU


def test_invalid_transition_combat_to_dialogue(state_machine: GameStateMachine) -> None:
    """Test invalid transition: COMBAT -> DIALOGUE (not allowed)."""
    state_machine.transition(GameState.EXPLORING)
    state_machine.transition(GameState.COMBAT)

    with pytest.raises(StateTransitionError) as exc_info:
        state_machine.transition(GameState.DIALOGUE)

    assert "Invalid transition: COMBAT -> DIALOGUE" in str(exc_info.value)
    assert state_machine.current_state == GameState.COMBAT


def test_invalid_transition_timeline_view_to_combat(
    state_machine: GameStateMachine,
) -> None:
    """Test invalid transition: TIMELINE_VIEW -> COMBAT (not allowed)."""
    state_machine.transition(GameState.EXPLORING)
    state_machine.transition(GameState.TIMELINE_VIEW)

    with pytest.raises(StateTransitionError) as exc_info:
        state_machine.transition(GameState.COMBAT)

    assert "Invalid transition: TIMELINE_VIEW -> COMBAT" in str(exc_info.value)
    assert state_machine.current_state == GameState.TIMELINE_VIEW


def test_invalid_transition_game_over_to_exploring(
    state_machine: GameStateMachine,
) -> None:
    """Test invalid transition: GAME_OVER -> EXPLORING (not allowed)."""
    state_machine.transition(GameState.EXPLORING)
    state_machine.transition(GameState.GAME_OVER)

    with pytest.raises(StateTransitionError):
        state_machine.transition(GameState.EXPLORING)

    assert state_machine.current_state == GameState.GAME_OVER


# ============================================================================
# Test: Event Emission
# ============================================================================


def test_transition_emits_event(
    state_machine: GameStateMachine, in_memory_store: EventStore
) -> None:
    """Test that transitions emit STATE_TRANSITION events."""
    initial_count = in_memory_store.get_event_count()

    state_machine.transition(GameState.EXPLORING, {"reason": "start_game"})

    # Should have emitted exactly one event
    assert in_memory_store.get_event_count() == initial_count + 1

    # Verify event details
    events = in_memory_store.get_events_by_session("test_session_001")
    last_event = events[-1]

    assert last_event.event_type == EventTypes.STATE_TRANSITION
    assert last_event.session_id == "test_session_001"
    assert last_event.timeline_id == "test_timeline_main"
    assert last_event.aggregate_type == "game_state"
    assert "MENU" in last_event.event_data
    assert "EXPLORING" in last_event.event_data


def test_failed_transition_does_not_emit_event(
    state_machine: GameStateMachine, in_memory_store: EventStore
) -> None:
    """Test that failed transitions do not emit events."""
    initial_count = in_memory_store.get_event_count()

    # Attempt invalid transition
    with pytest.raises(StateTransitionError):
        state_machine.transition(GameState.COMBAT)

    # Event count should remain unchanged
    assert in_memory_store.get_event_count() == initial_count


def test_multiple_transitions_emit_multiple_events(
    state_machine: GameStateMachine, in_memory_store: EventStore
) -> None:
    """Test that multiple transitions emit multiple events."""
    initial_count = in_memory_store.get_event_count()

    state_machine.transition(GameState.EXPLORING)
    state_machine.transition(GameState.COMBAT)
    state_machine.transition(GameState.EXPLORING)

    # Should have emitted 3 events
    assert in_memory_store.get_event_count() == initial_count + 3


# ============================================================================
# Test: Helper Methods
# ============================================================================


def test_get_allowed_transitions_from_menu(state_machine: GameStateMachine) -> None:
    """Test get_allowed_transitions() from MENU state."""
    allowed = state_machine.get_allowed_transitions()

    assert GameState.EXPLORING in allowed
    assert GameState.TIMELINE_VIEW in allowed
    assert GameState.GAME_OVER in allowed
    assert len(allowed) == 3


def test_get_allowed_transitions_from_exploring(
    state_machine: GameStateMachine,
) -> None:
    """Test get_allowed_transitions() from EXPLORING state."""
    state_machine.transition(GameState.EXPLORING)

    allowed = state_machine.get_allowed_transitions()

    assert GameState.COMBAT in allowed
    assert GameState.DIALOGUE in allowed
    assert GameState.INVENTORY in allowed
    assert GameState.TIMELINE_VIEW in allowed
    assert GameState.PAUSED in allowed
    assert GameState.MENU in allowed
    assert GameState.GAME_OVER in allowed
    assert len(allowed) == 7


def test_get_allowed_transitions_returns_copy(state_machine: GameStateMachine) -> None:
    """Test that get_allowed_transitions() returns a copy, not original set."""
    allowed1 = state_machine.get_allowed_transitions()
    allowed2 = state_machine.get_allowed_transitions()

    # Should be equal but not the same object
    assert allowed1 == allowed2
    assert allowed1 is not allowed2

    # Modifying one should not affect the other
    allowed1.clear()
    allowed2_after = state_machine.get_allowed_transitions()
    assert len(allowed2_after) == 3  # Still has 3 transitions from MENU


def test_can_transition_to_valid(state_machine: GameStateMachine) -> None:
    """Test can_transition_to() returns True for valid transitions."""
    assert state_machine.can_transition_to(GameState.EXPLORING) is True
    assert state_machine.can_transition_to(GameState.TIMELINE_VIEW) is True
    assert state_machine.can_transition_to(GameState.GAME_OVER) is True


def test_can_transition_to_invalid(state_machine: GameStateMachine) -> None:
    """Test can_transition_to() returns False for invalid transitions."""
    assert state_machine.can_transition_to(GameState.COMBAT) is False
    assert state_machine.can_transition_to(GameState.DIALOGUE) is False
    assert state_machine.can_transition_to(GameState.INVENTORY) is False
    assert state_machine.can_transition_to(GameState.PAUSED) is False


# ============================================================================
# Test: Edge Cases
# ============================================================================


def test_transition_to_same_state_is_noop(state_machine: GameStateMachine) -> None:
    """Test that transitioning to the current state is a no-op."""
    assert state_machine.current_state == GameState.MENU

    # Transition to same state
    state_machine.transition(GameState.MENU)

    # Should still be in MENU
    assert state_machine.current_state == GameState.MENU


def test_transition_to_same_state_does_not_emit_event(
    state_machine: GameStateMachine, in_memory_store: EventStore
) -> None:
    """Test that no-op transitions don't emit events."""
    initial_count = in_memory_store.get_event_count()

    state_machine.transition(GameState.MENU)

    # Event count should remain unchanged
    assert in_memory_store.get_event_count() == initial_count


def test_transition_with_invalid_type(state_machine: GameStateMachine) -> None:
    """Test that transition() validates to_state type."""
    with pytest.raises(ValueError, match="to_state must be GameState enum"):
        state_machine.transition("EXPLORING")  # type: ignore


def test_transition_with_none_context(state_machine: GameStateMachine) -> None:
    """Test that transition() handles None context gracefully."""
    state_machine.transition(GameState.EXPLORING, None)

    assert state_machine.current_state == GameState.EXPLORING


def test_transition_with_empty_context(state_machine: GameStateMachine) -> None:
    """Test that transition() handles empty context dictionary."""
    state_machine.transition(GameState.EXPLORING, {})

    assert state_machine.current_state == GameState.EXPLORING


# ============================================================================
# Test: String Representations
# ============================================================================


def test_state_machine_repr(state_machine: GameStateMachine) -> None:
    """Test __repr__ returns developer-friendly representation."""
    repr_str = repr(state_machine)

    assert "GameStateMachine" in repr_str
    assert "state=MENU" in repr_str
    assert "session=test_session_001" in repr_str
    assert "timeline=test_timeline_main" in repr_str


def test_state_machine_str(state_machine: GameStateMachine) -> None:
    """Test __str__ returns user-friendly representation."""
    str_repr = str(state_machine)

    assert str_repr == "State: MENU"


def test_state_machine_str_after_transition(state_machine: GameStateMachine) -> None:
    """Test __str__ updates after state transition."""
    state_machine.transition(GameState.EXPLORING)

    str_repr = str(state_machine)
    assert str_repr == "State: EXPLORING"


# ============================================================================
# Test: Transition Graph Completeness
# ============================================================================


def test_all_states_have_transitions_defined() -> None:
    """Test that ALLOWED_TRANSITIONS defines transitions for all states."""
    all_states = set(GameState)
    defined_states = set(GameStateMachine.ALLOWED_TRANSITIONS.keys())

    assert all_states == defined_states, "Some states missing from ALLOWED_TRANSITIONS"


def test_game_over_only_transitions_to_menu() -> None:
    """Test that GAME_OVER can only transition to MENU (restart)."""
    allowed = GameStateMachine.ALLOWED_TRANSITIONS[GameState.GAME_OVER]

    assert allowed == {GameState.MENU}


def test_all_states_can_reach_game_over() -> None:
    """Test that all states (except GAME_OVER) can eventually reach GAME_OVER."""
    # This is a graph reachability test
    # MENU, EXPLORING, COMBAT can directly reach GAME_OVER
    # DIALOGUE, INVENTORY can reach EXPLORING, then GAME_OVER
    # TIMELINE_VIEW can reach EXPLORING, then GAME_OVER
    # PAUSED can reach EXPLORING/COMBAT, then GAME_OVER

    direct_to_game_over = [
        GameState.MENU,
        GameState.EXPLORING,
        GameState.COMBAT,
    ]

    for state in direct_to_game_over:
        allowed = GameStateMachine.ALLOWED_TRANSITIONS[state]
        assert (
            GameState.GAME_OVER in allowed
        ), f"{state} cannot directly reach GAME_OVER"


def test_exploring_is_hub_state() -> None:
    """Test that EXPLORING is a hub state with most connections."""
    exploring_transitions = GameStateMachine.ALLOWED_TRANSITIONS[GameState.EXPLORING]

    # EXPLORING should be able to reach 7 states (most of any state)
    assert len(exploring_transitions) == 7

    # Should connect to all major game modes
    assert GameState.COMBAT in exploring_transitions
    assert GameState.DIALOGUE in exploring_transitions
    assert GameState.INVENTORY in exploring_transitions
    assert GameState.TIMELINE_VIEW in exploring_transitions
    assert GameState.PAUSED in exploring_transitions
    assert GameState.MENU in exploring_transitions
    assert GameState.GAME_OVER in exploring_transitions


# ============================================================================
# Test: Complex Transition Sequences
# ============================================================================


def test_complex_game_loop_sequence(state_machine: GameStateMachine) -> None:
    """Test a complex sequence of valid transitions simulating gameplay."""
    # Start game
    state_machine.transition(GameState.EXPLORING)
    assert state_machine.current_state == GameState.EXPLORING

    # Talk to NPC
    state_machine.transition(GameState.DIALOGUE)
    assert state_machine.current_state == GameState.DIALOGUE

    # NPC sends you back to exploring
    state_machine.transition(GameState.EXPLORING)
    assert state_machine.current_state == GameState.EXPLORING

    # Encounter enemy
    state_machine.transition(GameState.COMBAT)
    assert state_machine.current_state == GameState.COMBAT

    # Use potion in combat
    state_machine.transition(GameState.INVENTORY)
    assert state_machine.current_state == GameState.INVENTORY

    # Return to combat
    state_machine.transition(GameState.COMBAT)
    assert state_machine.current_state == GameState.COMBAT

    # Win combat
    state_machine.transition(GameState.EXPLORING)
    assert state_machine.current_state == GameState.EXPLORING

    # Pause game
    state_machine.transition(GameState.PAUSED)
    assert state_machine.current_state == GameState.PAUSED

    # Resume
    state_machine.transition(GameState.EXPLORING)
    assert state_machine.current_state == GameState.EXPLORING

    # View timeline
    state_machine.transition(GameState.TIMELINE_VIEW)
    assert state_machine.current_state == GameState.TIMELINE_VIEW

    # Return to exploring
    state_machine.transition(GameState.EXPLORING)
    assert state_machine.current_state == GameState.EXPLORING

    # Die in combat
    state_machine.transition(GameState.COMBAT)
    state_machine.transition(GameState.GAME_OVER)
    assert state_machine.current_state == GameState.GAME_OVER

    # Restart
    state_machine.transition(GameState.MENU)
    assert state_machine.current_state == GameState.MENU


def test_branching_timeline_scenario(state_machine: GameStateMachine) -> None:
    """Test a timeline branching scenario."""
    # Start exploring
    state_machine.transition(GameState.EXPLORING)

    # View timeline
    state_machine.transition(GameState.TIMELINE_VIEW)

    # Timeline triggers dialogue (time paradox conversation)
    state_machine.transition(GameState.DIALOGUE)

    # Dialogue leads to combat (timeline guardian)
    state_machine.transition(GameState.COMBAT)

    # Defeat leads to game over
    state_machine.transition(GameState.GAME_OVER)

    assert state_machine.current_state == GameState.GAME_OVER

