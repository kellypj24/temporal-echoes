# Prompt: Implement SQLite Event Store

**Phase**: 1 - Core Game Loop  
**Step**: 1  
**Supervisors**: @architect-supervisor @data-worker

## Context
We're building the foundational event store for Temporal Echoes RPG. This will be the single source of truth for all game state, enabling timeline branching and replay functionality.

## Task
Implement the SQLite-based event store with the following requirements:

### 1. Event Store Class (`src/core/persistence.py`)
```python
class EventStore:
    """SQLite event store with ACID guarantees."""
    
    def __init__(self, db_path: str = "data/events.db"):
        """Initialize database connection and schema."""
        pass
    
    def append_event(self, event: GameEvent) -> None:
        """Append event to immutable log."""
        pass
    
    def get_events_by_timeline(
        self,
        timeline_id: str,
        start_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[GameEvent]:
        """Retrieve events for a timeline."""
        pass
    
    def create_timeline(
        self,
        parent_timeline_id: Optional[str],
        divergence_event_id: str,
        timeline_name: Optional[str] = None
    ) -> str:
        """Create new timeline branch."""
        pass
```

### 2. Game Event Dataclass (`src/core/events.py`)
```python
@dataclass
class GameEvent:
    """Immutable game event for sourcing."""
    event_id: str
    event_timestamp: datetime
    session_id: str
    timeline_id: str
    event_type: str
    player_id: str
    state_before: dict
    player_action: str
    ai_response: Optional[str]
    outcome: dict
    metadata: Optional[dict] = None
```

### 3. Database Schema
```sql
CREATE TABLE game_events (
    event_id TEXT PRIMARY KEY,
    event_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT NOT NULL,
    timeline_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    player_id TEXT NOT NULL,
    state_before TEXT NOT NULL,  -- JSON
    player_action TEXT NOT NULL,
    ai_response TEXT,
    outcome TEXT NOT NULL,  -- JSON
    metadata TEXT,  -- JSON
    
    INDEX idx_session (session_id, event_timestamp),
    INDEX idx_timeline (timeline_id, event_timestamp),
    INDEX idx_event_type (event_type, event_timestamp)
);

CREATE TABLE timelines (
    timeline_id TEXT PRIMARY KEY,
    parent_timeline_id TEXT,
    divergence_point_event_id TEXT NOT NULL,
    divergence_timestamp DATETIME NOT NULL,
    timeline_name TEXT,
    is_active BOOLEAN DEFAULT 1,
    
    FOREIGN KEY (parent_timeline_id) REFERENCES timelines(timeline_id),
    FOREIGN KEY (divergence_point_event_id) REFERENCES game_events(event_id)
);
```

## Success Criteria
- [ ] All type hints present
- [ ] Docstrings on all public methods (Google style)
- [ ] ACID guarantees using transactions
- [ ] Proper error handling (no bare except)
- [ ] Unit tests with >= 80% coverage
- [ ] Can store and retrieve 1000 events without errors
- [ ] No linting errors
- [ ] Type checking passes

## Reference
- See: `.cursor/rules/data-worker.mdc` for SQLite patterns
- See: `.cursor/rules/architect-supervisor.mdc` for dependency injection
- See: `assignments/active/phase-1-core-game-loop/PLAN.md` Step 1

## Test Cases
```python
def test_append_event_stores_correctly():
    """Test that events are stored and can be retrieved."""
    pass

def test_timeline_creation():
    """Test creating new timeline branches."""
    pass

def test_concurrent_writes():
    """Test that concurrent writes don't corrupt data."""
    pass

def test_event_ordering():
    """Test that events are retrieved in correct order."""
    pass
```

## Common Pitfalls to Avoid
- ❌ Don't use mutable default arguments
- ❌ Don't skip transaction safety
- ❌ Don't forget to close connections
- ❌ Don't use bare except clauses
- ❌ Don't skip type hints

## Example Usage
```python
# Initialize
store = EventStore("data/events.db")

# Create event
event = GameEvent(
    event_id=str(uuid.uuid4()),
    event_timestamp=datetime.utcnow(),
    session_id="session_123",
    timeline_id="timeline_main",
    event_type="state_transition",
    player_id="player_1",
    state_before={"state": "MENU"},
    player_action="start_game",
    ai_response=None,
    outcome={"new_state": "EXPLORING"},
    metadata=None
)

# Store event
store.append_event(event)

# Retrieve events
events = store.get_events_by_timeline("timeline_main")
```

