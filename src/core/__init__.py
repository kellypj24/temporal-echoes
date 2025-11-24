"""Core game systems for Temporal Echoes.

This package contains the foundational architecture components:
- Event sourcing (events, persistence)
- State machine
- Game context
- Configuration
"""

from .events import EventTypes, GameEvent
from .exceptions import StateTransitionError, TemporalEchoesError
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
]
