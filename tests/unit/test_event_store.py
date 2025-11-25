"""Unit tests for EventStore class.

Tests cover:
- Event appending and retrieval
- Timeline queries
- Session queries
- Timeline branching
- Transaction safety
- Error handling
- Performance characteristics

Constitution Principles Validated:
- #1: Event sourcing (append-only)
- #5: Test coverage (>= 80%)
- #11: Event immutability
- #12: Transaction safety
"""

import sqlite3

import pytest

from src.core.events import GameEvent
from src.core.persistence import EventStore
from tests.fixtures.event_fixtures import (
    create_event_sequence,
    create_test_event,
)

# Fixtures


@pytest.fixture
def in_memory_store():
    """Create an in-memory event store for fast testing."""
    store = EventStore(":memory:")
    yield store
    store.close()


@pytest.fixture
def temp_file_store(tmp_path):
    """Create a temporary file-based event store."""
    db_path = tmp_path / "test_events.db"
    store = EventStore(str(db_path))
    yield store
    store.close()


@pytest.fixture
def populated_store(in_memory_store):
    """Create an event store with sample data."""
    events = create_event_sequence(count=10, session_id="sess_001", timeline_id="main")
    for event in events:
        in_memory_store.append_event(event)
    return in_memory_store


# Test: Event Store Initialization


def test_in_memory_store_initialization():
    """Test that in-memory store initializes correctly."""
    store = EventStore(":memory:")
    assert store.db_path == ":memory:"
    assert store._conn is not None
    store.close()


def test_file_store_initialization(tmp_path):
    """Test that file-based store creates database file."""
    db_path = tmp_path / "test.db"
    store = EventStore(str(db_path))

    assert db_path.exists()
    assert store.db_path == str(db_path)
    store.close()


def test_store_creates_parent_directories(tmp_path):
    """Test that nested directories are created automatically."""
    db_path = tmp_path / "nested" / "dir" / "events.db"
    store = EventStore(str(db_path))

    assert db_path.exists()
    assert db_path.parent.exists()
    store.close()


def test_wal_mode_enabled(temp_file_store):
    """Test that WAL mode is enabled for file-based stores (DEC-0001).

    Note: In-memory databases use 'memory' journal mode, which is expected.
    WAL mode only applies to file-based SQLite databases.
    """
    cursor = temp_file_store._conn.execute("PRAGMA journal_mode")
    mode = cursor.fetchone()[0]
    assert mode.upper() == "WAL"


def test_schema_initialization(in_memory_store):
    """Test that schema is created with correct tables and indexes."""
    # Check game_events table exists
    cursor = in_memory_store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='game_events'"
    )
    assert cursor.fetchone() is not None

    # Check indexes exist
    cursor = in_memory_store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    )
    indexes = [row[0] for row in cursor.fetchall()]

    assert "idx_timeline_id" in indexes
    assert "idx_session_id" in indexes
    assert "idx_event_type" in indexes
    assert "idx_aggregate" in indexes


# Test: Event Appending


def test_append_single_event(in_memory_store):
    """Test appending a single event."""
    event = create_test_event()
    in_memory_store.append_event(event)

    # Verify event was stored
    count = in_memory_store.get_event_count()
    assert count == 1


def test_append_multiple_events(in_memory_store):
    """Test appending multiple events."""
    events = create_event_sequence(count=5)

    for event in events:
        in_memory_store.append_event(event)

    count = in_memory_store.get_event_count()
    assert count == 5


def test_append_event_with_all_fields(in_memory_store):
    """Test that all event fields are stored correctly."""
    event = GameEvent(
        event_type="TestEvent",
        session_id="sess_123",
        timeline_id="timeline_abc",
        aggregate_id="agg_456",
        aggregate_type="test_type",
        event_data='{"key": "value"}',
        metadata='{"meta": "data"}',
    )

    in_memory_store.append_event(event)

    # Retrieve and verify
    retrieved = in_memory_store.get_events_by_timeline("timeline_abc")
    assert len(retrieved) == 1

    r = retrieved[0]
    assert r.event_id == event.event_id
    assert r.event_timestamp == event.event_timestamp
    assert r.session_id == "sess_123"
    assert r.timeline_id == "timeline_abc"
    assert r.event_type == "TestEvent"
    assert r.aggregate_id == "agg_456"
    assert r.aggregate_type == "test_type"
    assert r.event_data == '{"key": "value"}'
    assert r.metadata == '{"meta": "data"}'


def test_append_event_duplicate_id_fails(in_memory_store):
    """Test that duplicate event IDs raise IntegrityError."""
    event1 = create_test_event()
    in_memory_store.append_event(event1)

    # Try to append event with same ID
    event2 = GameEvent(
        event_id=event1.event_id,  # Same ID
        event_type="DifferentEvent",
        session_id="sess_002",
        timeline_id="timeline_002",
    )

    with pytest.raises(sqlite3.IntegrityError):
        in_memory_store.append_event(event2)


def test_append_invalid_event_type_fails(in_memory_store):
    """Test that appending non-GameEvent raises ValueError."""
    with pytest.raises(ValueError, match="Expected GameEvent"):
        in_memory_store.append_event({"not": "an event"})


