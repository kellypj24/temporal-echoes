"""Temporal Echoes - 16-bit RPG with AI Dungeon Master.

This is the main entry point for Phase 1. It demonstrates the core game loop
with fixed timestep, event sourcing, and state management.

Phase 1 is architecture-focused with no rendering - console output only.
"""

import logging
import sys
from collections.abc import Callable

from src.core.game_context import GameContext
from src.core.game_loop import GameLoop
from src.core.state_machine import GameState

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def create_demo_handlers(
    context: GameContext,
) -> dict[GameState, "Callable[[float], None]"]:
    """
    Create simple demo handlers for each game state.

    These handlers demonstrate the game loop calling state-specific
    update logic. In Phase 2+, these will be replaced with actual
    game mechanics (player movement, combat, etc.).

    Args:
        context: GameContext for state transitions

    Returns:
        Dictionary mapping GameState to handler functions
    """
    tick_count = {"count": 0}  # Mutable counter for closures

    def menu_handler(_dt: float) -> None:
        """Handle MENU state updates."""
        tick_count["count"] += 1

        # After 3 seconds (180 ticks), transition to EXPLORING
        if tick_count["count"] >= 180:
            logger.info("🎮 Demo: Transitioning from MENU to EXPLORING")
            context.transition_to(GameState.EXPLORING, {"reason": "demo_flow"})
            tick_count["count"] = 0

    def exploring_handler(_dt: float) -> None:
        """Handle EXPLORING state updates."""
        tick_count["count"] += 1

        # After 5 seconds (300 ticks), transition to COMBAT
        if tick_count["count"] >= 300:
            logger.info("⚔️  Demo: Transitioning from EXPLORING to COMBAT")
            context.transition_to(GameState.COMBAT, {"enemy": "Demo Enemy"})
            tick_count["count"] = 0

    def combat_handler(_dt: float) -> None:
        """Handle COMBAT state updates."""
        tick_count["count"] += 1

        # After 5 seconds, transition back to EXPLORING
        if tick_count["count"] >= 300:
            logger.info("✅ Demo: Transitioning from COMBAT to EXPLORING")
            context.transition_to(GameState.EXPLORING, {"result": "victory"})
            tick_count["count"] = 0

    # Register handlers
    return {
        GameState.MENU: menu_handler,
        GameState.EXPLORING: exploring_handler,
        GameState.COMBAT: combat_handler,
    }


def main() -> None:
    """
    Main entry point for Temporal Echoes (Phase 1).

    This demonstrates the core architecture:
    - GameContext coordinates EventStore and StateMachine
    - GameLoop runs at fixed 60 Hz
    - State handlers update game logic
    - Event sourcing tracks all state changes
    - Graceful shutdown on Ctrl+C

    Phase 1 goals:
    - Prove architecture works
    - Test event sourcing
    - Validate fixed timestep
    - No rendering (console only)
    """
    logger.info("=" * 60)
    logger.info("🎮 Temporal Echoes - Phase 1 Demo")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Architecture Demo:")
    logger.info("  • Fixed timestep game loop (60 Hz)")
    logger.info("  • Event sourcing with SQLite")
    logger.info("  • State machine (MENU → EXPLORING → COMBAT)")
    logger.info("  • Graceful shutdown (Ctrl+C to stop)")
    logger.info("")
    logger.info("Phase 1: No rendering - console output only")
    logger.info("=" * 60)
    logger.info("")

    try:
        # Create GameContext with in-memory database for demo
        logger.info("Initializing game context...")
        context = GameContext.create(
            ":memory:",
            session_id="demo_session",
            timeline_id="demo_timeline",
        )

        # Create GameLoop
        logger.info("Initializing game loop...")
        loop = GameLoop(context, target_fps=60)

        # Register demo handlers
        logger.info("Registering state handlers...")
        handlers = create_demo_handlers(context)
        for state, handler in handlers.items():
            loop.register_state_handler(state, handler)

        # Setup signal handlers for graceful shutdown
        loop.setup_signal_handlers()

        logger.info("")
        logger.info("🚀 Starting game loop...")
        logger.info("   (Press Ctrl+C to stop)")
        logger.info("")

        # Run the game loop
        loop.run()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Cleanup
        logger.info("")
        logger.info("=" * 60)
        logger.info("Shutting down...")

        # Close context (emits GAME_END event)
        if "context" in locals():
            context.close()

        logger.info("✅ Demo complete!")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
