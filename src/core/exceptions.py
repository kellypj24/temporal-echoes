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


class TemporalError(TemporalEchoesError):
    """
    Base class for all temporal-ability failures (rewind, echo cast, counter-stop).

    Catch this to handle any failure of a temporal ability without specifying
    each concrete subclass.
    """

    pass


class InsufficientChargeError(TemporalError):
    """
    Raised when a temporal ability is invoked with too little temporal_charge.

    The actor's current charge is less than the amount the ability requires.
    No event is emitted; no state is mutated. Caller should surface this
    to the player as "not enough charge" UX feedback.
    """

    pass


class RewindBoundaryError(TemporalError):
    """
    Raised when a rewind would land before turn 0 (combat start).

    ``turns`` is greater than ``combat._total_turns``, so the requested
    target turn is negative. No event is emitted; no state is mutated.
    """

    pass


class RewindUnavailableError(TemporalError):
    """
    Raised when combat phase forbids rewind right now.

    Rewind is only allowed during ``AWAITING_PLAYER_INPUT`` or ``ROUND_END``.
    Mid-resolution (``EXECUTING_TURN``) or post-combat (``COMBAT_OVER``)
    rewinds are rejected to keep replay deterministic and meaningful.
    No event is emitted; no state is mutated.
    """

    pass


class RewindReplayError(TemporalError):
    """
    Raised when event replay fails after CHARGE_SPENT has already been recorded.

    By the time this is raised, in-memory CombatContext state has been
    restored from the pre-rewind snapshot (HP, BP, shields, RNG, phase,
    branch_id, turn counters). The ``CHARGE_SPENT`` event is *not* rolled
    back from the event store: it stands as an immutable historical record
    of the failed attempt (Constitution principle 11). The abandoned branch
    means the failed spend washes out of any future charge resolution.

    A retried rewind after this error emits a second CHARGE_SPENT event;
    the log truthfully records both attempts.
    """

    pass


class EchoHistoryError(TemporalError):
    """
    Raised when the owner has fewer recorded actions than the requested echo duration.

    Echo Cast draws its source window from the owner's last ``turns``
    executed actions (``CombatContext._action_history``); if fewer exist,
    there is nothing to embed in the ``ECHO_SPAWNED`` payload. No event is
    emitted; no state is mutated.
    """

    pass


class EchoAlreadyActiveError(TemporalError):
    """
    Raised when the actor's side already has a live echo.

    Max 1 active echo per side (DESIGN M1 constraint). An echo counts as
    "live" unless it has expired (all source actions replayed) or its
    owner is dead (inert — Phase 3 Step 5 locked semantic 9). No event is
    emitted; no state is mutated.
    """

    pass


class EchoUnavailableError(TemporalError):
    """
    Raised when Echo Cast is invoked after combat has already ended.

    No event is emitted; no state is mutated.
    """

    pass
