# Research Document: Phase 1 - Core Game Loop

**Phase**: Phase 1  
**Created**: 2025-11-24  
**Status**: 🔄 In Progress  

## Overview
This phase establishes the foundation of Temporal Echoes with event sourcing, state management, and the core game loop. Research focuses on validating architectural patterns, confirming tech stack compatibility, and identifying potential performance bottlenecks.

## Research Summary

**Total Topics**: 6  
**Completed**: 5 (Topics 1, 2, 3, 5, 6)  
**In Progress**: 0  
**Remaining**: 1 (Topic 4)  
**High Priority Remaining**: 1  
**Research Time**: 1 hour remaining (estimated)  

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

**Hybrid CQRS Architecture - Two Parallel Paths** (Phase 2+):

**Key Insight**: App and dbt BOTH read from `game_events`, but process differently:

```
game_events (JSON - Single Source of Truth)
    ├─> App Event Handlers ────> SQLite Read Models ──> Fast Gameplay Queries
    └─> dbt Transformations ───> DuckDB Analytics ────> Historical Insights
```

**Path 1: App Maintains Read Models (Real-Time Gameplay)**
```python
# App synchronously updates read models
class EventStore:
    def append_event(self, event: GameEvent) -> None:
        with self.conn:
            # 1. Write event (source of truth)
            self._write_event(event)
            
            # 2. Update read models (fast gameplay queries)
            self._update_player_state(event)
            self._update_inventory_state(event)
```

**Path 2: dbt Parses JSON (Batch Analytics)**
```sql
-- dbt IGNORES SQLite read models entirely
-- dbt reads game_events JSON and transforms independently

-- dbt/models/sources.yml
sources:
  - name: game
    description: Raw game events from SQLite
    tables:
      - name: game_events
        description: Append-only event log with JSON payloads

-- dbt/models/staging/stg_events.sql
-- Parse JSON from raw events (dbt's job, not app's)
WITH parsed_events AS (
    SELECT
        event_id,
        event_timestamp,
        event_type,
        aggregate_id,
        aggregate_type,
        timeline_id,
        session_id,
        -- Parse JSON fields
        json_extract(event_data, '$.player_name') AS player_name,
        json_extract(event_data, '$.level') AS level,
        json_extract(event_data, '$.health') AS health,
        json_extract(event_data, '$.position_x') AS position_x,
        json_extract(event_data, '$.position_y') AS position_y,
        json_extract(event_data, '$.action') AS action,
        json_extract(event_data, '$.outcome') AS outcome
    FROM {{ source('game', 'game_events') }}
)
SELECT * FROM parsed_events

-- dbt/models/intermediate/int_player_timeline_state.sql
-- Rebuild player state from events (CQRS in dbt!)
SELECT
    aggregate_id AS player_id,
    timeline_id,
    event_timestamp,
    player_name,
    level,
    health,
    position_x,
    position_y,
    action,
    outcome,
    ROW_NUMBER() OVER (
        PARTITION BY aggregate_id, timeline_id 
        ORDER BY event_timestamp DESC
    ) AS recency_rank
FROM {{ ref('stg_events') }}
WHERE aggregate_type = 'player'

-- dbt/models/analytics/current_player_state_by_timeline.sql
-- Latest state per timeline (analytics CQRS)
SELECT
    player_id,
    timeline_id,
    player_name,
    level,
    health,
    position_x,
    position_y,
    event_timestamp AS last_updated
FROM {{ ref('int_player_timeline_state') }}
WHERE recency_rank = 1

-- dbt/models/analytics/timeline_divergence_analysis.sql
-- Compare player choices across timelines
WITH timeline_actions AS (
    SELECT
        timeline_id,
        parent_timeline_id,
        event_type,
        action,
        outcome,
        COUNT(*) as action_count
    FROM {{ ref('stg_events') }}
    WHERE event_type IN ('player_action', 'choice_made')
    GROUP BY timeline_id, parent_timeline_id, event_type, action, outcome
)
SELECT
    t1.timeline_id AS timeline_1,
    t2.timeline_id AS timeline_2,
    t1.action,
    t1.outcome AS outcome_timeline_1,
    t2.outcome AS outcome_timeline_2,
    CASE 
        WHEN t1.outcome != t2.outcome THEN 'DIVERGED'
        ELSE 'SAME'
    END AS divergence_status
FROM timeline_actions t1
JOIN timeline_actions t2 
    ON t1.action = t2.action 
    AND t1.timeline_id != t2.timeline_id
WHERE t2.parent_timeline_id = t1.timeline_id
```

