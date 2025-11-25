"""Game context and session management.

This module implements the GameContext class, which serves as the central
coordinator for all game systems. It manages the lifecycle of game sessions,
coordinates between EventStore and GameStateMachine, and provides a clean
dependency injection container.

Architecture Decision Records:
- DEC-0002: Custom State Machine Pattern (integrated here)
- DEC-0001: SQLite for Event Store (integrated here)

Constitution Principles:
- #2: Dependency injection (no global state)
- #3: Type safety (type hints on all functions)
- #1: Event sourcing (coordinates event emission)
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from .events import EventTypes, GameEvent
from .persistence import EventStore
from .state_machine import GameState, GameStateMachine

logger = logging.getLogger(__name__)


class GameContext:
    """
    Central coordinator for all game systems and session management.

    GameContext serves as the dependency injection container and lifecycle
    manager for a game session. It coordinates between the EventStore and
    GameStateMachine, tracks session/timeline identities, and provides
    convenient methods for common game operations.

    Architecture:
        GameContext owns and coordinates:
        - EventStore: Persistence layer for event sourcing
        - GameStateMachine: State transition management
        - Session/Timeline IDs: Identity tracking

    Design Principles (Constitution):
        - No global state: All dependencies injected via constructor
        - Dependency injection: Systems passed in, not created
        - Event sourcing: All state changes flow through event store
        - Type safety: Full type hints throughout

    Usage:
        >>> # Manual initialization
        >>> event_store = EventStore("data/events.db")
        >>> context = GameContext(
        ...     event_store=event_store,
        ...     session_id="sess_001",
        ...     timeline_id="main"
        ... )
        >>> context.state_machine.transition(GameState.EXPLORING)
        >>> context.close()

        >>> # Context manager (recommended)
        >>> with GameContext.create("data/events.db") as context:
        ...     context.state_machine.transition(GameState.EXPLORING)
        ...     # Automatic cleanup on exit

    Attributes:
        session_id: Unique identifier for this game session
        timeline_id: Unique identifier for this timeline
        event_store: EventStore instance (read-only)
        state_machine: GameStateMachine instance (read-only)
    """

    def __init__(
        self,
        event_store: EventStore,
        session_id: str,
        timeline_id: str,
        initial_state: GameState = GameState.MENU,
    ):
        """
        Initialize GameContext with injected dependencies.

        Args:
            event_store: EventStore instance for persistence
            session_id: Unique identifier for this game session
            timeline_id: Unique identifier for this timeline
            initial_state: Starting game state (defaults to MENU)

        Raises:
            ValueError: If session_id or timeline_id is empty

        Example:
            >>> store = EventStore(":memory:")
            >>> context = GameContext(
            ...     event_store=store,
            ...     session_id="sess_001",
            ...     timeline_id="main"
            ... )
        """
        if not session_id:
            raise ValueError("session_id cannot be empty")
        if not timeline_id:
            raise ValueError("timeline_id cannot be empty")

        self.session_id = session_id
        self.timeline_id = timeline_id

        # Store dependencies (read-only via properties)
        self._event_store = event_store
        self._state_machine = GameStateMachine(
            event_store=event_store,
            session_id=session_id,
            timeline_id=timeline_id,
            initial_state=initial_state,
        )

        # Emit session start event
        self._emit_session_event(EventTypes.GAME_START)

        logger.info(
            f"GameContext initialized: session={session_id}, "
            f"timeline={timeline_id}, state={initial_state.name}"
        )

    @property
    def event_store(self) -> EventStore:
        """
        Get the EventStore instance (read-only).

        Returns:
            EventStore instance for this context
        """
        return self._event_store

    @property
    def state_machine(self) -> GameStateMachine:
        """
        Get the GameStateMachine instance (read-only).

        Returns:
            GameStateMachine instance for this context
        """
        return self._state_machine

    @property
    def current_state(self) -> GameState:
        """
        Get the current game state (convenience property).

        Returns:
            Current GameState enum value
        """
        return self._state_machine.current_state

    def _emit_session_event(self, event_type: str) -> None:
        """
        Emit a session lifecycle event.

        Args:
            event_type: Type of session event (GAME_START, GAME_END, etc.)
        """
        event = GameEvent(
            event_type=event_type,
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            aggregate_id=f"session_{self.session_id}",
            aggregate_type="session",
            event_data="{}",
            metadata=f'{{"timestamp": "{datetime.now(UTC).isoformat()}"}}',
        )
        self._event_store.append_event(event)
        logger.debug(f"Session event emitted: {event_type}")

    def close(self) -> None:
        """
        Close the game context and clean up resources.

        This emits a GAME_END event and closes the EventStore connection.
        After calling close(), the context should not be used.

        Example:
            >>> context = GameContext.create("data/events.db")
            >>> # ... use context ...
            >>> context.close()
        """
        # Emit session end event
        self._emit_session_event(EventTypes.GAME_END)

        # Close EventStore
        self._event_store.close()

        logger.info(f"GameContext closed: session={self.session_id}")

    def __enter__(self) -> "GameContext":
        """
        Context manager entry.

        Returns:
            Self for use in with statement

        Example:
            >>> with GameContext.create("data/events.db") as context:
            ...     context.state_machine.transition(GameState.EXPLORING)
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        """
        Context manager exit (automatic cleanup).

        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)
        """
        self.close()

    # ========================================================================
    # Common Operations (Convenience Methods)
    # ========================================================================

    def transition_to(self, to_state: GameState, context: dict | None = None) -> None:
        """
        Transition to a new game state (convenience method).

        This is a convenience wrapper around state_machine.transition()
        for cleaner code.

        Args:
            to_state: Target game state
            context: Optional context dictionary

        Raises:
            StateTransitionError: If transition is not allowed

        Example:
            >>> context.transition_to(GameState.EXPLORING, {"reason": "start_game"})
        """
        self._state_machine.transition(to_state, context)

    def get_session_events(self, limit: int | None = None) -> list[GameEvent]:
        """
        Get all events for this session.

        Args:
            limit: Optional limit on number of events to return

        Returns:
            List of GameEvent objects for this session

        Example:
            >>> events = context.get_session_events(limit=10)
            >>> print(f"Last 10 events: {len(events)}")
        """
        return self._event_store.get_events_by_session(self.session_id, limit)

    def get_timeline_events(self, limit: int | None = None) -> list[GameEvent]:
        """
        Get all events for this timeline.

        Args:
            limit: Optional limit on number of events to return

        Returns:
            List of GameEvent objects for this timeline

        Example:
            >>> events = context.get_timeline_events()
            >>> print(f"Timeline has {len(events)} events")
        """
        return self._event_store.get_events_by_timeline(self.timeline_id, limit)

    def get_event_count(self) -> int:
        """
        Get total event count for this session.

        Returns:
            Number of events in this session

        Example:
            >>> count = context.get_event_count()
            >>> print(f"Session has {count} events")
        """
        # Query by session to get session-specific count
        return len(self.get_session_events())

    def branch_timeline(
        self, new_timeline_id: str, branch_point_timestamp: float | None = None
    ) -> None:
        """
        Create a timeline branch from the current timeline.

        This is a convenience wrapper for timeline branching, which is
        crucial for the time-travel mechanics in later phases.

        Args:
            new_timeline_id: ID for the new timeline branch
            branch_point_timestamp: Optional timestamp to branch from

        Example:
            >>> # Branch from current point
            >>> context.branch_timeline("alternate_timeline")

            >>> # Branch from specific timestamp
            >>> context.branch_timeline("past_branch", branch_point_timestamp=1234567890.0)
        """
        self._event_store.create_timeline(
            new_timeline_id=new_timeline_id,
            source_timeline_id=self.timeline_id,
            session_id=self.session_id,
            branch_point_timestamp=branch_point_timestamp,
        )
        logger.info(
            f"Timeline branched: {self.timeline_id} -> {new_timeline_id} "
            f"at timestamp {branch_point_timestamp or 'current'}"
        )

    # ========================================================================
    # Serialization (Save/Load Support)
    # ========================================================================

    def to_dict(self) -> dict:
        """
        Serialize context to dictionary for save/load.

        This creates a snapshot of the current game context that can be
        saved to disk and later restored. The EventStore is not serialized
        (it's persisted separately in the database).

        Returns:
            Dictionary containing serializable context data

        Example:
            >>> context_data = context.to_dict()
            >>> print(context_data)
            {
                'session_id': 'sess_abc123',
                'timeline_id': 'timeline_xyz',
                'current_state': 'EXPLORING',
                'event_count': 42
            }
        """
        return {
            "session_id": self.session_id,
            "timeline_id": self.timeline_id,
            "current_state": self.current_state.name,
            "event_count": self.get_event_count(),
        }

    @classmethod
    def from_dict(cls, data: dict, event_store: EventStore) -> "GameContext":
        """
        Deserialize context from dictionary.

        This reconstructs a GameContext from a saved snapshot. The state
        machine is reconstructed with the saved state, allowing the game
        to resume from where it was saved.

        Args:
            data: Dictionary containing serialized context data
            event_store: EventStore instance to use (must contain the session's events)

        Returns:
            Reconstructed GameContext instance

        Raises:
            ValueError: If required fields are missing from data
            KeyError: If state name is invalid

        Example:
            >>> # Save
            >>> context_data = context.to_dict()
            >>> # ... later ...
            >>> # Load
            >>> store = EventStore("data/events.db")
            >>> restored_context = GameContext.from_dict(context_data, store)
            >>> print(restored_context.current_state)
            <GameState.EXPLORING: 2>
        """
        # Validate required fields
        required_fields = ["session_id", "timeline_id", "current_state"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Parse state
        try:
            initial_state = GameState[data["current_state"]]
        except KeyError as e:
            raise KeyError(f"Invalid state name: {data['current_state']}") from e

        # Reconstruct context (without emitting GAME_START event)
        # We directly construct to avoid duplicate events
        context = cls.__new__(cls)
        context.session_id = data["session_id"]
        context.timeline_id = data["timeline_id"]
        context._event_store = event_store
        context._state_machine = GameStateMachine(
            event_store=event_store,
            session_id=data["session_id"],
            timeline_id=data["timeline_id"],
            initial_state=initial_state,
        )

        logger.info(
            f"GameContext restored from save: session={context.session_id}, "
            f"state={initial_state.name}"
        )

        return context

    # ========================================================================
    # Factory Method
    # ========================================================================

    @classmethod
    def create(
        cls,
        db_path: str,
        session_id: str | None = None,
        timeline_id: str | None = None,
        initial_state: GameState = GameState.MENU,
    ) -> "GameContext":
        """
        Factory method to create a new GameContext with auto-generated IDs.

        This is the recommended way to create a GameContext. It handles:
        - EventStore initialization
        - Session/timeline ID generation (if not provided)
        - Clean initialization flow

        Args:
            db_path: Path to SQLite database (use ":memory:" for testing)
            session_id: Optional session ID (auto-generated if None)
            timeline_id: Optional timeline ID (auto-generated if None)
            initial_state: Starting game state (defaults to MENU)

        Returns:
            Initialized GameContext instance

        Example:
            >>> # Auto-generate IDs
            >>> context = GameContext.create("data/events.db")
            >>> print(context.session_id)  # sess_a1b2c3d4...

            >>> # Provide custom IDs
            >>> context = GameContext.create(
            ...     "data/events.db",
            ...     session_id="my_session",
            ...     timeline_id="main"
            ... )

            >>> # In-memory for testing
            >>> context = GameContext.create(":memory:")

            >>> # Use as context manager
            >>> with GameContext.create("data/events.db") as ctx:
            ...     ctx.state_machine.transition(GameState.EXPLORING)
        """
        # Generate IDs if not provided
        if session_id is None:
            session_id = f"sess_{uuid4().hex[:16]}"
        if timeline_id is None:
            timeline_id = f"timeline_{uuid4().hex[:16]}"

        # Create EventStore
        event_store = EventStore(db_path)

        # Create and return context
        return cls(
            event_store=event_store,
            session_id=session_id,
            timeline_id=timeline_id,
            initial_state=initial_state,
        )

    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (
            f"GameContext("
            f"session={self.session_id}, "
            f"timeline={self.timeline_id}, "
            f"state={self.current_state.name})"
        )

    def __str__(self) -> str:
        """User-friendly string representation."""
        return f"Game Session: {self.session_id} (Timeline: {self.timeline_id})"
