"""Game loop implementation with fixed timestep.

This module implements the main game loop using a fixed timestep accumulator
pattern (Gaffer on Games). The loop runs at 60 Hz (16.67ms per tick) with
deterministic physics, making it compatible with event sourcing and testable.

Architecture Decision Records:
- DEC-0006: Fixed Timestep Game Loop (60 Hz)
- DEC-0003: No Rendering in Phase 1 (console output only)
- Research Topic 2: Pygame Event Loop Integration (threading prep)

Constitution Principles:
- #2: Dependency injection (GameContext injected)
- #3: Type safety (type hints on all functions)
- #13: 60 FPS target (fixed timestep ensures determinism)
"""

import logging
import signal
import time
from collections.abc import Callable

from .game_context import GameContext
from .state_machine import GameState

logger = logging.getLogger(__name__)


class GameLoop:
    """
    Main game loop with fixed timestep and accumulator pattern.

    This class implements a fixed timestep game loop at 60 Hz (16.67ms per tick).
    The loop uses an accumulator pattern to ensure consistent, deterministic
    game logic updates regardless of rendering performance.

    Architecture (Gaffer on Games Pattern):
        1. Measure elapsed time since last frame
        2. Add elapsed time to accumulator
        3. While accumulator >= fixed_dt:
           - Update game logic with fixed_dt
           - Subtract fixed_dt from accumulator
        4. Render with interpolation (Phase 2+)

    Key Features:
        - Fixed timestep: 60 Hz (16.67ms per tick)
        - Deterministic: Logic always uses same delta time
        - Frame skip protection: Max 10 ticks per frame
        - Event sourcing compatible: Deterministic updates
        - No rendering: Console output only (Phase 1)

    Usage:
        >>> context = GameContext.create("data/events.db")
        >>> loop = GameLoop(context, target_fps=60)
        >>> loop.run()  # Runs until stopped
        >>> loop.stop()

    Attributes:
        context: GameContext instance for game state
        target_fps: Target frames per second (default: 60)
        is_running: Whether the loop is currently running
    """

    # Fixed timestep in seconds (60 Hz = 16.67ms)
    FIXED_TIMESTEP = 1.0 / 60.0  # 0.01666... seconds

    # Maximum ticks per frame (prevent spiral of death)
    MAX_FRAME_SKIP = 10

    def __init__(
        self,
        context: GameContext,
        target_fps: int = 60,
    ):
        """
        Initialize GameLoop with game context.

        Args:
            context: GameContext instance for game state management
            target_fps: Target frames per second (default: 60)

        Raises:
            ValueError: If target_fps is invalid
        """
        if target_fps <= 0:
            raise ValueError("target_fps must be positive")

        self.context = context
        self.target_fps = target_fps
        self.is_running = False

        # Timing state
        self._accumulator = 0.0
        self._current_time = 0.0
        self._frame_count = 0
        self._tick_count = 0

        # Performance tracking
        self._last_fps_report = 0.0
        self._fps_report_interval = 5.0  # Report FPS every 5 seconds

        # State handlers (registered via register_state_handler)
        self._state_handlers: dict[GameState, Callable[[float], None]] = {}

        # Shutdown handling
        self._shutdown_requested = False

        logger.info(
            f"GameLoop initialized: target_fps={target_fps}, fixed_dt={self.FIXED_TIMESTEP:.4f}s"
        )

    def register_state_handler(self, state: GameState, handler: Callable[[float], None]) -> None:
        """
        Register an update handler for a specific game state.

        State handlers are called once per game tick (60 Hz) when the game
        is in that state. Handlers receive the fixed delta time (16.67ms).

        Args:
            state: The game state to register the handler for
            handler: Callable that takes delta_time (float) and returns None

        Example:
            >>> def update_combat(dt: float) -> None:
            ...     print(f"Combat update: {dt}s")
            ...
            >>> loop.register_state_handler(GameState.COMBAT, update_combat)
        """
        if state in self._state_handlers:
            logger.warning(f"Overwriting existing handler for state: {state.name}")

        self._state_handlers[state] = handler
        logger.debug(f"Registered handler for state: {state.name}")

    def unregister_state_handler(self, state: GameState) -> None:
        """
        Unregister the update handler for a specific game state.

        Args:
            state: The game state to unregister the handler for

        Example:
            >>> loop.unregister_state_handler(GameState.COMBAT)
        """
        if state in self._state_handlers:
            del self._state_handlers[state]
            logger.debug(f"Unregistered handler for state: {state.name}")
        else:
            logger.warning(f"No handler registered for state: {state.name}")

    def setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for graceful shutdown.

        Registers handlers for SIGINT (Ctrl+C) and SIGTERM to allow
        graceful shutdown when the process receives these signals.

        Example:
            >>> loop = GameLoop(context)
            >>> loop.setup_signal_handlers()
            >>> loop.run()  # Can be stopped with Ctrl+C
        """

        def signal_handler(signum: int, _frame) -> None:  # type: ignore[no-untyped-def]
            """Handle shutdown signals."""
            signal_name = signal.Signals(signum).name
            logger.info(f"Received {signal_name}, requesting shutdown...")
            self._shutdown_requested = True
            self.stop()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.debug("Signal handlers registered (SIGINT, SIGTERM)")

    def run(self) -> None:
        """
        Run the main game loop.

        This method starts the game loop and runs until stop() is called.
        The loop uses a fixed timestep accumulator pattern to ensure
        deterministic game logic updates.

        The loop will:
        1. Measure elapsed time
        2. Accumulate time
        3. Update game logic in fixed timesteps
        4. Handle input and events
        5. Report performance metrics

        Example:
            >>> loop = GameLoop(context)
            >>> loop.run()  # Runs until stop() called
        """
        if self.is_running:
            logger.warning("GameLoop already running")
            return

        self.is_running = True
        self._current_time = time.time()
        self._last_fps_report = self._current_time

        logger.info("GameLoop started")

        try:
            while self.is_running and not self._shutdown_requested:
                self._tick()
        finally:
            if self._shutdown_requested:
                logger.info("GameLoop shutting down gracefully...")
            logger.info(f"GameLoop stopped: {self._frame_count} frames, {self._tick_count} ticks")

    def _tick(self) -> None:
        """
        Execute one iteration of the game loop.

        This method:
        1. Calculates elapsed time since last tick
        2. Adds elapsed time to accumulator
        3. Updates game logic in fixed timesteps (while accumulator >= fixed_dt)
        4. Applies frame skip protection
        5. Reports performance metrics

        This is the core of the fixed timestep pattern.
        """
        # Measure elapsed time
        new_time = time.time()
        frame_time = new_time - self._current_time
        self._current_time = new_time

        # Add to accumulator
        self._accumulator += frame_time

        # Apply frame skip protection (prevent spiral of death)
        ticks_this_frame = 0

        # Update game logic in fixed timesteps
        while self._accumulator >= self.FIXED_TIMESTEP:
            # Check frame skip limit
            if ticks_this_frame >= self.MAX_FRAME_SKIP:
                logger.warning(
                    f"Frame skip limit reached: {self.MAX_FRAME_SKIP} ticks, "
                    f"accumulator={self._accumulator:.4f}s, discarding time"
                )
                # Discard accumulated time to prevent spiral of death
                self._accumulator = 0.0
                break

            # Update game logic with fixed timestep
            self._update(self.FIXED_TIMESTEP)

            # Subtract fixed timestep from accumulator
            self._accumulator -= self.FIXED_TIMESTEP

            # Track ticks
            self._tick_count += 1
            ticks_this_frame += 1

        # Track frames
        self._frame_count += 1

        # Report performance metrics
        self._report_performance()

    def _update(self, dt: float) -> None:
        """
        Update game logic with fixed delta time.

        This method is called once per game tick (60 Hz) with a fixed
        delta time of 16.67ms. This ensures deterministic game logic
        regardless of rendering performance.

        The method calls the registered state handler for the current
        game state (if one is registered).

        Args:
            dt: Fixed delta time (always FIXED_TIMESTEP = 16.67ms)
        """
        # Get current game state
        current_state = self.context.current_state

        # Call state-specific handler if registered
        if current_state in self._state_handlers:
            handler = self._state_handlers[current_state]
            handler(dt)
        # If no handler registered, do nothing (valid for Phase 1)

    def _report_performance(self) -> None:
        """
        Report performance metrics periodically.

        This method logs FPS and tick rate every few seconds for monitoring
        loop performance. Helps identify performance issues early.
        """
        current_time = time.time()
        elapsed_since_report = current_time - self._last_fps_report

        if elapsed_since_report >= self._fps_report_interval:
            # Calculate FPS (frames per second)
            fps = self._frame_count / elapsed_since_report

            # Calculate TPS (ticks per second, should be ~60)
            tps = self._tick_count / elapsed_since_report

            logger.info(
                f"Performance: FPS={fps:.2f}, TPS={tps:.2f}, accumulator={self._accumulator:.4f}s"
            )

            # Reset counters
            self._frame_count = 0
            self._tick_count = 0
            self._last_fps_report = current_time

    def stop(self) -> None:
        """
        Stop the game loop.

        This method signals the loop to stop after the current tick completes.
        The loop will exit gracefully and log final statistics.

        Example:
            >>> loop.run()  # In background thread
            >>> # ... later ...
            >>> loop.stop()  # Graceful shutdown
        """
        if not self.is_running:
            logger.warning("GameLoop not running")
            return

        self.is_running = False
        logger.info("GameLoop stop requested")

    @property
    def average_fps(self) -> float:
        """
        Calculate average FPS over the entire run.

        Returns:
            Average frames per second

        Note:
            This is calculated from the start of the loop, not just
            the last reporting interval.
        """
        if self._current_time == 0.0:
            return 0.0

        elapsed = time.time() - (self._current_time - self._accumulator)
        return self._frame_count / elapsed if elapsed > 0 else 0.0

    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (
            f"GameLoop(fps={self.target_fps}, running={self.is_running}, ticks={self._tick_count})"
        )

    def __str__(self) -> str:
        """User-friendly string representation."""
        status = "running" if self.is_running else "stopped"
        return f"Game Loop: {status} (target: {self.target_fps} FPS)"
