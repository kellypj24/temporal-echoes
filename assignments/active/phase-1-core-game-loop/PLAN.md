# Phase 1: Core Game Loop

**Status**: 🔄 In Progress  
**Started**: 2025-11-24  
**Completed**: _____________  
**Branch**: `phase/1-core-game-loop`

## Phase Workflow

This phase follows the Spec-Driven Development (SDD) approach:

1. **🔍 Research Phase** (documented in `research.md`) ✅ **COMPLETE**
   - Investigate unknowns, validate assumptions, check dependencies
   - **Status**: All 6 research topics completed (2025-11-24)

2. **📋 Decision Phase** (documented in `decisions.md`) ✅ **COMPLETE**
   - Make architectural and design decisions based on research
   - Document alternatives and trade-offs
   - **Status**: All 8 decisions documented, 0 deviations (2025-11-24)

3. **🛠️ Implementation Phase** (this document) 🟢 **READY TO START**
   - Execute steps based on research and decisions
   - Follow constitution principles
   - **Status**: All prerequisites met, ready for implementation

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

### Research Prerequisites ✅ **ALL COMPLETE**
- [x] `research.md` completed and reviewed (2025-11-24)
- [x] All high-priority research topics addressed (Topics 1-6 complete)
- [x] Critical assumptions validated (SQLite sufficient, threading over asyncio)
- [x] Tech stack versions confirmed (Python 3.13, Pygame, pydantic-settings)
- [x] Performance benchmarks completed (SQLite < 10ms writes, 60 FPS achievable)

### Decision Prerequisites ✅ **ALL COMPLETE**
- [x] **DEC-0001**: SQLite for Event Store (documented)
- [x] **DEC-0002**: Custom State Machine Pattern (documented)
- [x] **DEC-0003**: No Rendering in Phase 1 (documented)
- [x] **DEC-0004**: Hybrid CQRS Architecture (documented)
- [x] **DEC-0005**: Threading Over Asyncio for AI (documented)
- [x] **DEC-0006**: Fixed Timestep Game Loop (documented)
- [x] **DEC-0007**: Pydantic Settings for Configuration (documented)
- [x] **DEC-0008**: pytest Testing Stack (documented)
- [x] Constitution compliance verified (0 deviations)
- [x] Technical debt documented (none identified)
- [x] Implementation guidance clear (each ADR includes implementation notes)

**✅ APPROVED**: All SDD prerequisites met. Implementation phase approved to proceed (2025-11-24).

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
**Based On**: Research Topic 1, DEC-0001 (SQLite), DEC-0004 (Hybrid CQRS)

**Description**: 
Implement the core event store using SQLite with proper schema design, indexing, and transaction safety. This is the foundation for all game state persistence.

**Decision Guidance** (from DEC-0001 and DEC-0004):
- **Database**: SQLite with WAL mode enabled (PRAGMA journal_mode=WAL)
- **Schema**: Single `game_events` table with JSON `event_data` column
- **Indexes**: timeline_id, session_id, event_timestamp for fast queries
- **CQRS Prep**: Include `aggregate_id` + `aggregate_type` columns (future read models)
- **Hybrid CQRS** (DEC-0004):
  * Phase 1: Pure event sourcing (events only)
  * Phase 2+: App handlers update read models, dbt transforms JSON independently
  * Single source of truth: game_events table
- **Performance Target**: < 10ms p95 latency for event writes
- **Concurrency**: WAL mode for better read performance during writes

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
**Based On**: Research Topic 3, DEC-0002 (Custom State Machine)

**Description**: 
Implement the core state machine with state enum, transition validation, and event emission. This coordinates game modes (MENU, EXPLORING, COMBAT, etc.).

**Decision Guidance** (from DEC-0002 and Research Topic 3):
- **Implementation**: Custom state machine (no external library)
- **States**: GameState enum with 8 states (MENU, EXPLORING, COMBAT, DIALOGUE, INVENTORY, TIMELINE_VIEW, PAUSED, GAME_OVER)
- **Transitions**: Explicit `ALLOWED_TRANSITIONS` dictionary for validation
- **Event Emission**: Emit event **before** state change (Research Topic 3)
- **Dependency Injection**: EventStore passed via constructor (not global)
- **Error Handling**: Raise `StateTransitionError` on invalid transitions
- **Rationale**: Educational value, full control, easy debugging (DEC-0002)

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
**Based On**: Research Topic 2, DEC-0003 (No Rendering), DEC-0006 (Fixed Timestep)