def test_events_are_immutable(in_memory_store):
    """Test that GameEvent dataclass is frozen (immutable)."""
    event = create_test_event()

    # Frozen dataclasses raise FrozenInstanceError (subclass of AttributeError)
    with pytest.raises((AttributeError, TypeError)):
        event.event_type = "ModifiedType"


# Test: Querying by Timeline


def test_get_events_by_timeline(populated_store):
    """Test retrieving events for a specific timeline."""
    events = populated_store.get_events_by_timeline("main")

    assert len(events) == 10
    assert all(e.timeline_id == "main" for e in events)


def test_get_events_by_timeline_chronological_order(populated_store):
    """Test that events are returned in chronological order."""
    events = populated_store.get_events_by_timeline("main")

    timestamps = [e.event_timestamp for e in events]
    assert timestamps == sorted(timestamps)


def test_get_events_by_timeline_with_limit(populated_store):
    """Test limiting the number of events returned."""
    events = populated_store.get_events_by_timeline("main", limit=5)

    assert len(events) == 5


def test_get_events_empty_timeline(in_memory_store):
    """Test querying a timeline with no events."""
    events = in_memory_store.get_events_by_timeline("nonexistent")

    assert events == []


def test_get_events_multiple_timelines(in_memory_store):
    """Test that different timelines are isolated."""
    # Add events to timeline A
    for _ in range(3):
        in_memory_store.append_event(create_test_event(timeline_id="timeline_a"))

    # Add events to timeline B
    for _ in range(5):
        in_memory_store.append_event(create_test_event(timeline_id="timeline_b"))

    events_a = in_memory_store.get_events_by_timeline("timeline_a")
    events_b = in_memory_store.get_events_by_timeline("timeline_b")

    assert len(events_a) == 3
    assert len(events_b) == 5
    assert all(e.timeline_id == "timeline_a" for e in events_a)
    assert all(e.timeline_id == "timeline_b" for e in events_b)


# Test: Querying by Session


def test_get_events_by_session(in_memory_store):
    """Test retrieving all events for a session (across timelines)."""
    # Add events for session 1 across two timelines
    for _ in range(3):
        in_memory_store.append_event(
            create_test_event(session_id="sess_001", timeline_id="main")
        )

    for _ in range(2):
        in_memory_store.append_event(
            create_test_event(session_id="sess_001", timeline_id="branch_1")
        )

    events = in_memory_store.get_events_by_session("sess_001")

    assert len(events) == 5
    assert all(e.session_id == "sess_001" for e in events)


def test_get_events_by_session_with_limit(populated_store):
    """Test limiting session query results."""
    events = populated_store.get_events_by_session("sess_001", limit=3)

    assert len(events) == 3


# Test: Event Count


def test_get_event_count_total(populated_store):
    """Test getting total event count."""
    count = populated_store.get_event_count()

    assert count == 10


def test_get_event_count_by_timeline(in_memory_store):
    """Test getting event count for specific timeline."""
    for _ in range(7):
        in_memory_store.append_event(create_test_event(timeline_id="main"))

    for _ in range(3):
        in_memory_store.append_event(create_test_event(timeline_id="branch"))

    count_main = in_memory_store.get_event_count(timeline_id="main")
    count_branch = in_memory_store.get_event_count(timeline_id="branch")
    count_total = in_memory_store.get_event_count()

    assert count_main == 7
    assert count_branch == 3
    assert count_total == 10


# Test: Timeline Branching


def test_create_timeline_basic(in_memory_store):
    """Test creating a new timeline by branching."""
    # Create source timeline with events
    events = create_event_sequence(count=5, timeline_id="main")
    for event in events:
        in_memory_store.append_event(event)

    # Branch to new timeline
    copied_count = in_memory_store.create_timeline(
        new_timeline_id="branch_1", source_timeline_id="main", session_id="sess_001"
    )

    assert copied_count == 5

    # Verify both timelines exist with same events
    main_events = in_memory_store.get_events_by_timeline("main")
    branch_events = in_memory_store.get_events_by_timeline("branch_1")

    assert len(main_events) == 5
    assert len(branch_events) == 5

    # Verify timeline IDs are different
    assert all(e.timeline_id == "main" for e in main_events)
    assert all(e.timeline_id == "branch_1" for e in branch_events)


def test_create_timeline_with_branch_point(in_memory_store):
    """Test branching at a specific point in time."""
    # Create source timeline with 10 events
    events = create_event_sequence(count=10, timeline_id="main")
    for event in events:
        in_memory_store.append_event(event)

    # Get timestamp of 5th event
    branch_point = events[4].event_timestamp

    # Branch at that point
    copied_count = in_memory_store.create_timeline(
        new_timeline_id="branch_1",
        source_timeline_id="main",
        session_id="sess_001",
        branch_point_timestamp=branch_point,
    )

    # Should only copy first 5 events
    assert copied_count == 5

    branch_events = in_memory_store.get_events_by_timeline("branch_1")
    assert len(branch_events) == 5


