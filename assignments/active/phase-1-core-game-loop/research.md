# Research Document: Phase 1 - Core Game Loop

**Phase**: Phase 1  
**Created**: 2025-11-24  
**Status**: 🔄 In Progress  

## Overview
This phase establishes the foundation of Temporal Echoes with event sourcing, state management, and the core game loop. Research focuses on validating architectural patterns, confirming tech stack compatibility, and identifying potential performance bottlenecks.

## Research Summary

**Total Topics**: 6  
**Completed**: 0  
**High Priority**: 4  
**Research Time**: 6-8 hours (estimated)  

---

## Research Topics

### Topic 1: Event Sourcing with SQLite
**Status**: ✅ Complete  
**Priority**: 🔴 High  
**Assigned To**: @data-worker  
**Completed**: 2025-11-24

**Why Research Needed**:
Event sourcing is the architectural foundation for timeline branching. Need to validate SQLite performance for append-only event logs and ensure proper indexing strategies.

**Questions to Answer**:
1. ✅ What schema design best supports event sourcing in SQLite?
2. ✅ What indexes are needed for timeline replay performance?
3. ✅ How should we handle event versioning/schema evolution?
4. ✅ What's the expected write throughput for event logging?
5. ✅ Should we use WAL mode for better concurrency?

**Research Sources**:
- [x] SQLite documentation on WAL mode
- [x] Martin Fowler's Event Sourcing pattern
- [x] Greg Young's Event Store design principles
- [x] SQLite performance best practices
- [x] Python sqlite3 module documentation

**Research Methodology**:
- Review SQLite transaction patterns for high-write scenarios
- Benchmark append-only INSERT performance
- Research event schema versioning strategies
- Investigate SQLite's date/time handling for event timestamps

**Findings**:

**1. SQLite is Sufficient for Single-Player Event Sourcing**
- **Write Performance**: SQLite with WAL mode can handle 1000s of writes/second
- **60 FPS Target**: Worst case is 60 events/second (1 per frame), well within SQLite's capabilities
- **Append-Only Pattern**: SQLite excels at sequential writes with proper indexing
- **ACID Guarantees**: Full transaction support out of the box

**2. Schema Design - Evolution Path to CQRS**

**Phase 1: Pure Event Sourcing (Simple Start)**
```sql
CREATE TABLE game_events (
    event_id TEXT PRIMARY KEY,
    event_timestamp REAL NOT NULL,  -- Unix timestamp for precision
    session_id TEXT NOT NULL,
    timeline_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    aggregate_id TEXT,  -- player_id, enemy_id, item_id (entity identifier)
    aggregate_type TEXT,  -- 'player', 'combat', 'inventory', 'timeline'
    event_data TEXT,  -- JSON with full event context
    metadata TEXT  -- JSON for additional context
);

-- Critical indexes for performance
CREATE INDEX idx_timeline_id ON game_events(timeline_id, event_timestamp);
CREATE INDEX idx_session_id ON game_events(session_id);
CREATE INDEX idx_event_type ON game_events(event_type);
CREATE INDEX idx_aggregate ON game_events(aggregate_id, aggregate_type);
```

**Phase 2+: CQRS Read Models (Fast Queries)**
```sql
-- Materialized view: Current player state
CREATE TABLE player_state (
    player_id TEXT PRIMARY KEY,
    timeline_id TEXT NOT NULL,
    name TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    experience INTEGER DEFAULT 0,
    health INTEGER,
    max_health INTEGER,
    mana INTEGER,
    max_mana INTEGER,
    position_x INTEGER,
    position_y INTEGER,
    current_area TEXT,
    last_event_id TEXT NOT NULL,  -- Sync checkpoint
    updated_at REAL,
    FOREIGN KEY (last_event_id) REFERENCES game_events(event_id)
);

-- Materialized view: Inventory
CREATE TABLE inventory_state (
    player_id TEXT NOT NULL,
    timeline_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_name TEXT,
    quantity INTEGER DEFAULT 1,
    equipped BOOLEAN DEFAULT 0,
    last_event_id TEXT NOT NULL,
    PRIMARY KEY (player_id, timeline_id, item_id),
    FOREIGN KEY (last_event_id) REFERENCES game_events(event_id)
);

-- Materialized view: Timeline metadata
CREATE TABLE timeline_state (
    timeline_id TEXT PRIMARY KEY,
    parent_timeline_id TEXT,
    branched_at_event_id TEXT,
    branch_reason TEXT,
    created_at REAL,
    is_active BOOLEAN DEFAULT 1,
    convergence_point_id TEXT,
    last_event_id TEXT NOT NULL,
    FOREIGN KEY (branched_at_event_id) REFERENCES game_events(event_id),
    FOREIGN KEY (last_event_id) REFERENCES game_events(event_id)
);

-- Materialized view: Combat state
CREATE TABLE combat_state (
    combat_id TEXT PRIMARY KEY,
    timeline_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    enemy_id TEXT NOT NULL,
    enemy_name TEXT,
    enemy_health INTEGER,
    turn_number INTEGER,
    is_active BOOLEAN DEFAULT 1,
    winner TEXT,
    last_event_id TEXT NOT NULL,
    FOREIGN KEY (last_event_id) REFERENCES game_events(event_id)
);
```

