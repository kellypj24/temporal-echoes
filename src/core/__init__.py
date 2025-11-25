"""Core game systems for Temporal Echoes.

This package contains the foundational architecture components:
- Event sourcing (events, persistence)
- State machine
- Game context
- Game loop
- Configuration
"""

from .config import GameConfig
from .events import EventTypes, GameEvent
from .exceptions import StateTransitionError, TemporalEchoesError
from .game_context import GameContext
from .game_loop import GameLoop
from .persistence import EventStore
from .state_machine import GameState, GameStateMachine

__all__ = [
    "EventTypes",
    "GameEvent",
    "EventStore",
    "StateTransitionError",
    "TemporalEchoesError",
    "GameState",
    "GameStateMachine",
    "GameContext",
    "GameLoop",
    "GameConfig",
]