**Description**:
Create the main game loop structure without rendering. Handles update cycle, fixed timestep, and state-specific updates.

**Decision Guidance** (from DEC-0006 and Research Topic 2):
- **Timing Model**: Fixed timestep at 60 Hz (16.67ms per tick)
- **Pattern**: Accumulator pattern with frame skipping (Gaffer on Games)
- **Max Frame Skip**: 10 ticks per frame (prevent spiral of death)
- **Determinism**: Logic always uses fixed 16.67ms delta (testable, event sourcing compatible)
- **No Rendering**: Console-based output only for Phase 1 (DEC-0003)
- **Threading Prep**: Structure supports AIRequestQueue for Phase 4 (DEC-0005)
- **Performance Target**: Maintain stable 60 Hz tick rate over 1000+ frames

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
**Based On**: Research Topic 5, DEC-0007 (Pydantic Settings)

**Description**:
Implement configuration management using Pydantic Settings with type-safe validation.

**Decision Guidance** (from DEC-0007 and Research Topic 5):
- **Library**: Pydantic Settings (`pydantic-settings` package)
- **Base Class**: Inherit from `BaseSettings` for automatic .env loading
- **Type Safety**: Full type hints with Pydantic `Field` for validation
- **Validation**: Startup-time validation with clear error messages
- **Config Fields**: database_path, target_fps, debug_mode, ollama_host, llm_model, ai_timeout
- **Rationale**: Pydantic already a dependency, type-safe, excellent validation (DEC-0007)
- **IDE Support**: Autocomplete and type checking work out of the box

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

After all steps are complete, run comprehensive integration tests to validate system behavior.

**Testing Strategy** (from DEC-0008):
- **Framework**: pytest + unittest.mock + pytest-asyncio
- **Database**: In-memory SQLite (`:memory:`) for fast, isolated tests
- **Fixtures**: Reusable test data in `tests/fixtures/`
- **Coverage Target**: >= 80% on all modules

**Test Scenarios**:

1. **Scenario 1: Basic Game Flow** (Validates: DEC-0002, DEC-0001)
   - Setup: Fresh database, no existing data
   - Action: Start game, transition MENU → EXPLORING → COMBAT → EXPLORING → MENU
   - Expected: All transitions succeed, all events logged in `game_events` table, no errors
   - Validates: State machine transitions, event store persistence

2. **Scenario 2: Event Store Persistence** (Validates: DEC-0001, DEC-0004)
   - Setup: Run game for 100 state transitions
   - Action: Query event store for all events
   - Expected: Exactly 100 events retrieved in correct chronological order
   - Validates: Event sourcing integrity, ACID compliance

3. **Scenario 3: Deterministic Gameplay** (Validates: DEC-0006)
   - Setup: Fresh database, fixed seed
   - Action: Run identical input sequence twice
   - Expected: Identical event logs (same event_ids, timestamps, data)
   - Validates: Fixed timestep determinism for event sourcing replay

4. **Scenario 4: Timeline Creation** (Validates: DEC-0004)
   - Setup: Game in EXPLORING state with 50 events
   - Action: Create new timeline branch
   - Expected: New timeline_id created, events copied correctly to new timeline
   - Validates: Timeline branching for CQRS preparation

5. **Scenario 5: Error Handling** (Validates: DEC-0002)
   - Setup: Game in COMBAT state
   - Action: Attempt invalid transition to TIMELINE_VIEW (not in ALLOWED_TRANSITIONS)
   - Expected: StateTransitionError raised, no event emitted, state unchanged
   - Validates: Transition validation, error handling

6. **Scenario 6: Configuration Loading** (Validates: DEC-0007)
   - Setup: .env file with custom settings
   - Action: Initialize GameConfig
   - Expected: Settings loaded correctly with type validation
   - Validates: Pydantic Settings integration

7. **Scenario 7: Game Loop Stability** (Validates: DEC-0006)
   - Setup: Start game loop
   - Action: Run for 1000 ticks (~16.67 seconds at 60 Hz)
   - Expected: Stable 60 Hz tick rate, no frame drops, memory stable
   - Validates: Fixed timestep implementation, performance target

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