**Why This Hybrid Approach is Superior**:

1. **Single Source of Truth**: `game_events` (JSON) is the only authoritative source
2. **No Dual-Write Problem**: App writes events once, two systems read independently
3. **Gameplay Performance**: SQLite read models = fast combat/inventory queries (< 1ms)
4. **Analytics Flexibility**: dbt can reprocess events anytime, change transformations
5. **Schema Evolution**: dbt handles JSON parsing changes without app changes
6. **ELT Pattern**: True Extract-Load-Transform (dbt's sweet spot)
7. **Separation of Concerns**: Gameplay logic separate from analytics logic
8. **Reprocessability**: Can rebuild analytics from scratch by re-running dbt
9. **Timeline Comparisons**: dbt excels at complex cross-timeline analytics

**Comparison**: App Read Models vs dbt Analytics

| Aspect | SQLite Read Models (App) | DuckDB Analytics (dbt) |
|--------|--------------------------|------------------------|
| **Purpose** | Real-time gameplay queries | Historical analysis |
| **Update** | Synchronous (same transaction) | Batch (scheduled dbt runs) |
| **Latency** | < 1ms | Minutes (batch processing) |
| **Use Case** | "What's player health?" | "How do choices differ across timelines?" |
| **Query Type** | Simple lookups, JOINs | Aggregations, window functions, pivots |
| **Rebuild** | Event replay (if corrupted) | `dbt run` (anytime) |
| **Maintained By** | Python app code | SQL dbt models |

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
- **Hybrid CQRS Architecture**: Two parallel paths from events
  - App maintains read models for real-time gameplay queries
  - dbt transforms JSON events for batch analytics (independent of read models)
- **Events as Single Source of Truth**: Both app and dbt read from `game_events` JSON
- **No Dual-Write Problem**: App writes events once, read models + analytics derive from it
- **dbt Parses JSON**: Analytics layer owns JSON transformation logic, not the app
- **aggregate_id + aggregate_type** pattern enables entity-level event queries
- **Proper indexing on timeline_id** is critical for replay performance
- **Timeline Branching**: Read models = fast gameplay, dbt = deep timeline analysis
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

**Phase 2+ (Hybrid CQRS Evolution)**:
10. **App Side**: Create read model tables (player_state, inventory_state, etc.)
11. **App Side**: Update read models synchronously in same transaction as event write
12. **App Side**: Add last_event_id to all read models (rebuild capability)
13. **App Side**: Implement rebuild_read_models() for recovery from events
14. **App Side**: Use read models for gameplay queries, events for audit trail
15. **dbt Side**: Create dbt models that parse game_events JSON independently
16. **dbt Side**: dbt IGNORES read models, only reads game_events (JSON is source)
17. **dbt Side**: dbt models handle all JSON parsing and transformation logic
18. **dbt Side**: Timeline comparisons in dbt using complex analytics queries

**CQRS Migration Path**:
- **Phase 1**: Events only (keep it simple, no read models yet)
- **Phase 2**: Add app read models (player_state, inventory_state) + dbt staging models
- **Phase 3**: Add timeline_state + combat_state + dbt analytics models
- **Phase 4**: Optimize based on query patterns, refine dbt transformations

**Hybrid Design Pattern**:
```
Write Path:     Command → Event → game_events (JSON)
                                      │
                    ┌─────────────────┴────────────────┐
                    │                                  │
Read Path 1 (App):  │                                  │
  Update Read Models (synchronous)                     │
  Query → player_state, inventory_state (fast!)        │
                                                       │
Read Path 2 (dbt):                                     │
  Extract game_events → DuckDB raw layer              │
  Transform JSON → Staging → Intermediate → Analytics │
  Query → Analytics tables (historical insights)      │
                                                       │
Rebuild:            │                                  │
  App: game_events → Replay → Reconstruct Read Models │
  dbt: game_events → `dbt run` → Rebuild Analytics ───┘
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
**Status**: ✅ Complete  
**Priority**: 🔴 High  
**Assigned To**: @pygame-worker  
**Completed**: 2025-11-24

**Why Research Needed**:
The game loop must integrate Pygame's event system with our state machine and maintain 60 FPS while performing async AI calls and database writes.

**Questions to Answer**:
1. ✅ How to integrate async/await with Pygame's synchronous event loop?
2. ✅ What's the best approach for fixed vs variable timestep?
3. ✅ How to prevent blocking from database writes in game loop?
4. ✅ Can we achieve 60 FPS with SQLite writes per frame?
5. ✅ What Pygame version is compatible with Python 3.13?

**Research Sources**:
- [x] Pygame 2.6.x documentation
- [x] "Fix Your Timestep" by Glenn Fiedler
- [x] Pygame + asyncio integration patterns
- [x] Game loop architecture patterns
- [x] Python 3.13 compatibility matrix

**Research Methodology**:
- Review Pygame community patterns for async integration
- Research frame timing and delta time calculations
- Investigate pygame-menu or similar for UI state management
- Benchmark Pygame + SQLite write performance

**Findings**:

**IMPORTANT CONTEXT**: Phase 1 has **NO rendering** (per DEC-0003), so we're building the game loop **structure** without Pygame initially. Pygame integration happens in Phase 4. This research informs the architecture.

**1. Python 3.13 + Pygame Compatibility**

**Status**: ✅ **Pygame 2.6.1 supports Python 3.13**

From pyproject.toml:
```toml
python = "^3.13"
pygame = "^2.6.1"
```

**Verification**:
- Pygame 2.6.0+ added Python 3.13 support (released October 2024)
- Pygame 2.6.1 is stable and production-ready
- No known compatibility issues with Python 3.13.3

**2. Game Loop Architecture - Fixed Timestep**

**Decision**: Use **Fixed Timestep with Accumulator** pattern (from "Fix Your Timestep")

**Why Fixed Over Variable**:
- ✅ **Deterministic**: Same input always produces same output (critical for event sourcing)
- ✅ **Replay-able**: Event replay produces identical results
- ✅ **Predictable Physics**: No frame-rate dependent behavior
- ✅ **Easier to Test**: Tests run at consistent speed
- ❌ **Con**: More complex than variable timestep (worth it for benefits)

**Implementation Pattern**:
```python
import time
from typing import Callable

class GameLoop:
    """Fixed timestep game loop with accumulator."""
    
    def __init__(self, fps_target: int = 60):
        self.fps_target = fps_target
        self.dt = 1.0 / fps_target  # Fixed delta time (0.0166... for 60 FPS)
        self.accumulator = 0.0
        self.current_time = time.perf_counter()
        self.running = False
    
    def run(self, 
            update_callback: Callable[[float], None],
            render_callback: Callable[[float], None]) -> None:
        """
        Run game loop with fixed timestep.
        
        Args:
            update_callback: Called with fixed dt for game logic
            render_callback: Called with interpolation factor for rendering
        """
        self.running = True
        
        while self.running:
            # Measure frame time
            new_time = time.perf_counter()
            frame_time = new_time - self.current_time
            self.current_time = new_time
            
            # Cap frame time to prevent spiral of death
            if frame_time > 0.25:  # Max 250ms (4 FPS minimum)
                frame_time = 0.25
            
            # Add frame time to accumulator
            self.accumulator += frame_time
            
            # Update game logic at fixed timestep
            while self.accumulator >= self.dt:
                update_callback(self.dt)  # Fixed dt every time
                self.accumulator -= self.dt
            
            # Calculate interpolation for smooth rendering
            interpolation = self.accumulator / self.dt
            render_callback(interpolation)
    
    def stop(self) -> None:
        """Stop the game loop."""
        self.running = False
```

**How It Works**:
1. **Frame Time**: Measure actual time elapsed
2. **Accumulator**: Store leftover time between frames
3. **Fixed Update**: Run game logic in fixed increments (always same dt)
4. **Interpolation**: Smooth rendering between logic updates

**Example Usage (Phase 1 - No Rendering)**:
```python
def update_game_logic(dt: float) -> None:
    """Update game state with fixed timestep."""
    # Always receives dt = 0.01666... (for 60 FPS)
    state_machine.update(dt)
    game_context.tick(dt)
    # Log events to SQLite

def render_frame(interpolation: float) -> None:
    """Render (Phase 4+) or log status (Phase 1)."""
    # Phase 1: Just log current state
    print(f"Tick: {game_context.tick_count}, State: {state_machine.current_state.name}")
    
    # Phase 4: Interpolate between previous and current positions
    # player.render_position = lerp(prev_pos, current_pos, interpolation)

game_loop = GameLoop(fps_target=60)
game_loop.run(update_game_logic, render_frame)
```

**3. SQLite Write Performance in Game Loop**

**Question**: Can we write events every frame at 60 FPS?

**Answer**: ✅ **Yes, with caveats**

**Performance Analysis**:
- **SQLite WAL mode**: 1000+ writes/second possible
- **60 FPS** = 60 writes/second = **well within capability**
- **Single event write**: ~1ms with WAL mode
- **Frame budget at 60 FPS**: 16.67ms per frame
- **Event write overhead**: ~6% of frame budget (acceptable)

**Best Practice - Event Buffering**:
```python
class EventBuffer:
    """Buffer events and batch write every N frames."""
    
    def __init__(self, event_store: EventStore, flush_interval: int = 60):
        self.event_store = event_store
        self.buffer: list[GameEvent] = []
        self.flush_interval = flush_interval  # Frames between flushes
        self.frame_count = 0
    
    def add_event(self, event: GameEvent) -> None:
        """Add event to buffer."""
        self.buffer.append(event)
    
    def tick(self) -> None:
        """Called every frame. Flush if interval reached."""
        self.frame_count += 1
        
        if self.frame_count >= self.flush_interval or len(self.buffer) >= 10:
            self.flush()
    
    def flush(self) -> None:
        """Write all buffered events to database."""
        if not self.buffer:
            return
        
        # Batch write all events in single transaction
        with self.event_store.conn:
            for event in self.buffer:
                self.event_store._write_event(event)
        
        self.buffer.clear()
        self.frame_count = 0
```

**Strategy**:
- **Phase 1**: Write events immediately (simple, low event volume)
- **Phase 2+**: Buffer events, flush every 60 frames (1 second) or when buffer > 10 events
- **Critical events**: Flush immediately (save game, timeline branch)

**4. Async AI Integration (Phase 4+)**

**Problem**: Pygame is synchronous, AI calls should be async (non-blocking)

**Solution Options**:

**Option A: asyncio.run_in_executor (Recommended)**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class GameLoop:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.loop = asyncio.new_event_loop()
        self.pending_ai_tasks: dict[str, asyncio.Future] = {}
    
    async def request_ai_narrative(self, context: dict) -> str:
        """Async AI call (doesn't block game loop)."""
        return await ai_manager.generate_narrative(context)
    
    def update(self, dt: float) -> None:
        """Synchronous game loop update."""
        # Start AI task in background
        if needs_ai_narrative:
            task_id = str(uuid.uuid4())
            future = asyncio.run_coroutine_threadsafe(
                self.request_ai_narrative(context),
                self.loop
            )
            self.pending_ai_tasks[task_id] = future
        
        # Check completed AI tasks
        completed = []
        for task_id, future in self.pending_ai_tasks.items():
            if future.done():
                try:
                    result = future.result(timeout=0)  # Non-blocking
                    self._handle_ai_response(result)
                    completed.append(task_id)
                except Exception as e:
                    logger.error(f"AI task failed: {e}")
                    completed.append(task_id)
        
        # Remove completed tasks
        for task_id in completed:
            del self.pending_ai_tasks[task_id]
```

**Option B: Threading with Queue (Simpler)**
```python
import queue
import threading

class AIRequestQueue:
    """Thread-safe queue for AI requests/responses."""
    
    def __init__(self, ai_manager: AIManager):
        self.ai_manager = ai_manager
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def request_narrative(self, request_id: str, context: dict) -> None:
        """Queue AI request (non-blocking)."""
        self.request_queue.put((request_id, context))
    
    def get_response(self) -> tuple[str, str] | None:
        """Get completed response (non-blocking)."""
        try:
            return self.response_queue.get_nowait()  # Non-blocking
        except queue.Empty:
            return None
    
    def _worker(self) -> None:
        """Background worker thread."""
        while True:
            request_id, context = self.request_queue.get()
            
            try:
                # Blocking call, but in background thread
                result = asyncio.run(
                    self.ai_manager.generate_narrative(context)
                )
                self.response_queue.put((request_id, result))
            except Exception as e:
                logger.error(f"AI request {request_id} failed: {e}")
                self.response_queue.put((request_id, f"[AI Error: {e}]"))

# In game loop
def update(dt: float):
    # Check for AI responses (non-blocking)
    response = ai_queue.get_response()
    if response:
        request_id, narrative = response
        game_context.apply_narrative(narrative)
```

**Recommendation**: **Option B (Threading + Queue)** for Phase 4
- Simpler to understand and debug
- No asyncio event loop management
- Works seamlessly with synchronous game loop
- Thread-safe queues handle synchronization

**5. Phase 1 Game Loop (Console-Based, No Rendering)**

```python
# src/core/game_loop.py
import time
from typing import Callable, Optional

class GameLoop:
    """
    Fixed timestep game loop for Phase 1 (console-based).
    
    Phase 1: No rendering, just state updates and logging
    Phase 4: Add Pygame rendering with interpolation
    """
    
    def __init__(self, config: GameConfig):
        self.fps_target = config.fps_target
        self.dt = 1.0 / self.fps_target
        self.accumulator = 0.0
        self.current_time = time.perf_counter()
        self.running = False
        self.tick_count = 0
    
    def run(self, game_context: GameContext) -> None:
        """Run main game loop."""
        self.running = True
        print(f"Game loop started (target: {self.fps_target} FPS)")
        
        try:
            while self.running:
                new_time = time.perf_counter()
                frame_time = new_time - self.current_time
                self.current_time = new_time
                
                # Cap frame time
                if frame_time > 0.25:
                    frame_time = 0.25
                
                self.accumulator += frame_time
                
                # Fixed timestep updates
                while self.accumulator >= self.dt:
                    self._update(game_context, self.dt)
                    self.accumulator -= self.dt
                
                # Phase 1: Log status every second
                if self.tick_count % self.fps_target == 0:
                    self._log_status(game_context)
                
                # Sleep to maintain target FPS
                self._throttle_framerate()
        
        except KeyboardInterrupt:
            print("\nGame loop interrupted by user")
        finally:
            self.stop()
    
    def _update(self, game_context: GameContext, dt: float) -> None:
        """Update game logic at fixed timestep."""
        self.tick_count += 1
        
        # Update game context (triggers state machine, etc.)
        game_context.update(dt)
    
    def _log_status(self, game_context: GameContext) -> None:
        """Log current game status (Phase 1 only)."""
        state = game_context.state_machine.current_state
        print(f"[Tick {self.tick_count}] State: {state.name}, "
              f"Events: {game_context.event_count}")
    
    def _throttle_framerate(self) -> None:
        """Sleep to maintain target FPS."""
        # Simple throttling (Phase 1)
        # Phase 4: More sophisticated frame pacing
        time.sleep(0.001)  # Minimal sleep to yield CPU
    
    def stop(self) -> None:
        """Stop the game loop."""
        self.running = False
        print(f"Game loop stopped after {self.tick_count} ticks")
```

**6. Pygame Integration (Phase 4)**

**When adding Pygame in Phase 4**:
```python
import pygame

class GameLoopWithPygame(GameLoop):
    """Extended game loop with Pygame rendering."""
    
    def __init__(self, config: GameConfig):
        super().__init__(config)
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.window_width, config.window_height)
        )
        self.clock = pygame.time.Clock()
    
    def run(self, game_context: GameContext) -> None:
        """Run with Pygame event handling and rendering."""
        self.running = True
        
        while self.running:
            # Handle Pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                self._handle_input(event, game_context)
            
            # Fixed timestep updates (same as Phase 1)
            new_time = time.perf_counter()
            frame_time = new_time - self.current_time
            self.current_time = new_time
            
            if frame_time > 0.25:
                frame_time = 0.25
            
            self.accumulator += frame_time
            
            while self.accumulator >= self.dt:
                self._update(game_context, self.dt)
                self.accumulator -= self.dt
            
            # Render with interpolation
            interpolation = self.accumulator / self.dt
            self._render(game_context, interpolation)
            
            # Pygame clock tick
            self.clock.tick(self.fps_target)
        
        pygame.quit()
```

**Key Insights**:
- **Fixed timestep** is superior for deterministic gameplay and event sourcing
- **Pygame 2.6.1 + Python 3.13** are fully compatible
- **SQLite can handle 60 writes/second** easily (1ms per write with WAL mode)
- **Event buffering** is optional for Phase 1, recommended for Phase 2+
- **Async AI integration** via threading + queues (simpler than asyncio event loop)
- **Phase 1 game loop** can be console-based (no Pygame needed yet)
- **Frame time capping** prevents "spiral of death" from long frames
- **Interpolation** enables smooth 60 FPS rendering even if logic runs slower

**Decision**:
**DECIDED**: Fixed timestep game loop with accumulator pattern

**Rationale**:
- Deterministic for event sourcing and replay
- Industry standard ("Fix Your Timestep" pattern)
- Phase 1 can be console-based (no Pygame yet)
- Pygame integration in Phase 4 is straightforward
- SQLite performance is sufficient for 60 FPS event logging

**Implementation Guidance**:

**Phase 1 (Step 4)**:
1. Implement `GameLoop` class with fixed timestep
2. Console-based (no Pygame imports)
3. Log status every second
4. Update game context at fixed dt
5. Write events immediately (simple, low volume)
6. Test loop runs stably for 60+ seconds

**Phase 4 (Pygame Integration)**:
7. Extend to `GameLoopWithPygame`
8. Add Pygame event handling
9. Add rendering with interpolation
10. Add event buffering (flush every 60 frames)
11. Add AI request queue (threading)
12. Test 60 FPS maintained with rendering + AI

**Performance Targets**:
- **Update logic**: < 10ms per frame (60 FPS = 16.67ms budget)
- **Event write**: < 1ms (with WAL mode)
- **Total frame time**: < 16.67ms (60 FPS)

**Confidence Level**: 🟢 High

**References**:
- [Fix Your Timestep - Glenn Fiedler](https://gafferongames.com/post/fix_your_timestep/)
- [Pygame Documentation](https://www.pygame.org/docs/)
- [Python threading + queue](https://docs.python.org/3/library/queue.html)

---

### Topic 3: State Machine Pattern
**Status**: ✅ Complete  
**Priority**: 🔴 High  
**Assigned To**: @game-logic-worker  
**Completed**: 2025-11-24

**Why Research Needed**:
State machine must be robust, testable, and emit events for sourcing. Need to validate transition logic and ensure it supports future timeline branching.

**Questions to Answer**:
1. ✅ What Python library best supports state machines (or roll our own)?
2. ✅ How to structure state transitions for easy testing?
3. ✅ How to emit events during transitions without tight coupling?
4. ✅ Should states be classes or functions?
5. ✅ How to handle nested/hierarchical states?

**Research Sources**:
- [x] Python transitions library
- [x] State pattern in Design Patterns book
- [x] Game Programming Patterns - State chapter
- [x] Python enum best practices
- [x] Existing RPG state machine examples

**Research Methodology**:
- Evaluate transitions vs python-statemachine vs custom implementation
- Review state pattern implementations in Python games
- Research testability of different state machine approaches
- Consider dependency injection for state objects

**Findings**:

**1. Custom Implementation Selected (Per DEC-0002)**

**Decision Already Made**: Custom state machine using Python enum + explicit transition validation.

**Rationale** (from DEC-0002):
- Educational value for learning project
- Full control over implementation
- Easy to understand and debug
- No library overhead or magic
- Simple enough for Phase 1 needs

**2. State Machine Architecture**

**States as Enum** (Not Classes):
```python
from enum import Enum, auto

class GameState(Enum):
    """All possible game states."""
    MENU = auto()
    EXPLORING = auto()
    COMBAT = auto()
    DIALOGUE = auto()
    INVENTORY = auto()
    TIMELINE_VIEW = auto()
    PAUSED = auto()
    GAME_OVER = auto()
```

**Why Enum over Classes**:
- ✅ Type-safe (mypy can validate)
- ✅ Lightweight (no instantiation needed)
- ✅ Simple comparison (`state == GameState.MENU`)
- ✅ Easy to serialize (for save/load)
- ❌ No per-state behavior (not needed for Phase 1)

**3. Transition Validation - Explicit Allow List**

```python
from typing import Dict, Set

class GameStateMachine:
    """State machine with explicit transition rules."""
    
    # Define ALL valid transitions upfront
    ALLOWED_TRANSITIONS: Dict[GameState, Set[GameState]] = {
        GameState.MENU: {
            GameState.EXPLORING,      # Start new game
            GameState.TIMELINE_VIEW,  # View timelines
            GameState.GAME_OVER       # Quit
        },
        GameState.EXPLORING: {
            GameState.COMBAT,         # Encounter enemy
            GameState.DIALOGUE,       # Talk to NPC
            GameState.INVENTORY,      # Open inventory
            GameState.PAUSED,         # Pause game
            GameState.MENU,           # Return to menu
            GameState.TIMELINE_VIEW   # View timeline
        },
        GameState.COMBAT: {
            GameState.EXPLORING,      # Win combat
            GameState.GAME_OVER,      # Lose combat
            GameState.PAUSED          # Pause during combat
        },
        GameState.DIALOGUE: {
            GameState.EXPLORING,      # End dialogue
            GameState.COMBAT,         # Dialogue triggers fight
            GameState.TIMELINE_VIEW   # Dialogue about timelines
        },
        GameState.INVENTORY: {
            GameState.EXPLORING,      # Close inventory
            GameState.COMBAT          # Use item in combat
        },
        GameState.TIMELINE_VIEW: {
            GameState.MENU,           # Return to menu
            GameState.EXPLORING       # Branch timeline
        },
        GameState.PAUSED: {
            GameState.EXPLORING,      # Resume from exploring
            GameState.COMBAT,         # Resume from combat
            GameState.MENU            # Quit to menu
        },
        GameState.GAME_OVER: {
            GameState.MENU            # Restart
        }
    }
    
    def __init__(self, event_store: EventStore):
        """Initialize with dependency injection."""
        self._current_state = GameState.MENU
        self._event_store = event_store
        self._previous_state: Optional[GameState] = None
    
    @property
    def current_state(self) -> GameState:
        """Get current state (read-only)."""
        return self._current_state
    
    def transition(self, to_state: GameState, context: Dict[str, Any]) -> None:
        """
        Transition to new state with validation.
        
        Args:
            to_state: Target state to transition to
            context: Additional context for the transition
            
        Raises:
            StateTransitionError: If transition is invalid
        """
        # Validate transition is allowed
        if not self._is_valid_transition(to_state):
            raise StateTransitionError(
                f"Invalid transition: {self._current_state.name} -> {to_state.name}"
            )
        
        # Store previous state
        from_state = self._current_state
        self._previous_state = from_state
        
        # Emit event BEFORE changing state (for audit trail)
        self._emit_transition_event(from_state, to_state, context)
        
        # Change state
        self._current_state = to_state
    
    def _is_valid_transition(self, to_state: GameState) -> bool:
        """Check if transition is allowed."""
        allowed = self.ALLOWED_TRANSITIONS.get(self._current_state, set())
        return to_state in allowed
    
    def _emit_transition_event(
        self, 
        from_state: GameState, 
        to_state: GameState, 
        context: Dict[str, Any]
    ) -> None:
        """Emit state transition event."""
        event = GameEvent(
            event_id=str(uuid.uuid4()),
            event_timestamp=datetime.utcnow().timestamp(),
            session_id=context.get('session_id', 'unknown'),
            timeline_id=context.get('timeline_id', 'default'),
            event_type='state_transition',
            aggregate_id=context.get('player_id', 'player-1'),
            aggregate_type='game_state',
            event_data=json.dumps({
                'from_state': from_state.name,
                'to_state': to_state.name,
                'reason': context.get('reason', 'user_action'),
                'timestamp': datetime.utcnow().isoformat()
            }),
            metadata=json.dumps(context)
        )
        self._event_store.append_event(event)
    
    def can_transition_to(self, to_state: GameState) -> bool:
        """Check if transition is valid (for UI enabling/disabling)."""
        return self._is_valid_transition(to_state)
    
    def get_valid_transitions(self) -> Set[GameState]:
        """Get all valid transitions from current state."""
        return self.ALLOWED_TRANSITIONS.get(self._current_state, set())
```

**4. Event Emission Pattern**

**Key Design Decision**: Emit events BEFORE state change (for accurate audit trail).

```python
# Event emitted BEFORE state changes
self._emit_transition_event(from_state, to_state, context)
self._current_state = to_state  # State changes after event
```

**Why This Order**:
- ✅ Event shows accurate "from" and "to" states
- ✅ If event write fails, state doesn't change (atomicity)
- ✅ Event replay can reconstruct state history accurately

**5. Dependency Injection for EventStore**

```python
# In main.py or game initialization
event_store = EventStore("data/events.db")
state_machine = GameStateMachine(event_store=event_store)

# NOT like this (violates constitution principle #2):
# state_machine = GameStateMachine()  # Creates EventStore internally ❌
```

**6. Testability Patterns**

**A. Test Valid Transitions**:
```python
def test_valid_transition(state_machine):
    """Test allowed state transition."""
    state_machine.transition(GameState.EXPLORING, context={'player_id': 'p1'})
    assert state_machine.current_state == GameState.EXPLORING
```

**B. Test Invalid Transitions**:
```python
def test_invalid_transition_raises_error(state_machine):
    """Test disallowed transition raises error."""
    with pytest.raises(StateTransitionError) as exc_info:
        # Can't go directly from MENU to COMBAT
        state_machine.transition(GameState.COMBAT, context={})
    
    assert "Invalid transition" in str(exc_info.value)
    assert state_machine.current_state == GameState.MENU  # State unchanged
```

**C. Test Event Emission**:
```python
def test_transition_emits_event(state_machine, event_store_mock):
    """Ensure event emitted on transition."""
    state_machine.transition(GameState.EXPLORING, context={'player_id': 'p1'})
    
    # Verify EventStore.append_event was called
    assert event_store_mock.append_event.called
    
    # Verify event contents
    event = event_store_mock.append_event.call_args[0][0]
    assert event.event_type == 'state_transition'
    assert 'from_state' in json.loads(event.event_data)
    assert 'to_state' in json.loads(event.event_data)
```

**D. Test with Mocked EventStore** (Fast Unit Tests):
```python
from unittest.mock import Mock

@pytest.fixture
def event_store_mock():
    """Mock EventStore to avoid database in tests."""
    return Mock(spec=EventStore)

@pytest.fixture
def state_machine(event_store_mock):
    """State machine with mocked dependencies."""
    return GameStateMachine(event_store=event_store_mock)
```

**7. Nested/Hierarchical States (Future Enhancement)**

**Phase 1**: Flat state machine (simple, proven)

**Phase 2+** (If Needed): Add sub-states:
```python
class CombatSubState(Enum):
    PLAYER_TURN = auto()
    ENEMY_TURN = auto()
    CHOOSING_ACTION = auto()
    ANIMATING = auto()

class GameStateMachine:
    def __init__(self, event_store: EventStore):
        self._current_state = GameState.MENU
        self._combat_sub_state: Optional[CombatSubState] = None
```

**When to Add Hierarchical States**:
- Combat needs turn management (Phase 2)
- Dialogue needs branching choices (Phase 2)
- NOT needed for Phase 1 (premature complexity)

**8. State Machine vs Command Pattern**

**State Machine**: Manages WHAT state we're in  
**Command Pattern**: Manages HOW actions are executed

**They work together**:
```python
# Command triggers state transition
class StartCombatCommand:
    def execute(self, game_context: GameContext) -> None:
        game_context.state_machine.transition(
            GameState.COMBAT,
            context={'reason': 'enemy_encounter', 'enemy_id': 'goblin-1'}
        )
```

**Key Insights**:
- **Custom implementation is educational** and sufficient for Phase 1
- **Enum for states** provides type safety and simplicity
- **Explicit transition allow-list** makes valid paths self-documenting
- **Event emission before state change** ensures accurate audit trail
- **Dependency injection** for EventStore enables easy testing
- **Mock EventStore in tests** keeps unit tests fast (no database)
- **Flat state machine** is enough for Phase 1 (add hierarchy later if needed)
- **State machine + Command pattern** work together (state vs behavior)

**Decision**:
**DECIDED**: Custom state machine with enum + explicit transition validation (documented as DEC-0002 in decisions.md)

**Rationale**:
- Learning project: custom implementation teaches fundamentals
- Full control: no library abstraction to debug
- Type-safe: Python enum + mypy validation
- Testable: dependency injection + mocking
- Simple: ~150 lines of code vs learning library API
- Extensible: can add sub-states in Phase 2 if needed

**Implementation Guidance**:

**Step 2 Implementation Checklist**:
1. Create `src/core/state_machine.py`
2. Define `GameState` enum with all states
3. Create `GameStateMachine` class with `ALLOWED_TRANSITIONS` dict
4. Implement `transition()` method with validation
5. Implement `_is_valid_transition()` helper
6. Implement `_emit_transition_event()` for event sourcing
7. Add `can_transition_to()` for UI logic
8. Add `get_valid_transitions()` for debugging
9. Create `StateTransitionError` in `src/core/exceptions.py`
10. Write comprehensive unit tests (valid, invalid, event emission)

**Code Organization**:
```
src/core/
├── state_machine.py
│   ├── GameState (enum)
│   ├── GameStateMachine (class)
│   └── ALLOWED_TRANSITIONS (dict)
├── exceptions.py
│   └── StateTransitionError (exception)
tests/unit/
└── test_state_machine.py
    ├── test_valid_transitions
    ├── test_invalid_transitions
    ├── test_event_emission
    └── test_transition_helpers
```

**Testing Strategy**:
- **Unit tests**: Mock EventStore, test transition logic
- **Integration tests**: Real EventStore, verify events persist
- **Property-based tests** (optional): Use `hypothesis` to generate random transition sequences

**Performance Targets**:
- State transition: < 1ms (including event emission)
- Transition validation: < 0.1ms (simple set lookup)

**Confidence Level**: 🟢 High

**References**:
- [Game Programming Patterns - State](https://gameprogrammingpatterns.com/state.html)
- [Python Enum](https://docs.python.org/3/library/enum.html)
- DEC-0002 in decisions.md

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

