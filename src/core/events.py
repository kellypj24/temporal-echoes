"""Event sourcing data structures for Temporal Echoes.

This module defines the core event types used throughout the game.
All state changes are captured as immutable events following the
event sourcing pattern (Constitution Principle #1).

Event Schema Evolution:
- Phase 1: Simple event storage with JSON data
- Phase 2+: Typed event classes with validation
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class GameEvent:
    """
    Immutable game event for event sourcing.

    Events are the single source of truth for all game state. They are
    append-only and never modified after creation (Constitution Principle #11).

    Attributes:
        event_id: Unique identifier for this event (UUID)
        event_timestamp: Unix timestamp (float) for precise ordering
        session_id: Game session identifier (one playthrough)
        timeline_id: Top-level timeline / save slot (currently always "main")
        branch_id: Combat-local rewind branch (0 = original line, increments per rewind)
        event_type: Type of event (e.g., "PlayerMoved", "CombatStarted")
        aggregate_id: Entity identifier (player_id, enemy_id, item_id)
        aggregate_type: Entity type (e.g., "player", "combat", "inventory")
        event_data: JSON string with event-specific data
        metadata: JSON string with additional context (user_agent, version, etc.)

    Schema Design:
        - JSON columns (event_data, metadata) provide flexibility for schema evolution
        - aggregate_id + aggregate_type prepare for CQRS read models (Phase 2+)
        - Unix timestamp (float) ensures microsecond precision for ordering

    Examples:
        >>> event = GameEvent(
        ...     event_type="PlayerMoved",
        ...     aggregate_id="player_001",
        ...     aggregate_type="player",
        ...     event_data='{"x": 10, "y": 20, "area": "forest"}',
        ...     session_id="sess_001",
        ...     timeline_id="main"
        ... )
        >>> event.event_id  # Auto-generated UUID
        'evt_...'
        >>> event.event_timestamp  # Auto-generated timestamp
        1732492800.123456
    """

    # Core identification
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    event_timestamp: float = field(default_factory=lambda: datetime.now(UTC).timestamp())

    # Session and timeline tracking
    session_id: str = ""
    timeline_id: str = ""
    branch_id: int = 0

    # Event classification
    event_type: str = ""
    aggregate_id: str | None = None
    aggregate_type: str | None = None

    # Event payload (JSON)
    event_data: str = "{}"
    metadata: str = "{}"

    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.timeline_id:
            raise ValueError("timeline_id is required")
        if not self.event_type:
            raise ValueError("event_type is required")

    def to_dict(self) -> dict:
        """
        Convert event to dictionary for SQLite insertion.

        Returns:
            Dictionary with all event fields
        """
        return {
            "event_id": self.event_id,
            "event_timestamp": self.event_timestamp,
            "session_id": self.session_id,
            "timeline_id": self.timeline_id,
            "branch_id": self.branch_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "event_data": self.event_data,
            "metadata": self.metadata,
        }


# Common event types (will expand in future phases)
class EventTypes:
    """
    Event type constants for type safety.

    These will expand significantly in future phases as we add
    combat, inventory, timeline branching, etc.
    """

    # System events
    GAME_START = "GameStart"
    GAME_END = "GameEnd"

    # State transitions (Phase 1)
    STATE_TRANSITION = "StateTransition"

    # Player events (Phase 2+)
    PLAYER_MOVED = "PlayerMoved"
    PLAYER_LEVEL_UP = "PlayerLevelUp"

    # Combat events (Phase 2)
    COMBAT_STARTED = "CombatStarted"
    COMBAT_ENDED = "CombatEnded"
    TURN_STARTED = "TurnStarted"
    ACTION_EXECUTED = "ActionExecuted"
    SHIELD_BROKEN = "ShieldBroken"
    BOOST_POINT_GAINED = "BoostPointGained"
    COMBATANT_DEFEATED = "CombatantDefeated"
    COMBAT_FLED = "CombatFled"

    # Timeline events (Phase 3)
    TIMELINE_CREATED = "TimelineCreated"
    TIMELINE_BRANCHED = "TimelineBranched"
    ECHO_STONE_USED = "EchoStoneUsed"
    CHARGE_SPENT = "ChargeSpent"
    CHARGE_REGENERATED = "ChargeRegenerated"
    TEMPORAL_REWIND = "TemporalRewind"
    ECHO_SPAWNED = "EchoSpawned"
    ECHO_ACTED = "EchoActed"
    COUNTER_STOP_TRIGGERED = "CounterStopTriggered"


# Event types whose effects are undone by a rewind.
# Persistent event types (everything else) emit and remain — they affect
# meta-state like XP, loot, and quest counters that survive cross-timeline.
# See assignments/active/phase-3-timeline-mechanics/DESIGN.md for the full table.
_REWINDABLE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        EventTypes.TURN_STARTED,
        EventTypes.ACTION_EXECUTED,
        EventTypes.SHIELD_BROKEN,
        EventTypes.BOOST_POINT_GAINED,
        EventTypes.ECHO_STONE_USED,
        EventTypes.CHARGE_SPENT,
        EventTypes.CHARGE_REGENERATED,
        EventTypes.ECHO_SPAWNED,
        EventTypes.ECHO_ACTED,
    }
)


def is_rewindable(event_type: str) -> bool:
    """
    Whether an event type's effects are undone by a temporal rewind.

    Rewindable events are combat-local: HP changes, turn flow, charge spend,
    echo actions. Replay rebuilds them on the new branch.

    Persistent events (everything else) are historical facts that survive
    rewinds: loot, XP, quest progress, combat outcomes, and the rewind
    actions themselves. They emit once and stay applied across branches.

    Args:
        event_type: Event type string (matches an EventTypes constant)

    Returns:
        True if the event is combat-local rewindable, False if persistent
    """
    return event_type in _REWINDABLE_EVENT_TYPES