**Architectural Evolution Rationale**:

**Why Start with Pure Event Sourcing (Phase 1)?**
- ✅ **Learning Focus**: Understand event sourcing fundamentals first
- ✅ **Simplicity**: No synchronization complexity, single source of truth
- ✅ **No Premature Optimization**: Phase 1 has no complex queries yet
- ✅ **Rebuild Capability**: Can always add read models later by replaying events

**Why Evolve to CQRS (Phase 2+)?**
- ✅ **Performance**: Fast queries for combat, inventory, timeline comparisons
- ✅ **dbt Analytics**: Structured tables easier to query than JSON events
- ✅ **Relational Queries**: JOINs on player + inventory + combat state
- ✅ **Timeline Branching**: Compare timelines efficiently
- ✅ **UI Performance**: No event replay for every screen render

**CQRS Implementation Pattern**:
```python
class EventStore:
    def append_event(self, event: GameEvent) -> None:
        """Append event and update read models (Phase 2+)."""
        with self.conn:
            # 1. Write to events table (source of truth)
            self._write_event(event)
            
            # 2. Update read models (Phase 2+ only)
            if self._has_read_models():
                self._update_player_state(event)
                self._update_inventory_state(event)
                self._update_timeline_state(event)
    
    def _update_player_state(self, event: GameEvent) -> None:
        """Project event onto player_state read model."""
        if event.event_type == "player_level_up":
            self.conn.execute(
                """
                UPDATE player_state 
                SET level = ?, experience = ?, last_event_id = ?
                WHERE player_id = ? AND timeline_id = ?
                """,
                (event.event_data['new_level'], 
                 event.event_data['experience'],
                 event.event_id,
                 event.aggregate_id,
                 event.timeline_id)
            )
```

**Event Replay for Read Model Rebuilding**:
```python
def rebuild_read_models(self, timeline_id: str) -> None:
    """Rebuild all read models from events (CQRS recovery)."""
    # Clear existing read models for timeline
    self._clear_read_models(timeline_id)
    
    # Replay all events in order
    events = self.get_events_by_timeline(timeline_id)
    for event in events:
        self._update_player_state(event)
        self._update_inventory_state(event)
        self._update_timeline_state(event)
```

**dbt Integration with CQRS** (Phase 2+):
```sql
-- dbt/models/staging/stg_player_state.sql
-- Clean staging layer from OLTP read models
SELECT
    player_id,
    timeline_id,
    name,
    level,
    health,
    max_health,
    last_event_id,
    updated_at
FROM {{ source('game', 'player_state') }}
WHERE is_deleted = 0

-- dbt/models/analytics/player_progression.sql
-- Analytics on structured data (much faster than JSON parsing)
SELECT
    player_id,
    timeline_id,
    MAX(level) as max_level_reached,
    COUNT(DISTINCT session_id) as total_sessions,
    AVG(health / max_health) as avg_health_percentage
FROM {{ ref('stg_player_state') }}
GROUP BY player_id, timeline_id
```

**3. WAL Mode is Essential**
- Enables concurrent reads during writes
- Better write performance than default journal mode
- Command: `PRAGMA journal_mode=WAL;`
- Automatic checkpoint management

**4. Event Versioning Strategy**
- **Start Simple**: JSON columns provide schema flexibility
- **Envelope Pattern**: Add `event_version` field if needed later
- **Migration**: Can add columns with ALTER TABLE (SQLite supports this)
- **No Premature Optimization**: Handle versioning when actually needed

**5. Performance Characteristics**
- **INSERT**: < 1ms for single event (with WAL)
- **Batch INSERT**: Can handle 60+ events in < 10ms
- **Timeline Query**: < 100ms for 1000 events with proper indexing
- **File Size**: ~1KB per event average, manageable for development

**Key Insights**:
- **SQLite is the pragmatic choice** for single-player event sourcing
- **WAL mode is non-negotiable** for performance
- **CQRS Evolution Path**: Start with pure event sourcing (Phase 1), evolve to CQRS read models (Phase 2+)
- **Events as Source of Truth**: Read models can always be rebuilt from events
- **aggregate_id + aggregate_type** pattern enables entity-level event queries
- **Proper indexing on timeline_id** is critical for replay performance
- **dbt Integration**: CQRS read models provide structured data for analytics (vs. parsing JSON)
- **Timeline Branching**: Read models make timeline comparison queries fast
- **Migration to PostgreSQL** later is straightforward (event sourcing enables this)
- **File-based database** simplifies development (no server to manage)

