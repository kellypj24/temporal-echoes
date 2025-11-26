"""
Combat entities module.

This module provides entity classes for the combat system:
- Combatant: Abstract base class for all combat participants
- Player: Player character with Boost Point system
- Enemy: Enemy with Break System mechanics
- DamageType: Enum for damage types
- DamageResult: Result of damage calculations
"""

from .combatant import Combatant, DamageResult
from .damage_types import DamageType
from .enemy import Enemy
from .player import Player

__all__ = [
    "Combatant",
    "DamageResult",
    "DamageType",
    "Enemy",
    "Player",
]
