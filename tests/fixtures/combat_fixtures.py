"""
Test fixtures for combat integration tests.

Provides factory functions for common combat setups used across
integration tests.
"""

import pytest

from src.core.combat import CombatContext
from src.core.persistence import EventStore
from src.entities import Enemy, Player

from .entity_fixtures import create_test_enemy, create_test_player


def create_combat_context(
    combat_id: str = "combat_001",
    seed: int = 42,
    player: Player | None = None,
    enemies: list[Enemy] | None = None,
    event_store: EventStore | None = None,
    session_id: str = "sess_001",
    timeline_id: str = "timeline_main",
) -> CombatContext:
    """
    Create a CombatContext with sensible defaults.

    Args:
        combat_id: Unique combat identifier.
        seed: RNG seed for deterministic replay.
        player: Player instance (default: standard test player).
        enemies: List of enemies (default: single test enemy).
        event_store: EventStore instance (default: in-memory).
        session_id: Session identifier.
        timeline_id: Timeline identifier.

    Returns:
        Configured CombatContext ready for testing.
    """
    if player is None:
        player = create_test_player()
    if enemies is None:
        enemies = [create_test_enemy()]
    if event_store is None:
        event_store = EventStore(":memory:")

    return CombatContext(
        combat_id=combat_id,
        seed=seed,
        player=player,
        enemies=enemies,
        event_store=event_store,
        session_id=session_id,
        timeline_id=timeline_id,
    )


def create_1v1_context(
    seed: int = 42,
    event_store: EventStore | None = None,
) -> CombatContext:
    """
    Create a simple 1v1 combat context.

    Args:
        seed: RNG seed for deterministic replay.
        event_store: EventStore instance (default: in-memory).

    Returns:
        CombatContext with one player vs one enemy.
    """
    return create_combat_context(seed=seed, event_store=event_store)


def create_1v3_context(
    seed: int = 42,
    event_store: EventStore | None = None,
) -> CombatContext:
    """
    Create a 1v3 multi-enemy combat context.

    Args:
        seed: RNG seed for deterministic replay.
        event_store: EventStore instance (default: in-memory).

    Returns:
        CombatContext with one player vs three enemies.
    """
    enemies = [
        create_test_enemy(id="enemy_1", name="Goblin A", speed=30, archetype="aggressive"),
        create_test_enemy(id="enemy_2", name="Goblin B", speed=25, archetype="defensive"),
        create_test_enemy(id="enemy_3", name="Goblin C", speed=35, archetype="berserker"),
    ]
    return create_combat_context(seed=seed, enemies=enemies, event_store=event_store)


@pytest.fixture
def event_store() -> EventStore:
    """Pytest fixture for an in-memory event store."""
    return EventStore(":memory:")


@pytest.fixture
def combat_context(event_store: EventStore) -> CombatContext:
    """Pytest fixture for a standard 1v1 combat context."""
    return create_combat_context(event_store=event_store)