def test_create_timeline_invalid_source(in_memory_store):
    """Test that branching from nonexistent timeline fails."""
    with pytest.raises(ValueError, match="Source timeline not found"):
        in_memory_store.create_timeline(
            new_timeline_id="branch_1",
            source_timeline_id="nonexistent",
            session_id="sess_001",
        )


# Test: Transaction Safety


def test_transaction_commit_on_success(in_memory_store):
    """Test that transactions commit on success."""
    with in_memory_store._transaction():
        in_memory_store._conn.execute(
            "INSERT INTO game_events (event_id, event_timestamp, session_id, timeline_id, event_type, event_data, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test_id", 1.0, "sess", "timeline", "Test", "{}", "{}"),
        )

    # Verify committed
    count = in_memory_store.get_event_count()
    assert count == 1


def test_transaction_rollback_on_error(in_memory_store):
    """Test that transactions rollback on error."""
    # Add one event successfully
    in_memory_store.append_event(create_test_event())

    # Try to add two more in a transaction, but fail mid-way
    try:
        with in_memory_store._transaction():
            in_memory_store._conn.execute(
                "INSERT INTO game_events (event_id, event_timestamp, session_id, timeline_id, event_type, event_data, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("test_id2", 1.0, "sess", "timeline", "Test", "{}", "{}"),
            )

            # This should fail (duplicate event_id)
            in_memory_store._conn.execute(
                "INSERT INTO game_events (event_id, event_timestamp, session_id, timeline_id, event_type, event_data, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("test_id2", 1.0, "sess", "timeline", "Test", "{}", "{}"),  # Duplicate
            )
    except sqlite3.IntegrityError:
        pass

    # Should still only have 1 event (rollback happened)
    count = in_memory_store.get_event_count()
    assert count == 1


# Test: Context Manager


def test_context_manager_closes_connection():
    """Test that EventStore can be used as a context manager."""
    with EventStore(":memory:") as store:
        store.append_event(create_test_event())
        assert store._conn is not None

    # Connection should be closed after exiting context
    assert store._conn is None


# Test: Edge Cases


def test_empty_store_queries(in_memory_store):
    """Test querying an empty event store."""
    assert in_memory_store.get_event_count() == 0
    assert in_memory_store.get_events_by_timeline("any") == []
    assert in_memory_store.get_events_by_session("any") == []


def test_large_event_batch(in_memory_store):
    """Test appending a large number of events (performance check)."""
    import time

    start_time = time.perf_counter()

    # Append 1000 events
    for _ in range(1000):
        in_memory_store.append_event(create_test_event())

    elapsed = time.perf_counter() - start_time

    # Should complete in < 1 second (target < 10ms per write * 1000 = 10s worst case)
    assert elapsed < 1.0, f"Writing 1000 events took {elapsed}s (expected < 1s)"

    count = in_memory_store.get_event_count()
    assert count == 1000


def test_concurrent_timeline_writes(in_memory_store):
    """Test that different timelines can be written independently."""
    # This is a basic test; true concurrency would require threading
    for i in range(100):
        timeline = f"timeline_{i % 10}"  # 10 different timelines
        in_memory_store.append_event(create_test_event(timeline_id=timeline))

    # Verify all timelines have events
    for i in range(10):
        timeline = f"timeline_{i}"
        events = in_memory_store.get_events_by_timeline(timeline)
        assert len(events) == 10


# Test: GameEvent Validation


def test_game_event_requires_session_id():
    """Test that GameEvent requires session_id."""
    with pytest.raises(ValueError, match="session_id is required"):
        GameEvent(
            event_type="Test",
            session_id="",  # Empty
            timeline_id="timeline",
        )


def test_game_event_requires_timeline_id():
    """Test that GameEvent requires timeline_id."""
    with pytest.raises(ValueError, match="timeline_id is required"):
        GameEvent(
            event_type="Test",
            session_id="session",
            timeline_id="",  # Empty
        )


def test_game_event_requires_event_type():
    """Test that GameEvent requires event_type."""
    with pytest.raises(ValueError, match="event_type is required"):
        GameEvent(
            event_type="",  # Empty
            session_id="session",
            timeline_id="timeline",
        )


def test_game_event_auto_generates_id():
    """Test that event_id is auto-generated if not provided."""
    event1 = create_test_event()
    event2 = create_test_event()

    assert event1.event_id.startswith("evt_")
    assert event2.event_id.startswith("evt_")
    assert event1.event_id != event2.event_id


def test_game_event_auto_generates_timestamp():
    """Test that event_timestamp is auto-generated if not provided."""
    event = create_test_event()

    assert isinstance(event.event_timestamp, float)
    assert event.event_timestamp > 0


def test_game_event_to_dict():
    """Test GameEvent.to_dict() conversion."""
    event = create_test_event()
    event_dict = event.to_dict()

    assert isinstance(event_dict, dict)
    assert event_dict["event_id"] == event.event_id
    assert event_dict["event_type"] == event.event_type
    assert event_dict["session_id"] == event.session_id
    assert event_dict["timeline_id"] == event.timeline_id
