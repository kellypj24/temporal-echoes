"""State machine implementation for game state management.

This module implements a custom state machine for managing game modes
(MENU, EXPLORING, COMBAT, etc.) with explicit transition validation
and event emission for event sourcing.

Architecture Decision Records:
- DEC-0002: Custom State Machine Pattern (no external library)
- Research Topic 3: State Machine Pattern

Constitution Principles:
- #1: Event sourcing (emit events on state changes)
- #2: Dependency injection (EventStore injected via constructor)
- #3: Type safety (type hints on all functions)
"""

import json
import logging
from datetime import UTC, datetime
from enum import Enum, auto

from .events import EventTypes, GameEvent
from .exceptions import StateTransitionError
from .persistence import EventStore

logger = logging.getLogger(__name__)


class GameState(Enum):
    """
    Enumeration of all possible game states.

    The game operates in one state at a time, transitioning between
    states based on player actions and game events. Each state represents
    a distinct mode of gameplay with different rules and UI.

    States:
        MENU: Main menu, game selection, settings
        EXPLORING: Free roaming, NPC interaction, item collection
        COMBAT: Turn-based combat encounters
        DIALOGUE: Conversation with NPCs
        INVENTORY: Item management, equipment
        TIMELINE_VIEW: Timeline visualization and branching
        PAUSED: Game paused (can resume)
        GAME_OVER: End of game (success or failure)

    Usage:
        >>> state = GameState.MENU
        >>> state.name
        'MENU'
        >>> state.value
        1
    """

    MENU = auto()
    EXPLORING = auto()
    COMBAT = auto()
    DIALOGUE = auto()
    INVENTORY = auto()
    TIMELINE_VIEW = auto()
    PAUSED = auto()
    GAME_OVER = auto()

    def __str__(self) -> str:
        """Return the state name for logging."""
        return self.name


