# Decision Log: Phase 1 - Core Game Loop

**Phase**: Phase 1  
**Created**: 2025-11-24  
**Status**: ✅ Complete  
**Completed**: 2025-11-24  

## Overview
This document logs all significant architectural, design, and implementation decisions made during Phase 1. Decisions are captured using a lightweight ADR (Architecture Decision Record) format.

**Total Decisions**: 8  
**Constitution Deviations**: 0  
**Critical Impact**: 4  

---

## Decision Index

Quick reference table for all decisions:

| ID | Title | Status | Impact | Date | Deviation | Notes |
|----|-------|--------|--------|------|-----------|-------|
| DEC-0001 | SQLite for Event Store | 🟡 Accepted | 🔴 Critical | 2025-11-24 | ❌ | Event sourcing foundation |
| DEC-0002 | Custom State Machine Pattern | 🟡 Accepted | 🟡 High | 2025-11-24 | ❌ | Clear transitions, testable |
| DEC-0003 | No Rendering in Phase 1 | 🟡 Accepted | 🟢 Medium | 2025-11-24 | ❌ | Architecture-first approach |
| DEC-0004 | Hybrid CQRS Architecture | 🟡 Accepted | 🔴 Critical | 2025-11-24 | ❌ | App read models + dbt analytics |
| DEC-0005 | Threading Over Asyncio | 🟡 Accepted | 🔴 Critical | 2025-11-24 | ❌ | Simpler, Pygame-compatible |
| DEC-0006 | Fixed Timestep Game Loop | 🟡 Accepted | 🔴 Critical | 2025-11-24 | ❌ | Deterministic, 60 FPS target |
| DEC-0007 | Pydantic Settings for Config | 🟡 Accepted | 🟢 Medium | 2025-11-24 | ❌ | Type-safe, validation |
| DEC-0008 | pytest Testing Stack | 🟡 Accepted | 🟡 High | 2025-11-24 | ❌ | Industry standard |

---

## Completed Research-Based Decisions

All pending decisions have been resolved based on completed research findings.

---

## Actual Decisions

---

## [DEC-0001]: SQLite for Event Store

**Status**: 🟡 Accepted  
**Date**: 2025-11-24  
**Deciders**: @architect-supervisor, @data-worker  
**Impact**: 🔴 Critical  
**Constitution Deviation**: ❌ No  

### Context
Phase 1 requires an event store for event sourcing architecture. The choice of database affects performance, complexity, and future scalability. We need a reliable, ACID-compliant solution that supports append-only writes and timeline querying.

**Constraints**:
- Single-player game (no multi-user concurrency needed)
- Event sourcing pattern (append-only writes)
- Need ACID guarantees
- Development simplicity valued (learning project)
- Must support timeline branching queries

### Decision
Use **SQLite with WAL (Write-Ahead Logging) mode** for the event store.

**Schema Design**:
- `game_events` table with append-only inserts
- Indexes on: `timeline_id`, `session_id`, `event_timestamp`
- JSON column for event payload (flexibility for schema evolution)
- No UPDATE or DELETE operations (constitution compliance)

### Alternatives Considered

#### Alternative 1: PostgreSQL
**Description**: Production-grade RDBMS with advanced features

**Pros**:
- Better multi-writer concurrency (MVCC)
- Streaming replication built-in
- More powerful query optimizer
- Rich ecosystem (TimescaleDB, extensions)

**Cons**:
- Requires Docker container and connection management
- Network latency overhead
- More complex configuration
- Overkill for single-player game

**Reason Rejected**: Unnecessary complexity for current requirements. Can migrate later if needed (event sourcing makes this easy).

#### Alternative 2: JSON Files
**Description**: Store events as JSON files on disk

**Pros**:
- Extremely simple
- Human-readable
- No database setup

**Cons**:
- No transaction safety (ACID)
- Manual indexing required
- Poor query performance
- File locking issues
- Not suitable for event sourcing

**Reason Rejected**: Violates constitution principle #12 (transaction safety).

#### Alternative 3: DuckDB for Everything
**Description**: Use DuckDB for both OLTP and OLAP

**Pros**:
- One database instead of two
- Excellent analytical performance

**Cons**:
- Optimized for OLAP, not OLTP
- Concurrent write performance unknown
- Less mature for transactional workloads
- Blurs separation of concerns

**Reason Rejected**: Violates constitution principle #13 (database separation: SQLite for OLTP, DuckDB for OLAP).

### Consequences

#### Positive
- Simple, embedded database (no server to manage)
- ACID guarantees out of the box
- Excellent write performance with WAL mode
- Easy backups (just copy the file)
- Event sourcing makes future migration straightforward
- Developer can focus on game logic, not database ops

#### Negative  
- Limited to single-writer (acceptable for single-player)
- Less powerful query optimizer than PostgreSQL
- File-based means harder to scale to multiplayer later
- Need to manage schema migrations manually

#### Neutral
- SQLite is ubiquitous and well-understood
- Python sqlite3 module is built-in

### Trade-offs Accepted
**Giving up**: Multi-writer concurrency, advanced PostgreSQL features, replication  
**Gaining**: Simplicity, zero ops overhead, faster development iteration

For a learning project focused on event sourcing and game development, this trade-off strongly favors SQLite.

### Implementation Notes
```python
# Event store initialization
import sqlite3

class EventStore:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode
        self._init_schema()
    
    def append_event(self, event: GameEvent) -> None:
        """Append event with ACID guarantees."""
        with self.conn:  # Transaction context
            self.conn.execute(
                "INSERT INTO game_events (...) VALUES (?, ?, ...)",
                (event.event_id, event.timestamp, ...)
            )
```

