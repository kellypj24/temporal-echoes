"""Event store persistence layer using SQLite.

This module implements the event store for event sourcing architecture.
All game state is derived from an append-only log of immutable events
stored in SQLite (Constitution Principles #1, #11, #12).

Architecture Decision Records:
- DEC-0001: SQLite with WAL mode for event store
- DEC-0004: Hybrid CQRS (Phase 2+: read models + dbt analytics)

Performance Targets:
- < 10ms p95 latency for event writes
- Handle 60 events/second (worst case: 60 FPS with event per frame)
"""

import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from .events import GameEvent

logger = logging.getLogger(__name__)


class EventStore:
    """
    SQLite-based event store with ACID guarantees.

    This class manages the persistent event log that serves as the single
    source of truth for all game state. Events are append-only and never
    modified (Constitution Principle #11).

    Schema Design (DEC-0001, DEC-0004):
        - Single game_events table with JSON columns
        - Indexes on timeline_id, session_id, event_timestamp
        - aggregate_id + aggregate_type for future CQRS read models
        - WAL mode for better concurrency

    Usage:
        >>> store = EventStore("data/events.db")
        >>> event = GameEvent(
        ...     event_type="PlayerMoved",
        ...     session_id="sess_001",
        ...     timeline_id="main",
        ...     event_data='{"x": 10, "y": 20}'
        ... )
        >>> store.append_event(event)
        >>> events = store.get_events_by_timeline("main")
    """

    def __init__(self, db_path: str):
        """
        Initialize event store with SQLite database.

        Args:
            db_path: Path to SQLite database file (or ":memory:" for in-memory)

        Raises:
            sqlite3.Error: If database initialization fails
        """
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

        # Create database directory if needed (unless in-memory)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection and schema
        self._init_connection()
        self._init_schema()

        logger.info(f"EventStore initialized: {db_path}")

    def _init_connection(self) -> None:
        """Initialize SQLite connection with WAL mode."""
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # Allow use across threads (with caution)
        )

        # Enable WAL mode for better concurrency (DEC-0001)
        self._conn.execute("PRAGMA journal_mode=WAL")

        # Enable foreign keys (not used yet, but good practice)
        self._conn.execute("PRAGMA foreign_keys=ON")

        # Use Row factory for dict-like access
        self._conn.row_factory = sqlite3.Row

        logger.debug("SQLite connection initialized with WAL mode")

    def _init_schema(self) -> None:
        """
        Create game_events table and indexes.

        Schema follows DEC-0001 and DEC-0004 (Hybrid CQRS):
        - JSON columns for flexibility
        - aggregate_id/type for future read models
        - Indexes for timeline queries
        """
        assert self._conn is not None, "Connection must be initialized"
        with self._transaction():
            # Main events table
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS game_events (
                    event_id TEXT PRIMARY KEY,
                    event_timestamp REAL NOT NULL,
                    session_id TEXT NOT NULL,
                    timeline_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    aggregate_id TEXT,
                    aggregate_type TEXT,
                    event_data TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """
            )

            # Indexes for fast timeline queries
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timeline_id
                ON game_events(timeline_id, event_timestamp)
            """
            )

            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_id
                ON game_events(session_id)
            """
            )

            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_event_type
                ON game_events(event_type)
            """
            )

            # Index for CQRS aggregates (Phase 2+)
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_aggregate
                ON game_events(aggregate_id, aggregate_type)
            """
            )

        logger.debug("Event store schema initialized")

    @contextmanager
    def _transaction(self) -> Generator[None]:
        """
        Context manager for transactions (Constitution Principle #12).

        Ensures ACID guarantees for multi-step operations.

        Usage:
            >>> with store._transaction():
            ...     store._conn.execute(...)
            ...     store._conn.execute(...)
        """
        assert self._conn is not None, "Connection not initialized"
        try:
            yield None
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise

    def append_event(self, event: GameEvent) -> None:
        """
        Append event to the event log (append-only, no updates).

        Args:
            event: GameEvent to persist

        Raises:
            sqlite3.IntegrityError: If event_id already exists
            ValueError: If event is invalid

        Performance:
            Target < 10ms p95 latency (DEC-0001)
        """
        assert self._conn is not None, "Connection not initialized"
        if not isinstance(event, GameEvent):
            raise ValueError(f"Expected GameEvent, got {type(event)}")

        with self._transaction():
            self._conn.execute(
                """
                INSERT INTO game_events (
                    event_id, event_timestamp, session_id, timeline_id,
                    event_type, aggregate_id, aggregate_type,
                    event_data, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_timestamp,
                    event.session_id,
                    event.timeline_id,
                    event.event_type,
                    event.aggregate_id,
                    event.aggregate_type,
                    event.event_data,
                    event.metadata,
                ),
            )

        logger.debug(f"Event appended: {event.event_id} ({event.event_type})")

    def get_events_by_timeline(
        self, timeline_id: str, limit: int | None = None
    ) -> list[GameEvent]:
        """
        Retrieve all events for a specific timeline, ordered chronologically.

        Args:
            timeline_id: Timeline identifier
            limit: Optional limit on number of events (for testing)

        Returns:
            List of GameEvent objects in chronological order

        Performance:
            Fast due to idx_timeline_id index on (timeline_id, event_timestamp)
        """
        assert self._conn is not None, "Connection not initialized"
        query = """
            SELECT * FROM game_events
            WHERE timeline_id = ?
            ORDER BY event_timestamp ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor = self._conn.execute(query, (timeline_id,))
        rows = cursor.fetchall()

        events = []
        for row in rows:
            event = GameEvent(
                event_id=row["event_id"],
                event_timestamp=row["event_timestamp"],
                session_id=row["session_id"],
                timeline_id=row["timeline_id"],
                event_type=row["event_type"],
                aggregate_id=row["aggregate_id"],
                aggregate_type=row["aggregate_type"],
                event_data=row["event_data"],
                metadata=row["metadata"],
            )
            events.append(event)

        logger.debug(f"Retrieved {len(events)} events for timeline: {timeline_id}")
        return events

    def get_events_by_session(
        self, session_id: str, limit: int | None = None
    ) -> list[GameEvent]:
        """
        Retrieve all events for a game session (across all timelines).

        Args:
            session_id: Session identifier
            limit: Optional limit on number of events

        Returns:
            List of GameEvent objects in chronological order
        """
        assert self._conn is not None, "Connection not initialized"
        query = """
            SELECT * FROM game_events
            WHERE session_id = ?
            ORDER BY event_timestamp ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor = self._conn.execute(query, (session_id,))
        rows = cursor.fetchall()

        events = []
        for row in rows:
            event = GameEvent(
                event_id=row["event_id"],
                event_timestamp=row["event_timestamp"],
                session_id=row["session_id"],
                timeline_id=row["timeline_id"],
                event_type=row["event_type"],
                aggregate_id=row["aggregate_id"],
                aggregate_type=row["aggregate_type"],
                event_data=row["event_data"],
                metadata=row["metadata"],
            )
            events.append(event)

        logger.debug(f"Retrieved {len(events)} events for session: {session_id}")
        return events

    def get_event_count(self, timeline_id: str | None = None) -> int:
        """
        Get total event count (optionally filtered by timeline).

        Args:
            timeline_id: Optional timeline filter

        Returns:
            Total number of events
        """
        assert self._conn is not None, "Connection not initialized"
        if timeline_id:
            cursor = self._conn.execute(
                "SELECT COUNT(*) as count FROM game_events WHERE timeline_id = ?",
                (timeline_id,),
            )
        else:
            cursor = self._conn.execute("SELECT COUNT(*) as count FROM game_events")

        result = cursor.fetchone()
        return int(result["count"])

    def create_timeline(
        self,
        new_timeline_id: str,
        source_timeline_id: str,
        session_id: str,
        branch_point_timestamp: float | None = None,
    ) -> int:
        """
        Create a new timeline by copying events from a source timeline.

        This enables timeline branching for time-travel mechanics (Phase 3+).
        Events are copied up to the branch point, then new events can diverge.

        Args:
            new_timeline_id: ID for the new timeline branch
            source_timeline_id: Timeline to branch from
            session_id: Session identifier (same as source)
            branch_point_timestamp: Optional timestamp to branch from (defaults to latest)

        Returns:
            Number of events copied to new timeline

        Raises:
            ValueError: If timelines don't exist or invalid parameters
        """
        # Get events to copy
        source_events = self.get_events_by_timeline(source_timeline_id)

        if not source_events:
            raise ValueError(f"Source timeline not found: {source_timeline_id}")

        # Filter to branch point if specified
        if branch_point_timestamp:
            source_events = [
                e for e in source_events if e.event_timestamp <= branch_point_timestamp
            ]

        # Copy events to new timeline
        assert self._conn is not None, "Connection not initialized"
        with self._transaction():
            for event in source_events:
                # Create new event with same data but different timeline_id
                new_event = GameEvent(
                    event_id=f"evt_{event.event_id.split('_')[1]}_branch",  # New ID
                    event_timestamp=event.event_timestamp,
                    session_id=session_id,
                    timeline_id=new_timeline_id,  # New timeline
                    event_type=event.event_type,
                    aggregate_id=event.aggregate_id,
                    aggregate_type=event.aggregate_type,
                    event_data=event.event_data,
                    metadata=event.metadata,
                )

                self._conn.execute(
                    """
                    INSERT INTO game_events (
                        event_id, event_timestamp, session_id, timeline_id,
                        event_type, aggregate_id, aggregate_type,
                        event_data, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_event.event_id,
                        new_event.event_timestamp,
                        new_event.session_id,
                        new_event.timeline_id,
                        new_event.event_type,
                        new_event.aggregate_id,
                        new_event.aggregate_type,
                        new_event.event_data,
                        new_event.metadata,
                    ),
                )

        logger.info(
            f"Timeline created: {new_timeline_id} "
            f"(branched from {source_timeline_id}, {len(source_events)} events copied)"
        )
        return len(source_events)

    def close(self) -> None:
        """Close database connection gracefully."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("EventStore connection closed")

    def __enter__(self) -> "EventStore":
        """Context manager support."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager cleanup."""
        self.close()
