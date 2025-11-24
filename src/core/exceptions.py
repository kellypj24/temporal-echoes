"""Custom exceptions for Temporal Echoes.

This module defines game-specific exceptions for better error handling
and debugging. All custom exceptions inherit from a base class for
easy catching and filtering.
"""


class TemporalEchoesError(Exception):
    """
    Base exception for all Temporal Echoes custom exceptions.

    This allows catching all game-specific errors with a single except clause:
        try:
            game.run()
        except TemporalEchoesError as e:
            logger.error(f"Game error: {e}")

    All custom exceptions should inherit from this base class.
    """

    pass


class StateTransitionError(TemporalEchoesError):
    """
    Raised when an invalid state transition is attempted.

    This exception is raised by GameStateMachine when attempting to
    transition from one state to another state that is not allowed
    by the ALLOWED_TRANSITIONS configuration.

    Examples:
        >>> machine.transition(GameState.COMBAT, {})  # From MENU
        StateTransitionError: Invalid transition: MENU -> COMBAT

        >>> machine.transition(GameState.TIMELINE_VIEW, {})  # From COMBAT
        StateTransitionError: Invalid transition: COMBAT -> TIMELINE_VIEW

    Attributes:
        from_state: The current state (where transition was attempted from)
        to_state: The target state (where transition was attempted to)
        message: Human-readable error message
    """

    def __init__(
        self,
        message: str,
        from_state: str | None = None,
        to_state: str | None = None,
    ):
        """
        Initialize StateTransitionError.

        Args:
            message: Human-readable error message
            from_state: Optional current state name
            to_state: Optional target state name
        """
        super().__init__(message)
        self.from_state = from_state
        self.to_state = to_state
        self.message = message

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.from_state and self.to_state:
            return f"Invalid transition: {self.from_state} -> {self.to_state}"
        return self.message
