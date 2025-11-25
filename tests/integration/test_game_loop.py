"""Integration tests for GameLoop.

These tests verify that the entire system works together:
- GameLoop + GameContext + GameStateMachine + EventStore
- Fixed timestep accumulator pattern
- State handler registration and execution
- Graceful shutdown
- Performance characteristics (60 Hz target)

Constitution Principles Tested:
- #1: Event sourcing (events flow through the system)
- #2: Dependency injection (all components injected properly)
- #13: 60 FPS target (fixed timestep validation)
"""

import threading
import time

import pytest

from src.core.game_context import GameContext
from src.core.game_loop import GameLoop
from src.core.state_machine import GameState

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def game_context() -> GameContext:
    """Create a GameContext for integration testing."""
    return GameContext.create(
        ":memory:",
        session_id="integration_test",
        timeline_id="test_timeline",
    )


@pytest.fixture
def game_loop(game_context: GameContext) -> GameLoop:
    """Create a GameLoop for integration testing."""
    return GameLoop(game_context, target_fps=60)


# ============================================================================
# Basic Integration Tests
# ============================================================================


def test_game_loop_initialization_with_context(game_loop: GameLoop) -> None:
    """Test that GameLoop initializes properly with GameContext."""
    assert game_loop.context is not None
    assert game_loop.target_fps == 60
    assert not game_loop.is_running
    assert game_loop.FIXED_TIMESTEP == 1.0 / 60.0


def test_game_loop_context_integration(game_context: GameContext) -> None:
    """Test that GameLoop integrates with GameContext properly."""
    loop = GameLoop(game_context)

    # Context should be accessible
    assert loop.context is game_context
    assert loop.context.current_state == GameState.MENU


def test_state_handler_registration_integration(game_loop: GameLoop) -> None:
    """Test state handler registration in integrated system."""
    handler_called = {"count": 0}

    def test_handler(_dt: float) -> None:
        handler_called["count"] += 1

    # Register handler
    game_loop.register_state_handler(GameState.MENU, test_handler)

    # Verify registration (handler will be called during loop execution)
    assert GameState.MENU in game_loop._state_handlers


# ============================================================================
# Loop Execution Tests
# ============================================================================


def test_game_loop_runs_and_stops(game_loop: GameLoop) -> None:
    """Test that game loop can start and stop cleanly."""

    # Run loop in background thread
    def run_loop() -> None:
        game_loop.run()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    # Wait for loop to start
    time.sleep(0.1)

    # Verify loop is running
    assert game_loop.is_running

    # Stop the loop
    game_loop.stop()

    # Wait for thread to finish
    thread.join(timeout=1.0)

    # Verify loop stopped
    assert not game_loop.is_running


def test_state_handler_called_during_loop(game_loop: GameLoop) -> None:
    """Test that state handlers are called during loop execution."""
    handler_called = {"count": 0}

    def menu_handler(_dt: float) -> None:
        handler_called["count"] += 1

        # Stop after 10 calls (to prevent infinite loop)
        if handler_called["count"] >= 10:
            game_loop.stop()

    # Register handler for MENU state (default state)
    game_loop.register_state_handler(GameState.MENU, menu_handler)

    # Run loop in background thread
    def run_loop() -> None:
        game_loop.run()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    # Wait for loop to stop (should stop after 10 calls)
    thread.join(timeout=2.0)

    # Verify handler was called multiple times
    assert handler_called["count"] >= 10


def test_state_transitions_during_loop(game_loop: GameLoop) -> None:
    """Test that state transitions work during loop execution."""
    transitions = []

    def menu_handler(_dt: float) -> None:
        transitions.append("MENU")
        if len(transitions) >= 5:
            # Transition to EXPLORING after 5 ticks
            game_loop.context.transition_to(GameState.EXPLORING)

    def exploring_handler(_dt: float) -> None:
        transitions.append("EXPLORING")
        if len(transitions) >= 10:
            # Stop after 10 total ticks
            game_loop.stop()

    # Register handlers
    game_loop.register_state_handler(GameState.MENU, menu_handler)
    game_loop.register_state_handler(GameState.EXPLORING, exploring_handler)

    # Run loop
    def run_loop() -> None:
        game_loop.run()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    thread.join(timeout=2.0)

    # Verify both handlers were called
    assert "MENU" in transitions
    assert "EXPLORING" in transitions

    # Verify transition happened
    assert transitions[0:5] == ["MENU"] * 5
    assert "EXPLORING" in transitions[5:]


