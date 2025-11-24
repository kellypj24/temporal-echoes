# Phase 1: Core Game Loop

**Status**: 🔄 In Progress  
**Started**: 2025-11-24  
**Completed**: _____________  
**Branch**: `phase/1-core-game-loop`

## Phase Workflow

This phase follows the Spec-Driven Development (SDD) approach:

1. **🔍 Research Phase** (documented in `research.md`) ✅ IN PROGRESS
   - Investigate unknowns, validate assumptions, check dependencies
   - **Status**: 6 research topics to complete

2. **📋 Decision Phase** (documented in `decisions.md`) ✅ PARTIALLY COMPLETE
   - Make architectural and design decisions based on research
   - Document alternatives and trade-offs
   - **Status**: 3 decisions documented, 5 pending decisions awaiting research

3. **🛠️ Implementation Phase** (this document) ⏳ AWAITING APPROVAL
   - Execute steps based on research and decisions
   - Follow constitution principles
   - **Status**: Blocked until research and decisions complete

4. **✅ Validation Phase** ⏳ PENDING
   - Test, review, and validate all success criteria
   - Ensure constitution compliance

## Objectives
- Implement SQLite event store for event sourcing architecture
- Create base state machine with state transitions and validation
- Build foundational project structure with proper dependency injection
- Establish testing patterns and achieve >= 80% coverage
- Set up basic game loop structure (no rendering yet)

## Prerequisites

### Hard Prerequisites
- [x] Development environment set up
- [x] Poetry dependencies installed (`make install`)
- [x] Docker with Ollama running (`make docker-up`)
- [x] dbt project structure initialized (`make dbt-init`)
- [x] Project pushed to GitHub
- [x] Git branch created: `phase/1-core-game-loop`

### Research Prerequisites
- [ ] `research.md` completed and reviewed
- [ ] All high-priority research topics addressed (Topics 1-4)
- [ ] Critical assumptions validated
- [ ] Tech stack versions confirmed
- [ ] Performance benchmarks completed

### Decision Prerequisites
- [x] **DEC-0001**: SQLite for Event Store (documented)
- [x] **DEC-0002**: Custom State Machine Pattern (documented)
- [x] **DEC-0003**: No Rendering in Phase 1 (documented)
- [ ] **PD-1**: Event Store Schema Design (awaiting research)
- [ ] **PD-2**: State Machine Implementation Details (awaiting research)
- [ ] **PD-3**: Async Integration Strategy (awaiting research)
- [ ] **PD-4**: Game Loop Timing Model (awaiting research)
- [ ] **PD-5**: Configuration Management Approach (awaiting research)
- [ ] Constitution compliance verified
- [ ] Technical debt documented (if any)
- [ ] Implementation guidance clear

**🚨 CRITICAL**: Per SDD workflow, implementation CANNOT proceed until all research and decisions are complete and approved.

## Context
Phase 1 establishes the foundational architecture for Temporal Echoes. We're implementing event sourcing from the start to enable timeline branching later. The focus is on clean architecture, type safety, and testability - not on visual features or gameplay yet.

**Key Architectural Decision - Hybrid CQRS** (from `research.md` Topic 1):
- **Phase 1**: Pure event sourcing (game_events table with JSON)
- **Phase 2+**: Two parallel paths from events:
  1. **App Path**: Maintains SQLite read models for fast gameplay queries
  2. **dbt Path**: Parses game_events JSON independently for analytics
- **Single Source of Truth**: game_events (JSON) is the only authoritative source
- **No Dual-Write**: App writes events once; read models + analytics derive from it
- **Learning Goal**: Refine CQRS skills with real-world hybrid pattern