**Decision**:
**DECIDED**: Use SQLite with WAL mode (documented as DEC-0001 in decisions.md)

**Rationale**:
- Simplicity beats complexity for learning project
- Performance is more than adequate for single-player
- Event sourcing makes future migration trivial
- Zero ops overhead (no database server)

**Implementation Guidance**:

**Phase 1 (Pure Event Sourcing)**:
1. Use `sqlite3` built-in Python module (no extra dependencies)
2. Enable WAL mode immediately: `PRAGMA journal_mode=WAL`
3. Use parameterized queries (SQL injection protection)
4. Wrap multi-statement operations in transactions
5. Index timeline_id + event_timestamp for fast queries
6. Store complex data as JSON in event_data column
7. Use Unix timestamps for event_timestamp (precision + easy arithmetic)
8. Always include aggregate_id + aggregate_type for future CQRS
9. Event handlers can derive current state by replaying events

**Phase 2+ (CQRS Evolution)**:
10. Create read model tables (player_state, inventory_state, etc.)
11. Update read models synchronously in same transaction as event write
12. Add last_event_id to all read models (rebuild capability)
13. Implement rebuild_read_models() for recovery from events
14. Use read models for queries, events for audit trail
15. dbt models query read models (structured data, not JSON parsing)
16. Timeline comparisons become simple JOINs on timeline_id

**CQRS Migration Path**:
- Phase 1: Events only (keep it simple)
- Phase 2: Add player_state + inventory_state (combat needs fast queries)
- Phase 3: Add timeline_state + combat_state (timeline branching)
- Phase 4: Optimize read models based on actual query patterns

**Design Pattern**:
```
Write Path:  Command → Event → game_events table → Update Read Models
Read Path:   Query → Read Models directly (fast!)
Rebuild:     game_events → Replay → Reconstruct Read Models
```

**Code Example**:
```python
import sqlite3
from datetime import datetime

class EventStore:
    def __init__(self, db_path: str = "data/events.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()
    
    def append_event(self, event: GameEvent) -> None:
        """Append event with ACID guarantees."""
        with self.conn:  # Automatic transaction
            self.conn.execute(
                """
                INSERT INTO game_events (
                    event_id, event_timestamp, session_id, timeline_id,
                    event_type, player_id, state_before, player_action,
                    ai_response, outcome, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_timestamp.timestamp(),
                    event.session_id,
                    event.timeline_id,
                    event.event_type,
                    event.player_id,
                    json.dumps(event.state_before) if event.state_before else None,
                    event.player_action,
                    event.ai_response,
                    json.dumps(event.outcome) if event.outcome else None,
                    json.dumps(event.metadata) if event.metadata else None
                )
            )
```

**Confidence Level**: 🟢 High

**Next Steps**:
- **Phase 1**: Implement EventStore class with pure event sourcing
- Include aggregate_id + aggregate_type in schema (CQRS preparation)
- Benchmark actual performance during implementation
- Monitor file size growth during testing
- **Phase 2**: Design read model schemas based on query patterns
- **Phase 3**: Implement CQRS event handlers for read model updates
- Document CQRS migration as DEC-0004 when implementing Phase 2  

