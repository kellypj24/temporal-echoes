"""Reusable test fixtures for GameEvent testing.

Provides factory functions and sample data for unit tests.
"""

from src.core.events import GameEvent, EventTypes


def create_test_event(
    event_type: str = EventTypes.STATE_TRANSITION,
    session_id: str = "test_session",
    timeline_id: str = "test_timeline",
    aggregate_id: str = "test_aggregate",
    aggregate_type: str = "test",
    event_data: str = '{"test": true}',
    metadata: str = '{"test_meta": true}',
) -> GameEvent:
    """
    Factory function for creating test events.
    
    Args:
        event_type: Type of event (defaults to STATE_TRANSITION)
        session_id: Session identifier
        timeline_id: Timeline identifier
        aggregate_id: Aggregate identifier
        aggregate_type: Aggregate type
        event_data: JSON event data
        metadata: JSON metadata
    
    Returns:
        GameEvent with provided or default values
    """
    return GameEvent(
        event_type=event_type,
        session_id=session_id,
        timeline_id=timeline_id,
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        event_data=event_data,
        metadata=metadata,
    )


def create_player_moved_event(
    x: int = 10,
    y: int = 20,
    area: str = "forest",
    session_id: str = "test_session",
    timeline_id: str = "test_timeline",
) -> GameEvent:
    """Create a PlayerMoved event for testing."""
    return GameEvent(
        event_type=EventTypes.PLAYER_MOVED,
        session_id=session_id,
        timeline_id=timeline_id,
        aggregate_id="player_001",
        aggregate_type="player",
        event_data=f'{{"x": {x}, "y": {y}, "area": "{area}"}}',
        metadata='{"version": "1.0"}',
    )


def create_combat_event(
    action: str = "attack",
    target: str = "enemy_001",
    damage: int = 10,
    session_id: str = "test_session",
    timeline_id: str = "test_timeline",
) -> GameEvent:
    """Create a CombatAction event for testing."""
    return GameEvent(
        event_type=EventTypes.COMBAT_ACTION,
        session_id=session_id,
        timeline_id=timeline_id,
        aggregate_id="combat_001",
        aggregate_type="combat",
        event_data=f'{{"action": "{action}", "target": "{target}", "damage": {damage}}}',
        metadata='{"version": "1.0"}',
    )


def create_state_transition_event(
    from_state: str = "MENU",
    to_state: str = "EXPLORING",
    session_id: str = "test_session",
    timeline_id: str = "test_timeline",
) -> GameEvent:
    """Create a StateTransition event for testing."""
    return GameEvent(
        event_type=EventTypes.STATE_TRANSITION,
        session_id=session_id,
        timeline_id=timeline_id,
        aggregate_id="game_001",
        aggregate_type="game_state",
        event_data=f'{{"from": "{from_state}", "to": "{to_state}"}}',
        metadata='{"version": "1.0"}',
    )


# Sample event sequences for integration testing
def create_event_sequence(count: int = 10, session_id: str = "test_session", timeline_id: str = "test_timeline") -> list[GameEvent]:
    """Create a sequence of test events."""
    events = []
    
    # Game start
    events.append(GameEvent(
        event_type=EventTypes.GAME_START,
        session_id=session_id,
        timeline_id=timeline_id,
        aggregate_id="game_001",
        aggregate_type="game",
        event_data='{"started_at": "2025-11-24T00:00:00Z"}',
        metadata='{"version": "1.0"}',
    ))
    
    # State transitions
    transitions = [
        ("MENU", "EXPLORING"),
        ("EXPLORING", "COMBAT"),
        ("COMBAT", "EXPLORING"),
        ("EXPLORING", "DIALOGUE"),
        ("DIALOGUE", "EXPLORING"),
    ]
    
    for i, (from_state, to_state) in enumerate(transitions[:count-2]):
        events.append(create_state_transition_event(
            from_state=from_state,
            to_state=to_state,
            session_id=session_id,
            timeline_id=timeline_id,
        ))
    
    # Game end
    if len(events) < count:
        events.append(GameEvent(
            event_type=EventTypes.GAME_END,
            session_id=session_id,
            timeline_id=timeline_id,
            aggregate_id="game_001",
            aggregate_type="game",
            event_data='{"ended_at": "2025-11-24T01:00:00Z"}',
            metadata='{"version": "1.0"}',
        ))
    
    return events[:count]

