# Decision Log: Phase 1 - Core Game Loop

**Phase**: Phase 1  
**Created**: 2025-11-24  
**Status**: 🔄 Active  

## Overview
This document logs all significant architectural, design, and implementation decisions made during Phase 1. Decisions are captured using a lightweight ADR (Architecture Decision Record) format.

**Total Decisions**: 3  
**Constitution Deviations**: 0  
**High Impact**: 1  

---

## Decision Index

Quick reference table for all decisions:

| ID | Title | Status | Impact | Date | Deviation | Notes |
|----|-------|--------|--------|------|-----------|-------|
| DEC-0001 | SQLite for Event Store | 🟡 Accepted | 🔴 Critical | 2025-11-24 | ❌ | Event sourcing foundation |
| DEC-0002 | Custom State Machine Pattern | 🟡 Accepted | 🟡 High | 2025-11-24 | ❌ | Clear transitions, testable |
| DEC-0003 | No Rendering in Phase 1 | 🟡 Accepted | 🟢 Medium | 2025-11-24 | ❌ | Architecture-first approach |

---

## Pending Decisions

The following decisions require research completion before documentation:

### PD-1: Event Store Schema Design
**Status**: ⏳ Awaiting Research  
**Depends On**: Research Topic 1 (Event Sourcing with SQLite)  
**Impact**: 🔴 Critical  

**Questions to Resolve**:
- JSON vs separate columns for event payload?
- Event versioning strategy (schema migration vs envelope pattern)?
- Index strategy for timeline replay?
- WAL mode vs default journaling?

**Timeline**: To be decided after Topic 1 research completion

---

### PD-2: State Machine Implementation
**Status**: ⏳ Awaiting Research  
**Depends On**: Research Topic 3 (State Machine Pattern)  
**Impact**: 🟡 High  

**Questions to Resolve**:
- Custom implementation vs library (transitions, python-statemachine)?
- State objects as classes or functions?
- How to handle nested/hierarchical states?

**Timeline**: To be decided after Topic 3 research completion

---

### PD-3: Async Integration Strategy
**Status**: ⏳ Awaiting Research  
**Depends On**: Research Topic 4 (Async AI Integration)  
**Impact**: 🟡 High  

**Questions to Resolve**:
- asyncio vs threading vs hybrid for AI calls?
- How to prevent blocking Pygame loop?
- Task cancellation strategy?

**Timeline**: To be decided after Topic 4 research completion

---

### PD-4: Game Loop Timing Model
**Status**: ⏳ Awaiting Research  
**Depends On**: Research Topic 2 (Pygame Event Loop Integration)  
**Impact**: 🟡 High  

**Questions to Resolve**:
- Fixed timestep vs variable timestep?
- How to handle frame drops?
- Target FPS: locked 60 or variable?

**Timeline**: To be decided after Topic 2 research completion

---

### PD-5: Configuration Management Approach
**Status**: ⏳ Awaiting Research  
**Depends On**: Research Topic 5 (Configuration Management)  
**Impact**: 🟢 Medium  

**Questions to Resolve**:
- Library choice: pydantic-settings, dynaconf, or python-decouple?
- Configuration format: YAML, TOML, or Python dataclass?
- Environment-specific config handling?

**Timeline**: To be decided after Topic 5 research completion

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
- [ ] All pending decisions resolved
- [ ] Research findings documented
- [ ] Constitution compliance verified
- [ ] Technical debt tracked (if any)
- [ ] Implementation guidance clear
- [ ] Ready for PLAN.md execution