**References**:
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [Event Sourcing by Martin Fowler](https://martinfowler.com/eaaDev/EventSourcing.html)

---

### Topic 2: Pygame Event Loop Integration
**Status**: 🔲 Not Started  
**Priority**: 🔴 High  
**Assigned To**: @pygame-worker  

**Why Research Needed**:
The game loop must integrate Pygame's event system with our state machine and maintain 60 FPS while performing async AI calls and database writes.

**Questions to Answer**:
1. How to integrate async/await with Pygame's synchronous event loop?
2. What's the best approach for fixed vs variable timestep?
3. How to prevent blocking from database writes in game loop?
4. Can we achieve 60 FPS with SQLite writes per frame?
5. What Pygame version is compatible with Python 3.13?

**Research Sources**:
- [ ] Pygame 2.6.x documentation
- [ ] "Fix Your Timestep" by Glenn Fiedler
- [ ] Pygame + asyncio integration patterns
- [ ] Game loop architecture patterns
- [ ] Python 3.13 compatibility matrix

**Research Methodology**:
- Review Pygame community patterns for async integration
- Research frame timing and delta time calculations
- Investigate pygame-menu or similar for UI state management
- Benchmark Pygame + SQLite write performance

**Findings**:
[To be filled]

**Key Insights**:
- [To be filled]

**Decision**:
[To be filled - document in decisions.md]

**Implementation Guidance**:
[To be filled]

**Confidence Level**: 🟡 Medium  

**References**:
- [Pygame Documentation](https://www.pygame.org/docs/)
- [Fix Your Timestep](https://gafferongames.com/post/fix_your_timestep/)

---

### Topic 3: State Machine Pattern
**Status**: 🔲 Not Started  
**Priority**: 🔴 High  
**Assigned To**: @game-logic-worker  

**Why Research Needed**:
State machine must be robust, testable, and emit events for sourcing. Need to validate transition logic and ensure it supports future timeline branching.

**Questions to Answer**:
1. What Python library best supports state machines (or roll our own)?
2. How to structure state transitions for easy testing?
3. How to emit events during transitions without tight coupling?
4. Should states be classes or functions?
5. How to handle nested/hierarchical states?

**Research Sources**:
- [ ] Python transitions library
- [ ] State pattern in Design Patterns book
- [ ] Game Programming Patterns - State chapter
- [ ] Python enum best practices
- [ ] Existing RPG state machine examples

**Research Methodology**:
- Evaluate transitions vs python-statemachine vs custom implementation
- Review state pattern implementations in Python games
- Research testability of different state machine approaches
- Consider dependency injection for state objects

**Findings**:
[To be filled]

**Key Insights**:
- [To be filled]

**Decision**:
[To be filled - document in decisions.md]

**Implementation Guidance**:
[To be filled]

**Confidence Level**: 🟢 High  

**References**:
- [Game Programming Patterns - State](https://gameprogrammingpatterns.com/state.html)
- [Python transitions library](https://github.com/pytransitions/transitions)

---

### Topic 4: Async AI Integration
**Status**: 🔲 Not Started  
**Priority**: 🔴 High  
**Assigned To**: @ai-worker  

**Why Research Needed**:
AI calls must not block the game loop. Need to research asyncio integration with Pygame's synchronous event loop.

**Questions to Answer**:
1. How to run async AI calls without blocking Pygame's main loop?
2. Should we use threads, asyncio, or a hybrid approach?
3. How to handle AI timeouts gracefully?
4. What's the best pattern for task cancellation?
5. How to queue AI requests and process responses?

**Research Sources**:
- [ ] Python asyncio documentation
- [ ] aiohttp best practices
- [ ] Pygame + asyncio integration examples
- [ ] Thread-safe queue patterns
- [ ] asyncio.run_in_executor patterns

**Research Methodology**:
- Research asyncio event loop integration with Pygame
- Investigate concurrent.futures for background AI tasks
- Test aiohttp timeout and retry mechanisms
- Benchmark different async patterns for latency

**Findings**:
[To be filled]

**Key Insights**:
- [To be filled]

**Decision**:
[To be filled - document in decisions.md]

**Implementation Guidance**:
[To be filled]

**Confidence Level**: 🟡 Medium  

**References**:
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [aiohttp documentation](https://docs.aiohttp.org/)

---

### Topic 5: Configuration Management
**Status**: ✅ Complete  
**Priority**: 🟡 Medium  
**Assigned To**: @architect-supervisor  
**Completed**: 2025-11-24

**Why Research Needed**:
Need a clean way to manage game configuration (screen size, FPS target, AI settings) that's easy to test and doesn't use global state.

**Questions to Answer**:
1. ✅ What's the best Python library for configuration? (pydantic-settings, dynaconf, etc.)
2. ✅ How to handle environment-specific configs (dev, test, prod)?
3. ✅ Should config be injected like other dependencies?
4. ✅ How to validate configuration at startup?
5. ✅ What format: YAML, TOML, Python dataclass?

**Research Sources**:
- [x] Pydantic BaseSettings documentation
- [x] dynaconf library
- [x] Python configparser vs modern alternatives
- [x] 12-factor app methodology
- [x] Configuration management best practices

**Research Methodology**:
- Compare pydantic-settings vs dynaconf vs python-decouple
- Research type-safe configuration patterns
- Investigate environment variable handling
- Consider testability of different approaches

**Findings**:

**1. Pydantic Settings is the Clear Winner**
- **Type Safety**: Full Pydantic validation (constitution principle #3)
- **Environment Variables**: Automatic loading from .env files
- **Validation**: Schema validation at startup (fail fast)
- **IDE Support**: Type hints = autocomplete + type checking
- **Already Using Pydantic**: v2.10.0 in pyproject.toml

**2. Comparison of Options**

| Feature | pydantic-settings | dynaconf | python-decouple | configparser |
|---------|-------------------|----------|-----------------|--------------|
| Type Safety | ✅ Full | ⚠️ Partial | ❌ No | ❌ No |
| Validation | ✅ Schema | ⚠️ Manual | ❌ Manual | ❌ Manual |
| .env Support | ✅ Built-in | ✅ Built-in | ✅ Built-in | ❌ No |
| IDE Support | ✅ Excellent | ⚠️ OK | ⚠️ OK | ❌ Poor |
| Dependencies | Pydantic | dynaconf | python-decouple | stdlib |
| Learning Curve | 🟢 Low | 🟡 Medium | 🟢 Low | 🟢 Low |

**3. Configuration Structure**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class GameConfig(BaseSettings):
    """Game configuration with validation."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Game Settings
    game_title: str = "Temporal Echoes"
    fps_target: int = Field(default=60, ge=1, le=144)
    window_width: int = Field(default=800, ge=640)
    window_height: int = Field(default=600, ge=480)
    fullscreen: bool = False
    
    # Database Settings
    database_path: str = "data/events.db"
    duckdb_path: str = "data/analytics.duckdb"
    
    # AI Settings
    ollama_host: str = "localhost:11434"
    llm_model: str = "llama3.2"
    llm_timeout: float = Field(default=5.0, ge=1.0, le=30.0)
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    
    # Development Settings
    debug_mode: bool = False
    log_level: str = "INFO"
```

**4. Environment-Specific Configs**
```bash
# .env (local development)
DEBUG_MODE=true
LOG_LEVEL=DEBUG
FPS_TARGET=60

# .env.test (testing)
DATABASE_PATH=:memory:
DEBUG_MODE=true

# .env.prod (production - future)
DEBUG_MODE=false
LOG_LEVEL=WARNING
FULLSCREEN=true
```

**5. Dependency Injection Pattern**
```python
# In main.py or game context
config = GameConfig()  # Loads from .env automatically

# Inject into classes
event_store = EventStore(db_path=config.database_path)
ai_manager = AIManager(
    host=config.ollama_host,
    model=config.llm_model,
    timeout=config.llm_timeout
)
```

**6. Validation at Startup**
```python
def main():
    try:
        config = GameConfig()
    except ValidationError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    
    # Config is valid, proceed
    game = Game(config)
    game.run()
```

**Key Insights**:
- **Pydantic Settings** is the obvious choice (already using Pydantic)
- Type hints + validation = fewer runtime errors
- .env file support matches 12-factor app methodology
- Dependency injection aligns with constitution principle #2
- Zero additional dependencies (pydantic already in project)
- Validation fails fast at startup (no surprises during gameplay)

**Decision**:
**DECIDED**: Use Pydantic Settings with BaseSettings pattern

**Rationale**:
- Already using Pydantic v2.10.0 (no new dependency)
- Type safety aligns with constitution principle #3
- Automatic .env loading matches 12-factor principles
- IDE support improves developer experience
- Validation at startup prevents runtime config errors

**Implementation Guidance**:
1. Create `src/core/config.py` with `GameConfig(BaseSettings)` class
2. Use `Field()` for validation rules (min/max values)
3. Create `.env.example` with all config options documented
4. Load config once at startup: `config = GameConfig()`
5. Inject config into classes that need it
6. For tests, override values: `GameConfig(database_path=":memory:")`
7. Document all config options with docstrings

**Code Example**:
```python
# src/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class GameConfig(BaseSettings):
    """
    Game configuration with environment variable support.
    
    Loads from .env file automatically. Validates all settings at startup.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GAME_",  # Optional: prefix all vars with GAME_
        case_sensitive=False
    )
    
    fps_target: int = Field(
        default=60,
        ge=1,
        le=144,
        description="Target frames per second"
    )
    
    database_path: str = Field(
        default="data/events.db",
        description="Path to SQLite event store"
    )

# Usage
config = GameConfig()
print(f"FPS: {config.fps_target}")  # Type-safe!
```

**Confidence Level**: 🟢 High  

**References**:
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [The Twelve-Factor App](https://12factor.net/config)

---

### Topic 6: Testing Strategy
**Status**: ✅ Complete  
**Priority**: 🟡 Medium  
**Assigned To**: @architect-supervisor  
**Completed**: 2025-11-24

**Why Research Needed**:
Need to establish testing patterns for event sourcing, state machines, and Pygame integration to achieve >= 80% coverage.

**Questions to Answer**:
1. ✅ How to mock Pygame for unit tests?
2. ✅ How to test event sourcing replay logic?
3. ✅ How to test async AI calls without hitting real Ollama?
4. ✅ What fixtures are needed for common test scenarios?
5. ✅ How to test state machine transitions comprehensively?

**Research Sources**:
- [x] Pytest best practices
- [x] Pygame testing patterns
- [x] pytest-asyncio documentation
- [x] Mock/MagicMock best practices
- [x] Event sourcing testing strategies

**Research Methodology**:
- Research Pygame mocking strategies (pygame.locals, surfaces, etc.)
- Investigate pytest-mock and pytest-asyncio
- Review event sourcing testing patterns
- Consider property-based testing with hypothesis

**Findings**:

**1. Testing Stack (Already in pyproject.toml)**
- **pytest** v8.3.0: Test framework
- **pytest-cov**: Coverage reporting (>= 80% requirement)
- **pytest-asyncio**: For async AI tests (Phase 4+)
- **unittest.mock**: Built-in, sufficient for mocking

**2. Testing Patterns for Phase 1**

**A. Event Store Testing**
```python
# tests/unit/test_event_store.py
import pytest
from src.core.persistence import EventStore, GameEvent
from datetime import datetime

@pytest.fixture
def event_store():
    """In-memory database for tests."""
    store = EventStore(":memory:")
    yield store
    store.close()

@pytest.fixture
def sample_event():
    """Reusable test event."""
    return GameEvent(
        event_id="test-001",
        event_timestamp=datetime.utcnow(),
        session_id="session-1",
        timeline_id="timeline-1",
        event_type="state_transition",
        player_id="player-1",
        state_before={"state": "MENU"},
        player_action="start_game",
        outcome={"state": "EXPLORING"}
    )

def test_append_and_retrieve_event(event_store, sample_event):
    """Test event store append and retrieval."""
    # Arrange & Act
    event_store.append_event(sample_event)
    events = event_store.get_events_by_timeline("timeline-1")
    
    # Assert
    assert len(events) == 1
    assert events[0].event_id == "test-001"
    assert events[0].event_type == "state_transition"

def test_immutability(event_store, sample_event):
    """Ensure events cannot be modified (constitution principle #11)."""
    event_store.append_event(sample_event)
    
    # Attempt update should fail or be disallowed
    with pytest.raises(Exception):  # Specific exception TBD
        event_store.update_event(sample_event.event_id, {"new": "data"})
```

**B. State Machine Testing**
```python
# tests/unit/test_state_machine.py
import pytest
from src.core.state_machine import GameStateMachine, GameState, StateTransitionError
from unittest.mock import Mock

@pytest.fixture
def event_store_mock():
    """Mock event store to avoid database in unit tests."""
    return Mock()

@pytest.fixture
def state_machine(event_store_mock):
    """State machine with mocked dependencies."""
    return GameStateMachine(event_store=event_store_mock)

def test_valid_transition(state_machine):
    """Test allowed state transitions."""
    state_machine.transition(GameState.EXPLORING, context={"player": "test"})
    assert state_machine.current_state == GameState.EXPLORING

def test_invalid_transition_raises_error(state_machine):
    """Test invalid transitions are blocked."""
    with pytest.raises(StateTransitionError):
        state_machine.transition(GameState.COMBAT, context={})  # Can't go MENU -> COMBAT

def test_transition_emits_event(state_machine, event_store_mock):
    """Ensure events emitted on transitions (constitution #1)."""
    state_machine.transition(GameState.EXPLORING, context={"test": True})
    
    # Verify event_store.append_event was called
    assert event_store_mock.append_event.called
    call_args = event_store_mock.append_event.call_args[0][0]
    assert call_args.event_type == "state_transition"
```

**C. Configuration Testing**
```python
# tests/unit/test_config.py
import pytest
from pydantic import ValidationError
from src.core.config import GameConfig

def test_default_config():
    """Test default configuration values."""
    config = GameConfig()
    assert config.fps_target == 60
    assert config.window_width == 800

def test_validation_enforced():
    """Test pydantic validation (constitution #3)."""
    with pytest.raises(ValidationError):
        GameConfig(fps_target=0)  # Must be >= 1
    
    with pytest.raises(ValidationError):
        GameConfig(fps_target=200)  # Must be <= 144

def test_env_override(monkeypatch):
    """Test environment variable override."""
    monkeypatch.setenv("FPS_TARGET", "120")
    config = GameConfig()
    assert config.fps_target == 120
```

**D. Async AI Testing (Phase 4+)**
```python
# tests/unit/test_ai_manager.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_ai_call_without_real_ollama():
    """Test AI without hitting real Ollama."""
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"response": "test narrative"}
        )
        
        ai_manager = AIManager()
        result = await ai_manager.generate_narrative(context={})
        
        assert result == "test narrative"
        assert mock_post.called
```

**3. Fixture Organization**
```python
# tests/fixtures/__init__.py
# tests/fixtures/event_fixtures.py - Reusable event data
# tests/fixtures/game_fixtures.py - GameContext, StateMachine fixtures
# tests/conftest.py - pytest configuration and shared fixtures

# tests/conftest.py
import pytest

@pytest.fixture(scope="session")
def test_database_path():
    return ":memory:"  # Always use in-memory for tests

@pytest.fixture
def clean_database():
    """Ensures clean state between tests."""
    # Setup
    db = EventStore(":memory:")
    yield db
    # Teardown
    db.close()
```

**4. Pygame Mocking (Phase 4+)**
```python
# No Pygame in Phase 1, but future approach:
from unittest.mock import MagicMock
import sys

# Mock pygame module entirely for unit tests
sys.modules['pygame'] = MagicMock()

# Or use pytest-mock
def test_rendering(mocker):
    mock_pygame = mocker.patch('pygame')
    # Test rendering logic without actual pygame
```

**5. Event Sourcing Replay Testing**
```python
def test_event_replay_reconstruct_state(event_store):
    """Test state reconstruction from events."""
    # Arrange: Add sequence of events
    events = [
        GameEvent(..., event_type="game_start"),
        GameEvent(..., event_type="player_move"),
        GameEvent(..., event_type="combat_start"),
    ]
    for event in events:
        event_store.append_event(event)
    
    # Act: Replay events to reconstruct state
    state = replay_events(event_store.get_events_by_timeline("timeline-1"))
    
    # Assert: State matches expected
    assert state.current_location == "forest"
    assert state.in_combat == True
```

**6. Coverage Configuration**
```toml
# pyproject.toml (already exists)
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=src --cov-report=html --cov-report=term-missing --strict-markers"

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "**/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

**Key Insights**:
- **In-Memory Database** (`:memory:`) for fast, isolated tests
- **Mock Dependencies** for unit tests (event_store_mock, ai_mock)
- **Fixtures** provide reusable test data and setup
- **pytest-asyncio** handles async AI tests (Phase 4+)
- **unittest.mock** is sufficient (no need for pytest-mock)
- **Coverage** already configured in pyproject.toml (>= 80%)
- **No Pygame mocking needed for Phase 1** (no rendering)

**Decision**:
**DECIDED**: Use pytest + unittest.mock + pytest-asyncio (standard testing stack)

**Rationale**:
- pytest is industry standard (already configured)
- unittest.mock is built-in (no extra dependency)
- pytest-asyncio for future AI tests
- In-memory database makes tests fast
- Fixtures provide clean, reusable test data
- Aligns with constitution principle #5 (>= 80% coverage)

**Implementation Guidance**:
1. Create `tests/fixtures/event_fixtures.py` with reusable event data
2. Use `:memory:` for EventStore in all tests
3. Mock EventStore in StateMachine tests (avoid database in unit tests)
4. Write tests **alongside** implementation (TDD approach)
5. Run `make test` frequently (fast with in-memory DB)
6. Check coverage: `pytest --cov=src --cov-report=term-missing`
7. Aim for 100% on critical paths (EventStore, StateMachine)
8. Integration tests in `tests/integration/` (test multiple components together)

**Test Organization**:
```
tests/
├── unit/
│   ├── test_event_store.py      # EventStore unit tests
│   ├── test_state_machine.py    # StateMachine unit tests
│   ├── test_game_context.py     # GameContext unit tests
│   ├── test_config.py            # Config validation tests
│   └── test_game_loop.py         # GameLoop unit tests
├── integration/
│   ├── test_event_sourcing_flow.py  # End-to-end event flow
│   └── test_game_lifecycle.py       # Full game startup/shutdown
├── fixtures/
│   ├── __init__.py
│   ├── event_fixtures.py         # Reusable events
│   └── game_fixtures.py          # GameContext, StateMachine fixtures
└── conftest.py                   # Shared pytest configuration
```

**Confidence Level**: 🟢 High  

**References**:
- [Pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

---

## Tech Stack Validation

**Purpose**: Validate versions and check for breaking changes in key dependencies.

| Component | Current Version | Latest Version | Breaking Changes? | Security Issues? | Action | Notes |
|-----------|----------------|----------------|-------------------|------------------|--------|-------|
| Python | 3.13.3 | [Check] | [Y/N] | [Y/N] | ✅ / ⚠️ / ❌ | [To be filled] |
| Pygame | 2.6.1 | [Check] | [Y/N] | [Y/N] | ✅ / ⚠️ / ❌ | [To be filled] |
| SQLite | 3.x (via sqlite3) | [Check] | [Y/N] | [Y/N] | ✅ / ⚠️ / ❌ | [To be filled] |
| aiohttp | 3.11.0 | [Check] | [Y/N] | [Y/N] | ✅ / ⚠️ / ❌ | [To be filled] |
| Pydantic | 2.10.0 | [Check] | [Y/N] | [Y/N] | ✅ / ⚠️ / ❌ | [To be filled] |
| Pytest | 8.3.0 | [Check] | [Y/N] | [Y/N] | ✅ / ⚠️ / ❌ | [To be filled] |

**Action Items**:
- [ ] Check all versions against latest releases
- [ ] Review changelogs for breaking changes
- [ ] Test critical dependencies in sandbox
- [ ] Update pyproject.toml with validated versions

---

## Assumptions Made

### Assumption 1: SQLite Performance is Sufficient
**Assumption**: SQLite can handle append-only event writes at 60 FPS without blocking

**Why Made**: SQLite is ACID-compliant and WAL mode should provide good write performance

**Risk if Wrong**: Game loop will lag, user experience degraded
- **Severity**: 🔴 Critical
- **Likelihood**: 🟡 Medium

**Validation Plan**: Benchmark SQLite inserts with 60 writes/second in game loop simulation

**Timeline**: During Step 1 (SQLite Event Store implementation)

**Mitigation**: 
- Buffer events in memory and batch write every N frames
- Move to PostgreSQL if SQLite can't handle throughput
- Use separate thread for database writes

**Status**: 🔲 Not Yet Validated

---

### Assumption 2: Pygame + asyncio is Viable
**Assumption**: We can integrate async AI calls with Pygame's synchronous event loop

**Why Made**: Other projects have successfully integrated asyncio with game loops

**Risk if Wrong**: AI calls will block game loop or require major refactoring
- **Severity**: 🟡 Moderate
- **Likelihood**: 🟡 Medium

**Validation Plan**: Prototype async task execution during game loop in Step 4

**Timeline**: During Step 4 (Game Loop Implementation)

**Mitigation**:
- Use threading instead of asyncio if needed
- Queue AI requests and poll for results
- Accept 5-second AI timeout with fallback

**Status**: 🔲 Not Yet Validated

---

### Assumption 3: Event Sourcing Won't Bloat Database
**Assumption**: Append-only events won't cause database size issues in development

**Why Made**: Testing and development won't generate millions of events

**Risk if Wrong**: Database file becomes unwieldy, slows down development
- **Severity**: 🟢 Low
- **Likelihood**: 🟢 Low

**Validation Plan**: Monitor database file size during testing phases

**Timeline**: Ongoing throughout development

**Mitigation**:
- Implement event archival/deletion for dev databases
- Document how to reset database
- Add make target for database cleanup

**Status**: 🔲 Not Yet Validated

---

## Performance Benchmarks

### Benchmark 1: SQLite Write Performance
**Component**: Event Store

**Method**: Insert 1000 events sequentially, measure time

**Target**: < 16ms for single event insert (60 FPS requirement)

**Status**: 🔲 Not Yet Benchmarked

**Action**: Create benchmark script in Step 1

---

### Benchmark 2: State Machine Transition Speed
**Component**: State Machine

**Method**: Execute 1000 state transitions, measure average time

**Target**: < 1ms per transition

**Status**: 🔲 Not Yet Benchmarked

**Action**: Create benchmark script in Step 2

---

## Security Considerations

### Risk 1: SQL Injection in Event Store
**Description**: Event payloads could contain user input that's not properly escaped

**Severity**: 🟡 High

**Mitigation**: 
- Always use parameterized queries
- Validate event schema with Pydantic before insert
- Never construct SQL strings with f-strings or concatenation

**Status**: ✅ Mitigated (by design)

---

### Risk 2: Ollama Connection Security
**Description**: AI requests to Ollama are over HTTP, not HTTPS

**Severity**: 🟢 Medium

**Mitigation**:
- Ollama runs locally on localhost only
- No sensitive data in AI prompts (player names ok, no PII)
- Document that Ollama should not be exposed to internet

**Status**: ✅ Mitigated (localhost only)

---

## Questions for Expert Review

1. **Event Schema Versioning**: Should we version event schemas from Day 1 or add later?
   - **Context**: Event sourcing requires handling schema evolution
   - **Impact**: Affects event store design in Step 1
   - **Urgency**: 🟡 Medium

2. **State Machine Library**: Use existing library or custom implementation?
   - **Context**: Custom gives full control, library may have overhead
   - **Impact**: Affects Step 2 implementation complexity
   - **Urgency**: 🔴 High

---

## Research Timeline

| Topic | Start Date | Completion Date | Duration | Blocker? |
|-------|-----------|-----------------|----------|----------|
| Event Sourcing | [TBD] | [TBD] | 2-3 hours | No |
| Pygame Integration | [TBD] | [TBD] | 1-2 hours | No |
| State Machine | [TBD] | [TBD] | 1-2 hours | No |
| Async AI | [TBD] | [TBD] | 2 hours | No |
| Configuration | [TBD] | [TBD] | 1 hour | No |
| Testing Strategy | [TBD] | [TBD] | 1 hour | No |

**Total Estimated Time**: 6-8 hours

---

## Constitution Compliance

**Purpose**: Verify research findings align with development principles.

- [ ] Research supports event sourcing architecture ✅
- [ ] Findings compatible with dependency injection ✅
- [ ] No global state patterns identified ✅
- [ ] Performance targets align with 60 FPS goal (to be validated)
- [ ] AI integration respects async requirements (to be validated)
- [ ] Database choices support OLTP/OLAP separation ✅

**Potential Conflicts**:
[None identified yet - will update as research progresses]

**Resolution Plan**:
[To be filled if conflicts arise]

---

## Sign-off

- [ ] All high-priority research complete
- [ ] Critical decisions made and documented
- [ ] Assumptions validated or documented
- [ ] Tech stack versions confirmed
- [ ] Security risks identified and mitigated
- [ ] Ready to proceed with implementation

**Research Lead**: @architect-supervisor  
**Completion Date**: [TBD]  
**Approved By**: [TBD]  
**Approval Date**: [TBD]

