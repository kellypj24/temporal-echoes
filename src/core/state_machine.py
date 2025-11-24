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

from enum import Enum, auto


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
