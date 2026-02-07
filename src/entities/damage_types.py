"""
Damage types for combat system.

This module defines all damage types used in the combat system,
including physical and elemental types. These are used for:
- Type effectiveness (weaknesses)
- Shield breaking mechanics
- Damage calculations
"""

from enum import Enum, auto


class DamageType(Enum):
    """
    Damage types for combat actions.

    Used to determine type effectiveness against enemy weaknesses
    and for breaking enemy shields in the Break System.
    """

    # Physical damage
    PHYSICAL = auto()

    # Elemental damage types
    FIRE = auto()
    ICE = auto()
    LIGHTNING = auto()
    WIND = auto()
    LIGHT = auto()
    DARK = auto()

    def __str__(self) -> str:
        """Return human-readable damage type name."""
        return self.name.capitalize()