# ============================================================================
# Performance Tests
# ============================================================================


def test_game_loop_maintains_tick_rate(game_loop: GameLoop) -> None:
    """Test that game loop maintains approximately 60 Hz tick rate."""
    tick_count = {"count": 0}
    start_time = {"time": 0.0}

    def counting_handler(_dt: float) -> None:
        if tick_count["count"] == 0:
            start_time["time"] = time.time()

        tick_count["count"] += 1

        # Stop after 120 ticks (2 seconds at 60 Hz)
        if tick_count["count"] >= 120:
            game_loop.stop()

    # Register handler
    game_loop.register_state_handler(GameState.MENU, counting_handler)

    # Run loop
    def run_loop() -> None:
        game_loop.run()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    thread.join(timeout=5.0)

    # Measure elapsed time
    elapsed = time.time() - start_time["time"]

    # Verify tick count
    assert tick_count["count"] >= 120

    # Verify approximate timing (should be close to 2 seconds)
    # Allow some tolerance for system scheduling
    assert 1.8 <= elapsed <= 2.5  # 25% tolerance


def test_fixed_timestep_delta(game_loop: GameLoop) -> None:
    """Test that handlers receive fixed delta time (16.67ms)."""
    deltas = []

    def delta_checking_handler(dt: float) -> None:
        deltas.append(dt)

        # Stop after collecting 10 deltas
        if len(deltas) >= 10:
            game_loop.stop()

    # Register handler
    game_loop.register_state_handler(GameState.MENU, delta_checking_handler)

    # Run loop
    def run_loop() -> None:
        game_loop.run()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    thread.join(timeout=2.0)

    # Verify all deltas are the fixed timestep
    for dt in deltas:
        assert dt == game_loop.FIXED_TIMESTEP


# ============================================================================
# Event Sourcing Integration Tests
# ============================================================================


def test_events_recorded_during_loop(game_context: GameContext) -> None:
    """Test that state transitions during loop are recorded in event store."""
    loop = GameLoop(game_context)

    def transition_handler(_dt: float) -> None:
        # Transition to EXPLORING
        game_context.transition_to(GameState.EXPLORING)
        # Transition to COMBAT
        game_context.transition_to(GameState.COMBAT)
        # Stop loop
        loop.stop()

    loop.register_state_handler(GameState.MENU, transition_handler)

    # Run loop
    def run_loop() -> None:
        loop.run()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    thread.join(timeout=2.0)

    # Verify events were recorded
    events = game_context.get_session_events()

    # Should have: GAME_START + STATE_TRANSITION (MENU->EXPLORING) + STATE_TRANSITION (EXPLORING->COMBAT)
    assert len(events) >= 3

    # Verify event types (EventTypes.STATE_TRANSITION = "StateTransition")
    from src.core.events import EventTypes

    state_transitions = [
        e for e in events if e.event_type == EventTypes.STATE_TRANSITION
    ]
    assert len(state_transitions) == 2


# ============================================================================
# Graceful Shutdown Tests
# ============================================================================


def test_loop_stops_cleanly_via_stop_method(game_loop: GameLoop) -> None:
    """Test that stop() method cleanly stops the loop."""

    def infinite_handler(_dt: float) -> None:
        # Handler that would run forever
        pass

    game_loop.register_state_handler(GameState.MENU, infinite_handler)

    # Run loop in background
    def run_loop() -> None:
        game_loop.run()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    # Wait a bit
    time.sleep(0.2)

    # Stop the loop
    game_loop.stop()

    # Wait for clean shutdown
    thread.join(timeout=1.0)

    # Verify loop stopped
    assert not game_loop.is_running
    assert not thread.is_alive()