**Key Points**:
- Always use WAL mode for better concurrency
- Use parameterized queries (SQL injection protection)
- Wrap multi-step operations in transactions
- Index timeline_id for fast timeline queries

### Success Criteria
- [x] SQLite with WAL mode configured
- [ ] < 10ms p95 latency for event writes (to be benchmarked in Step 1)
- [ ] Can handle 60 events/second (worst case: 60 FPS with event per frame)
- [ ] No database corruption during testing
- [ ] Timeline queries return results in < 100ms for 1000 events

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|-----------|--------|---------------------|-------|
| File corruption | 🟢 Low | 🔴 Critical | Regular backups, WAL mode, proper shutdown handling | @data-worker |
| Performance bottleneck | 🟡 Med | 🟡 High | Benchmark early (Step 1), optimize indexes | @data-worker |
| Outgrow SQLite later | 🟡 Med | 🟢 Med | Event sourcing enables easy migration to PostgreSQL | @architect-supervisor |

### Related Decisions
- Depends on: None (foundational decision)
- Influences: DEC-0002 (state machine must emit events to this store)

### Constitution Compliance
**Principle 11 (Events are Immutable)**: ✅ SQLite with append-only writes enforces this  
**Principle 12 (Transaction Safety)**: ✅ ACID guarantees via SQLite transactions  
**Principle 13 (Database Separation)**: ✅ SQLite for OLTP, DuckDB for OLAP

No deviations. This decision fully aligns with constitution principles.