**Architecture Principles** (from `.cursor/rules/CONSTITUTION.md`):
- Event sourcing: All state changes emit immutable events (Principle #1)
- Dependency injection: No global state or singletons except AIManager (Principle #2)
- Type safety: Type hints on all functions (Principle #3)
- Test-driven: Write tests alongside implementation (Principle #5)
- Separation of concerns: No rendering in core logic (Principle #4)

**Related Documents**:
- `research.md` - Research findings for this phase
- `decisions.md` - Decision log for this phase (3 ADRs documented)
- `.cursor/rules/CONSTITUTION.md` - Development principles

## Steps

### Step 1: SQLite Event Store Implementation
**Branch**: `feature/phase-1-event-store`  
**Supervisors**: `@architect-supervisor`, `@data-worker`  
**Based On**: Research Topic 1 (Event Sourcing with SQLite), DEC-0001

**Description**: 
Implement the core event store using SQLite with proper schema design, indexing, and transaction safety. This is the foundation for all game state persistence.

**Research Guidance**:
- Use WAL mode for better concurrency (per Research Topic 1)
- Schema design informed by DEC-0001
- Index on timeline_id, session_id, event_timestamp
- Include aggregate_id + aggregate_type for CQRS preparation
- JSON column (event_data) for full event context
- **Hybrid CQRS Architecture** (from Research Topic 1):
  * Phase 1: Events only (game_events table)
  * Phase 2+: App maintains read models + dbt parses JSON independently
  * dbt reads game_events JSON, NOT read models (two parallel paths)

**Tasks**:
- [ ] Create `src/core/persistence.py` with EventStore class
- [ ] Define GameEvent dataclass with all required fields
- [ ] Implement SQL schema with indexes on timeline_id, session_id, timestamp
- [ ] Add append_event() method with ACID guarantees
- [ ] Add get_events_by_timeline() query method
- [ ] Add create_timeline() for timeline branching
- [ ] Create comprehensive unit tests

**Success Criteria**:
- [ ] Unit tests pass: `pytest tests/unit/test_event_store.py -v`
- [ ] Code coverage >= 80%: `pytest --cov=src/core/persistence.py`
- [ ] No linting errors: `ruff check src/core/persistence.py`
- [ ] Type checking passes: `mypy src/core/persistence.py`
- [ ] Manual validation: Can store and retrieve 1000 events without errors
- [ ] Documentation: Docstrings on all public methods

**Files to Create/Modify**:
- `src/core/__init__.py` - Package initialization
- `src/core/persistence.py` - EventStore class and schema
- `src/core/events.py` - GameEvent dataclass and event types
- `tests/unit/test_event_store.py` - Comprehensive unit tests
- `tests/fixtures/event_fixtures.py` - Test data fixtures

**Estimated Time**: 4-6 hours

---

### Step 2: Base State Machine
**Branch**: `feature/phase-1-state-machine`  
**Supervisors**: `@architect-supervisor`, `@game-logic-worker`  
**Based On**: Research Topic 3 (State Machine Pattern), DEC-0002

**Description**: 
Implement the core state machine with state enum, transition validation, and event emission. This coordinates game modes (MENU, EXPLORING, COMBAT, etc.).

**Research Guidance**:
- Custom implementation (per DEC-0002) using enum + validation matrix
- Explicit allowed transitions for clarity
- Emit events on every state change (constitution principle #1)
- Dependency injection for EventStore (constitution principle #2)

**Tasks**:
- [ ] Create `src/core/state_machine.py` with GameStateMachine class
- [ ] Define GameState enum (MENU, EXPLORING, COMBAT, DIALOGUE, INVENTORY, TIMELINE_VIEW)
- [ ] Implement transition() method with validation
- [ ] Emit events on state transitions
- [ ] Add _is_valid_transition() logic based on state graph
- [ ] Create StateTransitionError exception
- [ ] Write unit tests for all transitions

**Success Criteria**:
- [ ] All valid transitions work correctly
- [ ] Invalid transitions raise StateTransitionError
- [ ] Events emitted for every state change
- [ ] Unit tests pass: `pytest tests/unit/test_state_machine.py -v`
- [ ] Coverage >= 80%
- [ ] No circular import dependencies
- [ ] Manual test: Can transition through game flow without errors

**Files to Create/Modify**:
- `src/core/state_machine.py` - GameStateMachine class
- `src/core/exceptions.py` - Custom exceptions
- `tests/unit/test_state_machine.py` - State machine tests

**Estimated Time**: 3-4 hours

---

### Step 3: Game Context and Session Management
**Branch**: `feature/phase-1-game-context`  
**Supervisors**: `@architect-supervisor`, `@game-logic-worker`

**Description**:
Create the GameContext class that holds all game state and coordinates between systems. Implements dependency injection pattern.

**Tasks**:
- [ ] Create `src/core/game_context.py` with GameContext class
- [ ] Add session_id and timeline_id tracking
- [ ] Inject EventStore and StateMachine into context
- [ ] Create factory method for initialization
- [ ] Add methods for common operations
- [ ] Implement context serialization for save/load
- [ ] Write unit tests

**Success Criteria**:
- [ ] GameContext properly manages dependencies
- [ ] No global state variables
- [ ] Unit tests pass
- [ ] Can create, use, and destroy context cleanly
- [ ] Manual test: Initialize context, run operations, verify events logged

**Files to Create/Modify**:
- `src/core/game_context.py` - GameContext class
- `tests/unit/test_game_context.py` - Context tests

**Estimated Time**: 2-3 hours

---

### Step 4: Basic Game Loop Structure
**Branch**: `feature/phase-1-game-loop`  
**Supervisors**: `@architect-supervisor`, `@game-logic-worker`  
**Based On**: Research Topic 2 (Pygame Event Loop Integration), Research Topic 4 (Async AI)

**Description**:
Create the main game loop structure without rendering. Handles update cycle, delta time, and state-specific updates.

**Research Guidance**:
- Game loop timing model determined by PD-4 (pending research)
- Async integration strategy from PD-3 (pending research)
- No rendering (per DEC-0003) - console-based for Phase 1
- Target consistent tick rate (60 FPS preparation)

**Tasks**:
- [ ] Create `src/core/game_loop.py` with GameLoop class
- [ ] Implement update() method with delta time
- [ ] Add state handler registration system
- [ ] Create simple console-based main loop for testing
- [ ] Update `src/main.py` to use GameLoop
- [ ] Add graceful shutdown handling
- [ ] Write integration tests

**Success Criteria**:
- [ ] Game loop runs at consistent tick rate
- [ ] State handlers get called correctly
- [ ] Delta time calculation accurate
- [ ] Can start and stop cleanly
- [ ] Integration tests pass
- [ ] Manual test: Run game loop for 60 seconds, verify stable performance

**Files to Create/Modify**:
- `src/core/game_loop.py` - GameLoop class
- `src/main.py` - Updated entry point
- `tests/integration/test_game_loop.py` - Integration tests

**Estimated Time**: 3-4 hours

---

### Step 5: Configuration System
**Branch**: `feature/phase-1-config`  
**Supervisors**: `@architect-supervisor`  
**Based On**: Research Topic 5 (Configuration Management)

**Description**:
Implement configuration management using environment variables and config files.

**Research Guidance**:
- Library choice determined by PD-5 (pending research)
- Type-safe configuration (constitution principle #3)
- Environment variable support (.env file)
- Validation for required settings

**Tasks**:
- [ ] Create `src/core/config.py` with Config class
- [ ] Load from environment variables
- [ ] Add validation for required settings
- [ ] Support .env file loading
- [ ] Create default configurations
- [ ] Add unit tests

**Success Criteria**:
- [ ] Config loads from .env file
- [ ] Environment variables override defaults
- [ ] Missing required config raises clear error
- [ ] Unit tests pass
- [ ] Documentation updated

**Files to Create/Modify**:
- `src/core/config.py` - Configuration management
- `tests/unit/test_config.py` - Config tests
- `.env.example` - Update with new variables

**Estimated Time**: 2-3 hours

---

## Integration Testing

After all steps are complete:

**Test Scenarios**:

1. **Scenario 1: Basic Game Flow**
   - Setup: Fresh database, no existing data
   - Action: Start game, transition MENU → EXPLORING → COMBAT → EXPLORING → MENU
   - Expected: All transitions succeed, all events logged, no errors

2. **Scenario 2: Event Store Persistence**
   - Setup: Run game for 100 state transitions
   - Action: Query event store for all events
   - Expected: Exactly 100 events retrieved in correct order

3. **Scenario 3: Timeline Creation**
   - Setup: Game in EXPLORING state
   - Action: Create new timeline branch
   - Expected: New timeline_id created, events copied correctly

4. **Scenario 4: Error Handling**
   - Setup: Game in COMBAT state
   - Action: Attempt invalid transition to MENU
   - Expected: StateTransitionError raised, no event emitted, state unchanged

## Validation Checklist

### Code Quality
- [ ] All unit tests pass: `make test`
- [ ] Code coverage >= 80%
- [ ] No linting errors: `make lint`
- [ ] Type hints on all functions
- [ ] Docstrings on public methods

### Functional Requirements
- [ ] Event store persists and retrieves events correctly
- [ ] State machine enforces valid transitions
- [ ] Game context properly manages dependencies
- [ ] Game loop runs stably
- [ ] Configuration system works

### Architecture Compliance
- [ ] Clean separation of concerns maintained
- [ ] Dependencies injected, not instantiated
- [ ] Events emitted for all state changes
- [ ] No circular dependencies
- [ ] No game logic in rendering code (N/A for Phase 1)

### Documentation
- [ ] README updated with Phase 1 completion
- [ ] API documentation for core modules
- [ ] Example usage provided
- [ ] Architecture decisions documented

### Performance
- [ ] Event store writes < 10ms (p95)
- [ ] State transitions < 1ms
- [ ] Game loop maintains target tick rate
- [ ] Memory usage stable over time

## Constitution Compliance

Review against `.cursor/rules/CONSTITUTION.md` principles:

### Immutable Principles Check
- [ ] ✅ **Principle #1**: Events are append-only (no updates/deletes to game_events)
- [ ] ✅ **Principle #2**: Dependencies injected via constructors (EventStore, StateMachine)
- [ ] ✅ **Principle #3**: Type hints on all functions
- [ ] ✅ **Principle #4**: Clean separation of concerns (no rendering in src/core/)
- [ ] ✅ **Principle #5**: >= 80% test coverage
- [ ] ✅ **Principle #6**: Specific error handling (no bare except)
- [ ] ✅ **Principle #7**: Google-style docstrings on public APIs
- [ ] ⏳ **Principle #8**: All AI calls are async/non-blocking (N/A for Phase 1)
- [ ] ⏳ **Principle #9**: AI fallbacks implemented (N/A for Phase 1)
- [ ] ⏳ **Principle #10**: Token limits validated (N/A for Phase 1)
- [ ] ✅ **Principle #11**: Events are immutable (SQLite append-only)
- [ ] ✅ **Principle #12**: Transactions used for multi-step DB operations
- [ ] ✅ **Principle #13**: SQLite for OLTP, DuckDB for OLAP
- [ ] ⏳ **Principle #14**: 60 FPS target maintained (structure only, no rendering)
- [ ] ⏳ **Principle #15**: < 5 second AI response time (N/A for Phase 1)

### Deviations
**None Expected**. All Phase 1 work aligns with constitution principles.

If ANY principles are violated during implementation, they MUST be documented in `decisions.md` with:
- **[Principle Name]**: [Link to decision record justifying deviation]
- Justification and remediation plan
- GitHub issue for technical debt tracking

## Rollback Plan
If this phase needs to be reverted:
1. `git checkout main`
2. `git branch -D phase/1-core-game-loop`
3. Remove `assignments/active/phase-1-core-game-loop/`
4. Drop `data/events.db` if created
5. Revert commits: `git revert <commit-hash>`
6. Update decision log with rollback reason

## Retrospective

### What Went Well
[Document successes for future reference]
- [To be filled upon completion]

### What Could Be Improved
[Document challenges and how to avoid them]
- [To be filled upon completion]

### Lessons Learned
[Key takeaways for future phases]
- [To be filled upon completion]

### Metrics
- **Estimated Time**: 14-20 hours (5 steps)
- **Actual Time**: _____ hours
- **Test Coverage**: _____%
- **Lines of Code**: _____
- **Decisions Made**: 3 (documented)
- **Constitution Deviations**: 0
- **Research Topics Completed**: 6

### Technical Debt Created
[Document any shortcuts or TODOs]
- [To be filled upon completion]

## Follow-up Phases
What should be done after this phase:
- **Phase 2**: Combat System - Turn-based combat, damage calc, combo tracking
- **Phase 3**: Timeline Mechanics - Timeline branching, Echo Stones, convergence
- **Phase 4**: Basic Rendering - Pygame setup, sprite loading, basic display
- **Phase 5**: AI Integration - Ollama connection, prompt templates, narratives

## Sign-off
- [ ] All steps completed
- [ ] All tests passing
- [ ] All validation criteria met
- [ ] Constitution compliance verified (all 15 principles)
- [ ] Documentation complete
- [ ] Retrospective filled out
- [ ] Ready to merge to `main`
- [ ] Ready to move to `assignments/completed/`

**Completed By**: _____________  
**Completion Date**: _____________  
**Review Status**: [ ] Approved / [ ] Needs Revision / [ ] Needs Constitution Review