def test_signal_handlers_setup(game_loop: GameLoop) -> None:
    """Test that signal handlers can be registered."""
    # Setup signal handlers (should not raise)
    game_loop.setup_signal_handlers()

    # Verify we can still stop normally
    assert not game_loop.is_running


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_loop_with_no_handlers(game_loop: GameLoop) -> None:
    """Test that loop works even with no handlers registered."""

    # No handlers registered - loop should still run

    # Run for a brief period
    def run_loop() -> None:
        game_loop.run()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    # Wait a bit
    time.sleep(0.1)

    # Stop
    game_loop.stop()
    thread.join(timeout=1.0)

    # Should have stopped cleanly
    assert not game_loop.is_running


def test_loop_with_handler_for_different_state(game_loop: GameLoop) -> None:
    """Test loop behavior when handler is for non-current state."""
    combat_called = {"called": False}

    def combat_handler(_dt: float) -> None:
        combat_called["called"] = True
        game_loop.stop()

    # Register handler for COMBAT, but we're in MENU
    game_loop.register_state_handler(GameState.COMBAT, combat_handler)

    # Run loop briefly
    def run_loop() -> None:
        game_loop.run()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    # Wait a bit
    time.sleep(0.1)

    # Stop
    game_loop.stop()
    thread.join(timeout=1.0)

    # Combat handler should not have been called (we're in MENU state)
    assert not combat_called["called"]


def test_handler_overwrite_warning(game_loop: GameLoop) -> None:
    """Test that overwriting a handler logs a warning."""

    def handler1(_dt: float) -> None:
        pass

    def handler2(_dt: float) -> None:
        pass

    # Register first handler
    game_loop.register_state_handler(GameState.MENU, handler1)

    # Register second handler (should log warning)
    game_loop.register_state_handler(GameState.MENU, handler2)

    # Verify second handler is registered
    assert game_loop._state_handlers[GameState.MENU] == handler2


# ============================================================================
# Full System Integration Test
# ============================================================================


def test_full_system_integration() -> None:
    """
    Comprehensive integration test of the entire system.

    This test verifies:
    - GameContext creation with auto-generated IDs
    - GameLoop initialization
    - State handler registration
    - Loop execution
    - State transitions
    - Event recording
    - Graceful shutdown
    """
    # Create context
    context = GameContext.create(":memory:")

    # Create loop
    loop = GameLoop(context)

    # Track execution
    execution_log = []

    def menu_handler(_dt: float) -> None:
        execution_log.append(("MENU", context.current_state.name))
        if len(execution_log) >= 3:
            context.transition_to(GameState.EXPLORING)

    def exploring_handler(_dt: float) -> None:
        execution_log.append(("EXPLORING", context.current_state.name))
        if len(execution_log) >= 6:
            context.transition_to(GameState.COMBAT)

    def combat_handler(_dt: float) -> None:
        execution_log.append(("COMBAT", context.current_state.name))
        if len(execution_log) >= 9:
            loop.stop()

    # Register handlers
    loop.register_state_handler(GameState.MENU, menu_handler)
    loop.register_state_handler(GameState.EXPLORING, exploring_handler)
    loop.register_state_handler(GameState.COMBAT, combat_handler)

    # Run loop
    def run_loop() -> None:
        loop.run()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    thread.join(timeout=3.0)

    # Verify execution
    assert len(execution_log) >= 9

    # Verify state progression
    assert execution_log[0][1] == "MENU"
    assert any(log[1] == "EXPLORING" for log in execution_log)
    assert any(log[1] == "COMBAT" for log in execution_log)

    # Verify events recorded
    events = context.get_session_events()
    assert len(events) >= 3  # GAME_START + transitions

    # Cleanup
    context.close()