### References
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [Event Sourcing by Martin Fowler](https://martinfowler.com/eaaDev/EventSourcing.html)
- [SQLite Performance Tuning](https://www.sqlite.org/pragma.html)

### Changelog
- **2025-11-24**: Decision accepted, moved from PLAN.md to proper ADR format

---

## [DEC-0002]: Custom State Machine Pattern

**Status**: 🟡 Accepted  
**Date**: 2025-11-24  
**Deciders**: @architect-supervisor, @game-logic-worker  
**Impact**: 🟡 High  
**Constitution Deviation**: ❌ No  

### Context
Phase 1 requires a state machine to manage game modes (MENU, EXPLORING, COMBAT, DIALOGUE, etc.). The implementation approach affects code clarity, testability, and maintainability.

**Requirements**:
- Clear state transitions
- Transition validation (prevent invalid state changes)
- Event emission for sourcing
- Testability
- Support for future hierarchical states (maybe)

### Decision
Implement a **custom State Machine** using Python enums and a transition validation matrix.

**Implementation Approach**:
- `GameState` enum for states
- `GameStateMachine` class with transition logic
- Transition validation via explicit allowed transitions
- Event emission on every state change
- Dependency injection for EventStore

### Alternatives Considered

#### Alternative 1: `transitions` Library
**Description**: Popular Python state machine library

**Pros**:
- Battle-tested, mature library
- Callbacks and guards built-in
- Supports hierarchical state machines
- Good documentation

**Cons**:
- Additional dependency
- Learning curve for library API
- More abstraction than needed for simple use case
- Harder to debug (magic under the hood)

**Reason Rejected**: For a learning project, building from scratch provides better understanding of state machines. The library's features are overkill for current needs.

#### Alternative 2: `python-statemachine`
**Description**: Another state machine library

**Pros**:
- Type-safe transitions
- Clean API
- Active maintenance

**Cons**:
- Additional dependency
- Learning curve
- Not clear how to integrate with event sourcing

**Reason Rejected**: Same reasoning as `transitions` - custom implementation is more educational.

#### Alternative 3: Pure Event Sourcing (No State Machine)
**Description**: Derive state purely from event replay

**Pros**:
- Most "pure" event sourcing approach
- Maximum flexibility

**Cons**:
- Complex to reason about
- Harder to enforce valid transitions
- Performance overhead (event replay)
- Steep learning curve

**Reason Rejected**: Too complex for Phase 1. Start with explicit state machine, evolve later if needed.

### Consequences

#### Positive
- Full control over implementation
- Easy to understand and debug
- Educational value (learn state machine patterns)
- Simple to test (no library mocking needed)
- Explicit transition rules (self-documenting)

#### Negative  
- Some boilerplate code
- Need to implement validation ourselves
- No built-in hierarchical state support (may need later)
- Reinventing the wheel slightly

#### Neutral
- ~100 lines of code to maintain
- Standard state pattern from Design Patterns book

### Trade-offs Accepted
**Giving up**: Library features, battle-tested code, hierarchical states out-of-the-box  
**Gaining**: Simplicity, learning, full control, easy debugging

For a learning-focused RPG, this trade-off favors custom implementation.

### Implementation Notes
```python
from enum import Enum, auto
from typing import Dict, Set

class GameState(Enum):
    MENU = auto()
    EXPLORING = auto()
    COMBAT = auto()
    DIALOGUE = auto()
    INVENTORY = auto()
    TIMELINE_VIEW = auto()

class GameStateMachine:
    # Define valid transitions
    ALLOWED_TRANSITIONS: Dict[GameState, Set[GameState]] = {
        GameState.MENU: {GameState.EXPLORING, GameState.TIMELINE_VIEW},
        GameState.EXPLORING: {GameState.COMBAT, GameState.DIALOGUE, GameState.INVENTORY, GameState.MENU},
        # ... more transitions
    }
    
    def transition(self, to_state: GameState, context: Dict) -> None:
        if not self._is_valid_transition(to_state):
            raise StateTransitionError(f"Invalid: {self._state} -> {to_state}")
        
        # Emit event BEFORE changing state
        self._emit_event(from_state=self._state, to_state=to_state, context=context)
        self._state = to_state
```

### Success Criteria
- [x] GameState enum defined
- [ ] All valid transitions explicitly allowed
- [ ] Invalid transitions raise StateTransitionError
- [ ] Events emitted for every transition
- [ ] Unit tests cover all transition paths
- [ ] >= 80% code coverage

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|-----------|--------|---------------------|-------|
| Need hierarchical states later | 🟡 Med | 🟡 High | Refactor to library if needed, events preserved | @game-logic-worker |
| Boilerplate becomes unwieldy | 🟢 Low | 🟢 Med | Keep it simple, only add complexity when needed | @game-logic-worker |

### Related Decisions
- Depends on: DEC-0001 (needs EventStore for event emission)
- Influences: All game state logic

### Constitution Compliance
**Principle 1 (Event Sourcing)**: ✅ Emits events on transitions  
**Principle 2 (Dependency Injection)**: ✅ EventStore injected via constructor  
**Principle 3 (Type Safety)**: ✅ Enum provides type safety

No deviations.

### References
- [Game Programming Patterns - State](https://gameprogrammingpatterns.com/state.html)
- [State Pattern - Design Patterns](https://refactoring.guru/design-patterns/state)

### Changelog
- **2025-11-24**: Decision accepted, moved from PLAN.md to proper ADR format

---

## [DEC-0003]: No Rendering in Phase 1

**Status**: 🟡 Accepted  
**Date**: 2025-11-24  
**Deciders**: @architect-supervisor  
**Impact**: 🟢 Medium  
**Constitution Deviation**: ❌ No  

### Context
Phase 1 establishes the core architecture. The question is whether to include Pygame rendering or focus purely on backend systems.

**Trade-off**: Visual progress vs solid architecture

### Decision
**No rendering in Phase 1**. Focus exclusively on:
- Event store
- State machine
- Game context
- Game loop structure (without rendering)
- Configuration

Rendering will be added in Phase 4 after combat mechanics are implemented.

### Alternatives Considered

#### Alternative 1: Build Everything Together
**Description**: Implement rendering alongside backend

**Pros**:
- Can see visual progress (motivating)
- Test UI early
- More "complete" feeling

**Cons**:
- Rendering is complex (sprites, animations, layers)
- Distracts from architecture focus
- Harder to test game logic
- Risk of coupling logic to rendering
- Longer phase duration

**Reason Rejected**: Too risky for first phase. Architecture must be solid before adding complexity.

#### Alternative 2: Minimal Console Output
**Description**: Add simple console-based visualization

**Pros**:
- Some visual feedback
- Very simple
- Good for debugging

**Cons**:
- Still a distraction
- Not representative of final UI
- Won't be used in production

**Reason Rejected**: Not worth the effort. Unit tests provide sufficient feedback.

### Consequences

#### Positive
- Focus on architecture quality
- Faster Phase 1 completion
- Better test coverage (no rendering to mock)
- Clear separation of concerns enforced
- Can iterate on backend without UI constraints

#### Negative  
- No visual progress (less satisfying)
- Can't demo the game yet
- Need to imagine UI interactions

#### Neutral
- Common approach in backend-first development
- Aligns with TDD practices

### Trade-offs Accepted
**Giving up**: Visual demos, early UI feedback, motivation from seeing graphics  
**Gaining**: Solid architecture, faster iteration, better testing, clear separation

For a learning project where architecture is the primary goal, this is the right trade-off.

### Implementation Notes
- Phase 1 deliverable: Console-based game loop that logs state transitions
- Manual testing via console output
- Phase 4 will add Pygame without modifying core logic (if architecture is clean)

### Success Criteria
- [x] No pygame imports in `src/core/` modules
- [ ] Game logic testable without rendering
- [ ] Clear separation maintained (constitution principle #4)
- [ ] Phase 4 can add rendering without refactoring core

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|-----------|--------|---------------------|-------|
| Lose motivation | 🟡 Med | 🟢 Med | Celebrate architecture wins, track test coverage | @architect-supervisor |
| Hard to visualize gameplay | 🟢 Low | 🟢 Low | Use unit tests as "documentation" | @architect-supervisor |

### Related Decisions
- Depends on: None
- Influences: Phase 4 rendering architecture

### Constitution Compliance
**Principle 4 (Separation of Concerns)**: ✅ Enforced by not mixing rendering with logic

No deviations.

### References
- [Test-Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)

### Changelog
- **2025-11-24**: Decision accepted, moved from PLAN.md to proper ADR format

---

## [DEC-0004]: Hybrid CQRS Architecture

**Status**: 🟡 Accepted  
**Date**: 2025-11-24  
**Deciders**: @architect-supervisor, @data-worker  
**Impact**: 🔴 Critical  
**Constitution Deviation**: ❌ No  
**Related Research**: Topic 1 (Event Sourcing with SQLite)

### Context
Phase 1 starts with pure event sourcing, but we need a clear evolution path for fast gameplay queries and analytics. The question is how to structure read models and dbt transformations without creating dual-write problems.

**Requirements**:
- Single source of truth for all game state
- Fast gameplay queries (< 10ms)
- Batch analytics for insights
- Clear evolution path from Phase 1 to Phase 2+
- Learning goal: Real-world CQRS patterns

### Decision
Implement **Hybrid CQRS with Two Parallel Paths**:

**Phase 1 (Current)**: Pure event sourcing
- Single `game_events` table with JSON `event_data`
- No read models yet
- All queries scan events directly

**Phase 2+ (Future)**: Hybrid CQRS
- **App Path**: Synchronously updates SQLite read models (`player_state`, `inventory_state`, etc.) via event handlers
- **dbt Path**: Independently reads `game_events` JSON, transforms into DuckDB analytics tables
- **Single Source of Truth**: `game_events` table (JSON) is authoritative
- **No Dual-Write**: App writes events once; read models and analytics derive from events

### Alternatives Considered

#### Alternative 1: Pure Event Sourcing Forever
**Description**: Never create read models, always query events

**Pros**:
- Simplest approach
- Perfect audit trail
- No synchronization issues

**Cons**:
- Slow queries (scan all events every time)
- Complex business logic queries
- Performance degrades over time
- Not practical for real-time gameplay

**Reason Rejected**: Violates constitution principle #14 (60 FPS target). Event scans will become too slow.

#### Alternative 2: dbt Reads from Read Models
**Description**: App maintains read models, dbt transforms those

**Pros**:
- dbt works with structured tables (easier)
- Faster dbt processing

**Cons**:
- **Violates single source of truth**
- If read models have bugs, analytics inherit them
- Couples app and analytics pipelines
- Harder to replay/fix historical data

**Reason Rejected**: Blurs CQRS boundaries. Read models should be disposable projections, not the source for analytics.

#### Alternative 3: Event Streaming to DuckDB
**Description**: Stream events to DuckDB in real-time, app queries DuckDB

**Pros**:
- DuckDB handles both OLTP and OLAP
- One database

**Cons**:
- Complex streaming infrastructure
- DuckDB not optimized for OLTP writes
- Coupling between gameplay and analytics
- Overkill for single-player game

**Reason Rejected**: Too complex for current needs, violates constitution principle #13 (database separation).

### Consequences

#### Positive
- **Clear separation**: App and dbt operate independently
- **Single source of truth**: `game_events` is authoritative
- **Disposable read models**: Can rebuild from events anytime
- **Learning value**: Real-world CQRS pattern
- **Flexibility**: dbt can transform events differently than app needs
- **Historical replay**: dbt can reprocess events for new insights

#### Negative  
- **Two systems to maintain**: App event handlers + dbt models
- **Eventual consistency**: dbt runs async, analytics lag behind gameplay
- **JSON parsing overhead**: dbt must parse JSON for every event
- **More complex testing**: Need to test both paths

#### Neutral
- Standard CQRS trade-off: complexity for performance
- Common pattern in event-sourced systems

### Trade-offs Accepted
**Giving up**: Simplicity of single path, real-time analytics  
**Gaining**: Fast gameplay, flexible analytics, clear boundaries, learning

For a project focused on learning event sourcing and dbt, this trade-off is ideal.

### Implementation Notes

**Phase 1: Pure Event Sourcing**
```sql
CREATE TABLE game_events (
    event_id TEXT PRIMARY KEY,
    event_timestamp REAL NOT NULL,
    session_id TEXT NOT NULL,
    timeline_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    aggregate_id TEXT,
    aggregate_type TEXT,
    event_data TEXT,  -- JSON with full context
    metadata TEXT     -- JSON with metadata
);
```

**Phase 2+: App Read Models** (SQLite)
```python
# Event handler pattern
def handle_player_moved(event: GameEvent):
    """Update player_state read model on PlayerMoved event."""
    data = json.loads(event.event_data)
    conn.execute("""
        UPDATE player_state 
        SET position_x = ?, position_y = ?, current_area = ?
        WHERE player_id = ?
    """, (data['x'], data['y'], data['area'], event.aggregate_id))
```

**Phase 2+: dbt Analytics** (DuckDB)
```sql
-- dbt model: staging/stg_player_events.sql
SELECT 
    event_id,
    event_timestamp,
    json_extract_string(event_data, '$.player_id') AS player_id,
    json_extract_string(event_data, '$.x') AS position_x,
    json_extract_string(event_data, '$.y') AS position_y
FROM {{ source('game', 'game_events') }}
WHERE event_type = 'PlayerMoved'
```

### Success Criteria
- [x] Schema supports JSON event storage
- [ ] App event handlers update read models (Phase 2+)
- [ ] dbt parses JSON independently (Phase 2+)
- [ ] Read models can be rebuilt from events
- [ ] Analytics lag is acceptable (< 5 minutes for dbt runs)
- [ ] No dual-write bugs (events are single source of truth)

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|-----------|--------|---------------------|-------|
| JSON parsing performance | 🟢 Low | 🟡 High | DuckDB is fast at JSON, benchmark early | @data-worker |
| Read model sync bugs | 🟡 Med | 🟡 High | Comprehensive tests, rebuild script | @data-worker |
| Analytics lag too high | 🟢 Low | 🟢 Med | Incremental dbt models, optimize queries | @data-worker |
| Complexity overwhelms | 🟡 Med | 🟡 High | Start simple (Phase 1), evolve gradually | @architect-supervisor |

### Related Decisions
- Depends on: DEC-0001 (SQLite event store)
- Influences: All future phases (read model design, dbt development)

### Constitution Compliance
**Principle #1 (Event Sourcing)**: ✅ Events are single source of truth  
**Principle #11 (Events Immutable)**: ✅ Events never modified  
**Principle #13 (Database Separation)**: ✅ SQLite (OLTP) + DuckDB (OLAP)

No deviations.

### References
- [CQRS by Martin Fowler](https://martinfowler.com/bliki/CQRS.html)
- [Event Sourcing Projections](https://domaincentric.net/blog/event-sourcing-projections)
- Research Topic 1: Event Sourcing with SQLite

### Changelog
- **2025-11-24**: Decision accepted based on Research Topic 1 findings

---

## [DEC-0005]: Threading Over Asyncio for AI

**Status**: 🟡 Accepted  
**Date**: 2025-11-24  
**Deciders**: @architect-supervisor, @ai-worker, @ai-integration-supervisor  
**Impact**: 🔴 Critical  
**Constitution Deviation**: ❌ No  
**Related Research**: Topic 4 (Async AI Integration), Topic 2 (Pygame Integration)

### Context
Phase 4 will integrate Ollama for AI Dungeon Master capabilities. AI calls must not block the game loop (60 FPS target). The question is whether to use full asyncio or threading for async integration.

**Requirements**:
- Non-blocking AI calls (< 5s timeout)
- Compatible with Pygame's synchronous event loop
- Simple to debug and maintain
- Fallback to rule-based content on failure

### Decision
Use **Threading + Queue Pattern** for AI integration, not full asyncio.

**Implementation**:
- Background thread processes AI requests from queue
- Game loop submits requests (non-blocking)
- Game loop polls response queue every frame
- Automatic fallback if queue full or request times out

### Alternatives Considered

#### Alternative 1: Full Asyncio Integration
**Description**: Convert game loop to async, use `aiohttp` for Ollama

**Pros**:
- "Modern" Python approach
- Better for 100+ concurrent requests
- Async ecosystem support

**Cons**:
- **Pygame isn't async-native** (requires wrapper)
- Need `aiosqlite` instead of standard SQLite
- Complex event loop management
- Steep learning curve
- Harder debugging (async stack traces)
- Overkill for single-player (< 10 concurrent requests)

**Reason Rejected**: Adds massive complexity for minimal benefit. Threading is sufficient for our use case.

#### Alternative 2: Synchronous Calls with Timeout
**Description**: Block game loop during AI calls, enforce timeout

**Pros**:
- Simplest implementation
- No threading/async complexity

**Cons**:
- **Violates constitution principle #9** (non-blocking AI)
- **Violates principle #14** (60 FPS target)
- Game freezes for up to 5 seconds
- Terrible player experience

**Reason Rejected**: Unacceptable UX, violates core principles.

#### Alternative 3: Hybrid (asyncio.run_in_executor)
**Description**: Use threading under the hood via asyncio

**Pros**:
- Async interface
- Threading implementation

**Cons**:
- Worst of both worlds (async complexity + threading)
- No benefit over pure threading
- Still need async event loop

**Reason Rejected**: Adds complexity without benefit.

### Consequences

#### Positive
- Simple, well-understood pattern
- Compatible with Pygame's sync loop
- Works with standard `requests` library
- Easy debugging (linear stack traces)
- Familiar to most Python developers
- Sufficient performance for single-player

#### Negative  
- Not "modern" async Python
- Manual queue management
- Can't handle 100+ concurrent requests (not needed)

#### Neutral
- Standard approach for Pygame + background tasks
- Same pattern used in many Pygame projects

### Trade-offs Accepted
**Giving up**: Async ecosystem, theoretical scalability  
**Gaining**: Simplicity, Pygame compatibility, easier debugging

For a single-player RPG learning project, this is the clear winner.

### Implementation Notes

**AIRequestQueue Pattern** (from Research Topic 4):
```python
from threading import Thread
from queue import Queue

class AIRequestQueue:
    def __init__(self):
        self.request_queue = Queue(maxsize=10)
        self.response_queue = Queue()
        self._worker = Thread(target=self._process, daemon=True)
        self._worker.start()
    
    def submit_request(self, request: AIRequest) -> None:
        """Non-blocking submission."""
        try:
            self.request_queue.put(request, block=False)
        except Full:
            # Queue full: Use fallback immediately
            request.fallback()
    
    def process_responses(self) -> None:
        """Called every frame in game loop."""
        while not self.response_queue.empty():
            response = self.response_queue.get_nowait()
            # Trigger callback with AI response
```

**Integration with Game Loop**:
```python
# In game loop (every frame)
ai_queue.process_responses()  # ~0.1ms overhead
```

### Success Criteria
- [ ] AI requests don't block game loop (Phase 4)
- [ ] 60 FPS maintained with 10 concurrent AI requests
- [ ] Timeout enforced at 5 seconds
- [ ] Fallbacks triggered on failure
- [ ] Queue backpressure prevents memory bloat
- [ ] Clean shutdown on game exit

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|-----------|--------|---------------------|-------|
| Threading bugs | 🟡 Med | 🟡 High | Comprehensive tests, simple design | @ai-worker |
| Performance insufficient | 🟢 Low | 🟡 High | Benchmark early, can migrate to asyncio if needed | @ai-integration-supervisor |
| Queue overflow | 🟢 Low | 🟢 Med | Fixed queue size, immediate fallback | @ai-worker |

### Related Decisions
- Depends on: DEC-0006 (game loop structure)
- Influences: Phase 4 AI integration

### Constitution Compliance
**Principle #9 (Async AI)**: ✅ Threading ensures non-blocking  
**Principle #9 (5s Timeout)**: ✅ Enforced at HTTP request level  
**Principle #9 (Fallbacks)**: ✅ Every request has rule-based fallback  
**Principle #14 (60 FPS)**: ✅ ~0.1ms overhead per frame

No deviations.

### References
- Research Topic 4: Async AI Integration
- Research Topic 2: Pygame Event Loop Integration
- [Python Threading Documentation](https://docs.python.org/3/library/threading.html)

### Changelog
- **2025-11-24**: Decision accepted based on Research Topics 2 and 4

---

## [DEC-0006]: Fixed Timestep Game Loop

**Status**: 🟡 Accepted  
**Date**: 2025-11-24  
**Deciders**: @architect-supervisor, @game-logic-worker, @pygame-worker  
**Impact**: 🔴 Critical  
**Constitution Deviation**: ❌ No  
**Related Research**: Topic 2 (Pygame Event Loop Integration)

### Context
The game loop timing model affects determinism, testing, and player experience. Need to decide between fixed timestep, variable timestep, or hybrid approaches.

**Requirements**:
- Deterministic gameplay (same inputs = same outputs)
- Smooth rendering at 60 FPS
- Testable (consistent tick rate for tests)
- Handle frame drops gracefully

### Decision
Use **Fixed Timestep with Interpolation** pattern.

**Implementation**:
- **Physics/Logic**: 60 Hz fixed timestep (16.67ms per tick)
- **Rendering**: Variable framerate with interpolation
- **Frame drops**: Accumulate time, catch up with multiple logic ticks
- **Max catch-up**: 10 ticks per frame (prevent spiral of death)

### Alternatives Considered

#### Alternative 1: Variable Timestep
**Description**: Update logic based on actual elapsed time (delta time)

**Pros**:
- Simpler implementation
- No interpolation needed
- Adapts to any framerate

**Cons**:
- **Non-deterministic** (timing-dependent bugs)
- Harder to test (variable delta time)
- Physics instability with large deltas
- Replay systems become complex

**Reason Rejected**: RPG needs deterministic behavior for event sourcing and timeline branching. Variable timestep would make replay unreliable.

#### Alternative 2: Pure Fixed Timestep (No Interpolation)
**Description**: Lock both logic and rendering to 60 FPS

**Pros**:
- Simplest fixed timestep
- Perfectly deterministic

**Cons**:
- Choppy on displays != 60 Hz
- Wasted CPU if rendering faster than 60 FPS
- No visual smoothness benefit

**Reason Rejected**: Unnecessarily rigid. Interpolation provides smoother visuals at no cost to determinism.

#### Alternative 3: Semi-Fixed (Gaffer on Games)
**Description**: Fixed timestep with variable render time and interpolation

**Pros**:
- Deterministic logic
- Smooth rendering
- Industry standard

**Cons**:
- More complex than variable
- Interpolation adds code

**Reason Accepted**: This is our choice (DEC-0006). Best of both worlds.

### Consequences

#### Positive
- **Deterministic gameplay**: Reproducible for testing and replay
- **Smooth rendering**: Interpolation on fast displays
- **Event sourcing compatible**: Fixed ticks make event replay reliable
- **Testable**: Can control tick rate in tests
- **Standard pattern**: Well-documented (Gaffer on Games)

#### Negative  
- More complex than variable timestep
- Need interpolation logic for rendering (Phase 4+)
- Slightly higher CPU on frame drops

#### Neutral
- Common approach in professional game engines
- ~150 lines of code

### Trade-offs Accepted
**Giving up**: Implementation simplicity  
**Gaining**: Determinism, testability, smooth rendering

For an event-sourced RPG with timeline branching, determinism is critical.

### Implementation Notes

**Game Loop Structure** (from Research Topic 2):
```python
class GameLoop:
    TARGET_FPS = 60
    TICK_RATE = 1.0 / TARGET_FPS  # 16.67ms
    MAX_FRAME_SKIP = 10  # Prevent spiral of death
    
    def run(self):
        accumulator = 0.0
        last_time = time.perf_counter()
        
        while self.running:
            current_time = time.perf_counter()
            frame_time = current_time - last_time
            last_time = current_time
            
            accumulator += frame_time
            
            # Fixed timestep logic updates
            ticks = 0
            while accumulator >= self.TICK_RATE and ticks < self.MAX_FRAME_SKIP:
                self.update(self.TICK_RATE)  # Fixed delta
                accumulator -= self.TICK_RATE
                ticks += 1
            
            # Variable framerate rendering (Phase 4+)
            alpha = accumulator / self.TICK_RATE  # Interpolation factor
            self.render(alpha)
```

**Key Points**:
- Logic always uses `16.67ms` delta (deterministic)
- Rendering interpolates between states (smooth)
- Frame drops trigger catch-up (max 10 ticks)
- Spiral of death prevented by `MAX_FRAME_SKIP`

### Success Criteria
- [ ] Logic runs at exactly 60 Hz (measured over 1000 frames)
- [ ] Deterministic: Same input sequence produces same events
- [ ] Frame drops handled gracefully (no crash)
- [ ] Tests can control tick rate
- [ ] Rendering smooth on 120 Hz displays (Phase 4+)

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|-----------|--------|---------------------|-------|
| Spiral of death (CPU overload) | 🟡 Med | 🟡 High | MAX_FRAME_SKIP limit, performance optimization | @game-logic-worker |
| Interpolation bugs | 🟢 Low | 🟢 Med | Only interpolate rendering, not logic | @pygame-worker |
| Testing complexity | 🟢 Low | 🟢 Med | Mock time in tests, inject clock | @game-logic-worker |

### Related Decisions
- Depends on: DEC-0002 (state machine needs deterministic ticks)
- Influences: All gameplay systems, rendering

### Constitution Compliance
**Principle #14 (60 FPS Target)**: ✅ Fixed 60 Hz tick rate  
**Principle #1 (Event Sourcing)**: ✅ Deterministic ticks enable reliable replay

No deviations.

### References
- [Fix Your Timestep! by Glenn Fiedler](https://gafferongames.com/post/fix_your_timestep/)
- Research Topic 2: Pygame Event Loop Integration
- [Game Programming Patterns - Game Loop](https://gameprogrammingpatterns.com/game-loop.html)

### Changelog
- **2025-11-24**: Decision accepted based on Research Topic 2

---

## [DEC-0007]: Pydantic Settings for Configuration

**Status**: 🟡 Accepted  
**Date**: 2025-11-24  
**Deciders**: @architect-supervisor  
**Impact**: 🟢 Medium  
**Constitution Deviation**: ❌ No  
**Related Research**: Topic 5 (Configuration Management)

### Context
Need type-safe configuration management with environment variable support. Several libraries available: pydantic-settings, dynaconf, python-decouple.

**Requirements**:
- Type safety (constitution principle #3)
- Environment variable support (.env files)
- Validation at startup
- Simple to use and maintain

### Decision
Use **Pydantic Settings** (`pydantic-settings` package) with `BaseSettings`.

**Rationale**:
- Type-safe with automatic validation
- Automatic `.env` file loading
- Pydantic already a dependency (constitution, data validation)
- Good IDE support (type hints)
- Industry standard

### Alternatives Considered

#### Alternative 1: dynaconf
**Description**: Flexible configuration library

**Pros**:
- Supports multiple formats (YAML, TOML, JSON)
- Environment-specific configs
- Feature-rich

**Cons**:
- Additional dependency
- More complexity than needed
- Learning curve
- Overkill for simple use case

**Reason Rejected**: Too complex for current needs. Pydantic is simpler and sufficient.

#### Alternative 2: python-decouple
**Description**: Lightweight config library

**Pros**:
- Very simple
- Small footprint
- Good for .env files

**Cons**:
- No type safety
- No validation
- Manual parsing
- Less powerful than Pydantic

**Reason Rejected**: Violates constitution principle #3 (type safety). Pydantic is better.

#### Alternative 3: Manual os.getenv()
**Description**: Read environment variables directly

**Pros**:
- No dependency
- Extremely simple

**Cons**:
- No type safety
- No validation
- No .env file support (need python-dotenv)
- Error-prone

**Reason Rejected**: Too primitive, violates type safety principle.

### Consequences

#### Positive
- Type-safe configuration with validation
- Automatic .env loading
- IDE autocomplete and type checking
- Pydantic already a dependency (no new dependency)
- Clear error messages on invalid config

#### Negative  
- Pydantic is a large dependency (but already used)
- Slightly verbose syntax

#### Neutral
- Industry standard approach
- Well-documented

### Trade-offs Accepted
**Giving up**: Format flexibility (YAML/TOML), minimal dependencies  
**Gaining**: Type safety, validation, simplicity

For a learning project emphasizing type safety, this is ideal.

### Implementation Notes

**Configuration Class** (from Research Topic 5):
```python
from pydantic_settings import BaseSettings
from pydantic import Field

class GameConfig(BaseSettings):
    """Type-safe game configuration."""
    
    # Database
    database_path: str = Field(default="data/events.db", env="DATABASE_PATH")
    
    # Game Settings
    target_fps: int = Field(default=60, ge=30, le=144, env="TARGET_FPS")
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    
    # AI Settings (Phase 4+)
    ollama_host: str = Field(default="localhost:11434", env="OLLAMA_HOST")
    llm_model: str = Field(default="llama3.2", env="LLM_MODEL")
    ai_timeout: float = Field(default=5.0, ge=1.0, le=30.0, env="AI_TIMEOUT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

**Usage**:
```python
config = GameConfig()  # Loads from .env automatically
print(config.target_fps)  # Type-safe access
```

### Success Criteria
- [x] Pydantic Settings added to dependencies
- [ ] GameConfig class created
- [ ] .env.example updated with all variables
- [ ] Validation errors clear and helpful
- [ ] Unit tests for configuration loading

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|-----------|--------|---------------------|-------|
| Config validation too strict | 🟢 Low | 🟢 Low | Sensible defaults, clear error messages | @architect-supervisor |
| Dependency size | 🟢 Low | 🟢 Low | Already using Pydantic | @architect-supervisor |

### Related Decisions
- Depends on: None
- Influences: All system initialization

### Constitution Compliance
**Principle #3 (Type Safety)**: ✅ Pydantic provides full type safety  
**Principle #6 (Error Handling)**: ✅ Clear validation errors

No deviations.

### References
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- Research Topic 5: Configuration Management

### Changelog
- **2025-11-24**: Decision accepted based on Research Topic 5

---

## [DEC-0008]: pytest Testing Stack

**Status**: 🟡 Accepted  
**Date**: 2025-11-24  
**Deciders**: @architect-supervisor  
**Impact**: 🟡 High  
**Constitution Deviation**: ❌ No  
**Related Research**: Topic 6 (Testing Strategy)

### Context
Need comprehensive testing strategy for Phase 1 and beyond. Must support unit tests, integration tests, async tests (Phase 4+), and achieve >= 80% coverage.

**Requirements**:
- Unit testing framework
- Mocking support
- Async test support (Phase 4+)
- Coverage tracking
- Fast test execution

### Decision
Use **pytest + unittest.mock + pytest-asyncio** testing stack.

**Rationale**:
- pytest is industry standard
- unittest.mock built-in (no extra dependency)
- pytest-asyncio for future AI tests
- Already configured in project
- Excellent fixture system

### Alternatives Considered

#### Alternative 1: unittest (Standard Library)
**Description**: Python's built-in testing framework

**Pros**:
- No dependency
- Built-in to Python
- Familiar to many developers

**Cons**:
- More verbose than pytest
- Weaker fixture system
- Less powerful assertions
- No async support out-of-the-box

**Reason Rejected**: pytest is superior in every way. Already configured.

#### Alternative 2: pytest + pytest-mock
**Description**: Use pytest-mock instead of unittest.mock

**Pros**:
- Cleaner syntax
- pytest-specific features

**Cons**:
- Additional dependency
- unittest.mock is sufficient
- Not significantly better

**Reason Rejected**: unittest.mock is built-in and sufficient. No need for extra dependency.

### Consequences

#### Positive
- Industry standard testing approach
- Excellent fixture system (reusable test data)
- Clear assertion errors
- Async support for Phase 4+
- Fast test execution (in-memory database)
- Good IDE integration

#### Negative  
- pytest-asyncio adds dependency (but needed for Phase 4)
- Learning curve if unfamiliar with fixtures

#### Neutral
- Well-documented and widely used
- Large ecosystem of plugins

### Trade-offs Accepted
**Giving up**: Minimalism (stdlib only)  
**Gaining**: Productivity, clarity, async support

For a project with AI integration, pytest-asyncio is essential.

### Implementation Notes

**Test Organization** (from Research Topic 6):
```
tests/
├── unit/                    # Fast, isolated tests
│   ├── test_event_store.py
│   ├── test_state_machine.py
│   └── test_config.py
├── integration/             # Cross-system tests
│   ├── test_game_loop.py
│   └── test_ai_integration.py  # Phase 4+
└── fixtures/
    ├── event_fixtures.py    # Reusable test data
    └── game_fixtures.py
```

**Fixture Examples**:
```python
import pytest

@pytest.fixture
def event_store():
    """In-memory database for fast tests."""
    store = EventStore(":memory:")
    yield store
    store.close()

@pytest.fixture
def sample_events():
    """Reusable test events."""
    return [
        GameEvent(event_type="game_start", ...),
        GameEvent(event_type="player_move", ...),
    ]
```

**Async Testing** (Phase 4+):
```python
import pytest

@pytest.mark.asyncio
async def test_ai_request_timeout(ai_queue):
    """Verify AI timeout triggers fallback."""
    # Test async AI behavior
    ...
```

### Success Criteria
- [x] pytest configured in pyproject.toml
- [x] pytest-asyncio added to dependencies
- [ ] Test directory structure created
- [ ] Fixtures for common test data
- [ ] >= 80% coverage on all modules
- [ ] Tests run in < 5 seconds (Phase 1)

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|-----------|--------|---------------------|-------|
| Slow tests (fixtures heavy) | 🟢 Low | 🟢 Med | Use in-memory database, mock external systems | @architect-supervisor |
| Fixture complexity | 🟢 Low | 🟢 Low | Keep fixtures simple, document usage | @architect-supervisor |

### Related Decisions
- Depends on: DEC-0001 (event store needs in-memory testing)
- Influences: All development (TDD approach)

### Constitution Compliance
**Principle #5 (Testing)**: ✅ >= 80% coverage enforced  
**Principle #7 (Documentation)**: ✅ Tests serve as documentation

No deviations.

### References
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- Research Topic 6: Testing Strategy

### Changelog
- **2025-11-24**: Decision accepted based on Research Topic 6

---

## Notes for Completing This Document

Once research is complete:

1. Convert each "Pending Decision" into a full ADR using the template from DECISIONS_TEMPLATE.md
2. Document alternatives considered, trade-offs, and rationale
3. Link decisions to constitution principles
4. Create GitHub issues for any technical debt
5. Update the Decision Index table

## Constitution Compliance

All decisions will be evaluated against `.cursor/rules/CONSTITUTION.md` principles:

- ✅ Event sourcing integrity (append-only)
- ✅ Dependency injection patterns
- ✅ Type safety requirements
- ✅ Separation of concerns
- ✅ Async/await for AI
- ✅ Performance targets

**Deviations Tracking**: If any decision requires a constitution deviation, it will be documented here with justification and remediation plan.

---

## Related Documents
- `research.md` - Research findings informing these decisions
- `PLAN.md` - Implementation plan based on these decisions
- `.cursor/rules/CONSTITUTION.md` - Development principles
- `assignments/templates/DECISIONS_TEMPLATE.md` - ADR template

---

## Decision Approval

**Phase Lead**: @architect-supervisor  
**Reviewed By**: [To be filled]  
**Approval Date**: [To be filled]  

**Sign-off Checklist**:
- [x] All pending decisions resolved (8 total decisions documented)
- [x] Research findings documented (all 6 topics complete)
- [x] Constitution compliance verified (0 deviations)
- [x] Technical debt tracked (none identified)
- [x] Implementation guidance clear (each ADR includes implementation notes)
- [x] Ready for PLAN.md execution

