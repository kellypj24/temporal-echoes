"""
Authored game content: encounters, enemy rosters, and tuning.

Content is declarative data (specs) rather than live objects, so an
encounter can be inspected, listed, and re-instantiated deterministically
without touching combat internals. `build()` is the only place specs
become entities.
"""

from .encounters import (
    DEFAULT_ENCOUNTER_ID,
    ENCOUNTERS,
    Encounter,
    EnemySpec,
    PlayerSpec,
    get_encounter,
    list_encounters,
)

__all__ = [
    "DEFAULT_ENCOUNTER_ID",
    "ENCOUNTERS",
    "Encounter",
    "EnemySpec",
    "PlayerSpec",
    "get_encounter",
    "list_encounters",
]
