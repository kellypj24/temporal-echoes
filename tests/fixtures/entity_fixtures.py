"""
Test fixtures for combat entities.

Provides factory functions to create test instances of Player and Enemy
entities with reasonable default values.
"""

import pytest

from src.entities import DamageType, Enemy, Player


def create_test_player(
    id: str = "player_1",
    name: str = "Hero",
    level: int = 10,
    hp: int = 300,
    max_hp: int = 300,
    attack: int = 50,
    defense: int = 30,
    speed: int = 40,
    boost_points: int = 0,
    max_boost_points: int = 5,
    temporal_charge: int = 0,
    max_temporal_charge: int = 3,
) -> Player:
    """
    Create a test Player instance with default values.

    Args:
        id: Unique identifier
        name: Player name
        level: Character level
        hp: Current HP
        max_hp: Maximum HP
        attack: Attack stat
        defense: Defense stat
        speed: Speed stat
        boost_points: Current BP
        max_boost_points: Maximum BP
        temporal_charge: Starting temporal charge (default 0)
        max_temporal_charge: Maximum temporal charge (default 3)

    Returns:
        Configured Player instance
    """
    return Player(
        id=id,
        name=name,
        level=level,
        hp=hp,
        max_hp=max_hp,
        attack=attack,
        defense=defense,
        speed=speed,
        boost_points=boost_points,
        max_boost_points=max_boost_points,
        temporal_charge=temporal_charge,
        max_temporal_charge=max_temporal_charge,
    )


def create_test_enemy(
    id: str = "enemy_1",
    name: str = "Goblin",
    level: int = 8,
    hp: int = 200,
    max_hp: int = 200,
    attack: int = 40,
    defense: int = 25,
    speed: int = 30,
    shield_points: int = 3,
    max_shield_points: int = 3,
    weaknesses: list[DamageType] | None = None,
    is_broken: bool = False,
    break_turns_remaining: int = 0,
    archetype: str = "aggressive",
    temporal_charge: int = 0,
    max_temporal_charge: int = 3,
) -> Enemy:
    """
    Create a test Enemy instance with default values.

    Args:
        id: Unique identifier
        name: Enemy name
        level: Enemy level
        hp: Current HP
        max_hp: Maximum HP
        attack: Attack stat
        defense: Defense stat
        speed: Speed stat
        shield_points: Current shield strength
        max_shield_points: Maximum shield strength
        weaknesses: List of weakness damage types (default: FIRE, ICE)
        archetype: AI archetype name
        temporal_charge: Starting temporal charge (default 0)
        max_temporal_charge: Maximum temporal charge (default 3)

    Returns:
        Configured Enemy instance
    """
    if weaknesses is None:
        weaknesses = [DamageType.FIRE, DamageType.ICE]

    return Enemy(
        id=id,
        name=name,
        level=level,
        hp=hp,
        max_hp=max_hp,
        attack=attack,
        defense=defense,
        speed=speed,
        shield_points=shield_points,
        max_shield_points=max_shield_points,
        weaknesses=weaknesses,
        is_broken=is_broken,
        break_turns_remaining=break_turns_remaining,
        archetype=archetype,
        temporal_charge=temporal_charge,
        max_temporal_charge=max_temporal_charge,
    )


@pytest.fixture
def player() -> Player:
    """Pytest fixture for a standard test player."""
    return create_test_player()


@pytest.fixture
def enemy() -> Enemy:
    """Pytest fixture for a standard test enemy."""
    return create_test_enemy()


@pytest.fixture
def boss_enemy() -> Enemy:
    """Pytest fixture for a boss enemy with higher stats."""
    return create_test_enemy(
        id="boss_1",
        name="Dragon",
        level=20,
        hp=1000,
        max_hp=1000,
        attack=80,
        defense=50,
        speed=35,
        shield_points=5,
        max_shield_points=5,
        weaknesses=[DamageType.ICE, DamageType.LIGHTNING],
        archetype="tactical",
    )