class GameStateMachine:
    """
    Custom state machine for managing game state transitions.

    This class manages the current game state and validates all state
    transitions according to the ALLOWED_TRANSITIONS graph. Events are
    emitted for every state change to support event sourcing.

    Design Decisions (from DEC-0002):
    - Custom implementation (no external library)
    - Explicit transition validation
    - Event emission BEFORE state change (Research Topic 3)
    - Dependency injection (EventStore via constructor)

    Architecture:
        MENU ←→ EXPLORING ←→ COMBAT
                    ↕           ↕
               DIALOGUE    INVENTORY
                    ↕           ↕
              TIMELINE_VIEW  PAUSED
                    ↓
               GAME_OVER

    Usage:
        >>> store = EventStore(":memory:")
        >>> machine = GameStateMachine(store, session_id="sess_001", timeline_id="main")
        >>> machine.current_state
        <GameState.MENU: 1>
        >>> machine.transition(GameState.EXPLORING, {"reason": "start_game"})
        >>> machine.current_state
        <GameState.EXPLORING: 2>

    Attributes:
        current_state: The current game state (read-only via property)
        session_id: Current game session identifier
        timeline_id: Current timeline identifier
    """

    # Define allowed state transitions (explicit graph)
    # Key: from_state, Value: set of allowed to_states
    ALLOWED_TRANSITIONS: dict[GameState, set[GameState]] = {
        GameState.MENU: {
            GameState.EXPLORING,  # Start new game
            GameState.TIMELINE_VIEW,  # View timeline from menu
            GameState.GAME_OVER,  # Quit game
        },
        GameState.EXPLORING: {
            GameState.COMBAT,  # Encounter enemy
            GameState.DIALOGUE,  # Talk to NPC
            GameState.INVENTORY,  # Open inventory
            GameState.TIMELINE_VIEW,  # View timeline
            GameState.PAUSED,  # Pause game
            GameState.MENU,  # Return to menu
            GameState.GAME_OVER,  # Death or completion
        },
        GameState.COMBAT: {
            GameState.EXPLORING,  # Victory or escape
            GameState.INVENTORY,  # Use item in combat
            GameState.PAUSED,  # Pause during combat
            GameState.GAME_OVER,  # Defeat
        },
        GameState.DIALOGUE: {
            GameState.EXPLORING,  # End conversation
            GameState.COMBAT,  # Conversation triggers fight
            GameState.TIMELINE_VIEW,  # NPC shows timeline
        },
        GameState.INVENTORY: {
            GameState.EXPLORING,  # Close inventory
            GameState.COMBAT,  # Return to combat
        },
        GameState.TIMELINE_VIEW: {
            GameState.EXPLORING,  # Return to exploration
            GameState.MENU,  # Return to menu
            GameState.DIALOGUE,  # Timeline triggers conversation
        },
        GameState.PAUSED: {
            GameState.EXPLORING,  # Resume from exploration
            GameState.COMBAT,  # Resume combat
            GameState.MENU,  # Return to menu
        },
        GameState.GAME_OVER: {
            GameState.MENU,  # Restart or main menu
        },
    }

    def __init__(
        self,
        event_store: EventStore,
        session_id: str,
        timeline_id: str,
        initial_state: GameState = GameState.MENU,
    ):
        """
        Initialize GameStateMachine with event store and identifiers.

        Args:
            event_store: EventStore instance for persisting state transitions
            session_id: Unique identifier for this game session
            timeline_id: Unique identifier for this timeline
            initial_state: Starting state (defaults to MENU)

        Raises:
            ValueError: If session_id or timeline_id is empty
        """
        if not session_id:
            raise ValueError("session_id cannot be empty")
        if not timeline_id:
            raise ValueError("timeline_id cannot be empty")

        self._event_store = event_store
        self._state = initial_state
        self.session_id = session_id
        self.timeline_id = timeline_id

        logger.info(
            f"GameStateMachine initialized: "
            f"session={session_id}, timeline={timeline_id}, state={initial_state}"
        )

    @property
    def current_state(self) -> GameState:
        """
        Get the current game state (read-only).

        Returns:
            Current GameState
        """
        return self._state

    def transition(self, to_state: GameState, context: dict | None = None) -> None:
        """
        Transition to a new game state with validation and event emission.

        This method:
        1. Validates the transition is allowed
        2. Emits a StateTransition event (BEFORE state change per Research Topic 3)
        3. Updates the internal state
        4. Logs the transition

        Args:
            to_state: Target game state
            context: Optional context dictionary (e.g., {"reason": "player_died"})

        Raises:
            StateTransitionError: If transition is not allowed
            ValueError: If to_state is not a GameState enum

        Example:
            >>> machine.transition(GameState.COMBAT, {"enemy": "Shadow Beast"})
        """
        if not isinstance(to_state, GameState):
            raise ValueError(f"to_state must be GameState enum, got {type(to_state)}")

        # Check if already in target state (no-op)
        if self._state == to_state:
            logger.debug(f"Already in state {to_state}, no transition needed")
            return

        # Validate transition is allowed
        if not self._is_valid_transition(to_state):
            raise StateTransitionError(
                message=f"Invalid transition: {self._state.name} -> {to_state.name}",
                from_state=self._state.name,
                to_state=to_state.name,
            )

        from_state = self._state

        # Emit event BEFORE state change (Research Topic 3)
        # This ensures event log accurately reflects the transition point
        event_data_dict = {
            "from": from_state.name,
            "to": to_state.name,
            "context": context or {},
        }

        event = GameEvent(
            event_type=EventTypes.STATE_TRANSITION,
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            aggregate_id=f"game_{self.session_id}",
            aggregate_type="game_state",
            event_data=json.dumps(event_data_dict),
            metadata=f'{{"timestamp": "{datetime.now(UTC).isoformat()}"}}',
        )

        self._event_store.append_event(event)

        # Update state AFTER event emission
        self._state = to_state

        logger.info(
            f"State transition: {from_state.name} -> {to_state.name} "
            f"(session={self.session_id}, timeline={self.timeline_id})"
        )

    def _is_valid_transition(self, to_state: GameState) -> bool:
        """
        Check if transition from current state to target state is allowed.

        Args:
            to_state: Target game state

        Returns:
            True if transition is allowed, False otherwise
        """
        allowed_states = self.ALLOWED_TRANSITIONS.get(self._state, set())
        return to_state in allowed_states

    def get_allowed_transitions(self) -> set[GameState]:
        """
        Get all valid transitions from the current state.

        Useful for UI to show available actions or for AI to determine
        valid next states.

        Returns:
            Set of GameState enums that can be transitioned to

        Example:
            >>> machine.current_state
            <GameState.EXPLORING: 2>
            >>> machine.get_allowed_transitions()
            {<GameState.COMBAT: 3>, <GameState.DIALOGUE: 4>, ...}
        """
        return self.ALLOWED_TRANSITIONS.get(self._state, set()).copy()

    def can_transition_to(self, to_state: GameState) -> bool:
        """
        Check if a specific transition is allowed (without raising exception).

        This is a non-throwing alternative to attempting a transition.

        Args:
            to_state: Target game state to check

        Returns:
            True if transition is allowed, False otherwise

        Example:
            >>> if machine.can_transition_to(GameState.COMBAT):
            ...     machine.transition(GameState.COMBAT, {"enemy": "Goblin"})
        """
        return self._is_valid_transition(to_state)

    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (
            f"GameStateMachine("
            f"state={self._state.name}, "
            f"session={self.session_id}, "
            f"timeline={self.timeline_id})"
        )

    def __str__(self) -> str:
        """User-friendly string representation."""
        return f"State: {self._state.name}"
