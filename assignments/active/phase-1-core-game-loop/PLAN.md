# Phase 1: Core Game Loop

**Branch**: `phase/1-core-game-loop`  
**Status**: In Progress  
**Started**: 2024-11-24  

## Objectives
- Implement SQLite event store for event sourcing architecture
- Create base state machine with state transitions and validation
- Build foundational project structure with proper dependency injection
- Establish testing patterns and achieve >= 80% coverage
- Set up basic game loop structure (no rendering yet)

## Prerequisites
- [x] Development environment set up
- [x] Poetry dependencies installed
- [x] Docker with Ollama running
- [x] dbt project structure initialized
- [x] Project pushed to GitHub

## Context
Phase 1 establishes the foundational architecture for Temporal Echoes. We're implementing event sourcing from the start to enable timeline branching later. The focus is on clean architecture, type safety, and testability - not on visual features or gameplay yet.

**Architecture Principles:**
- Event sourcing: All state changes emit immutable events
- Dependency injection: No global state or singletons (except AIManager)
- Type safety: Type hints on all functions
- Test-driven: Write tests alongside implementation

## Steps

### Step 1: SQLite Event Store Implementation
**Branch**: `feature/phase-1-event-store`  
**Supervisors**: `@architect-supervisor`, `@data-worker`

**Description**: 
Implement the core event store using SQLite with proper schema design, indexing, and transaction safety. This is the foundation for all game state persistence.

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

**Description**: 
Implement the core state machine with state enum, transition validation, and event emission. This coordinates game modes (MENU, EXPLORING, COMBAT, etc.).

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

**Description**:
Create the main game loop structure without rendering. Handles update cycle, delta time, and state-specific updates.

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

**Description**:
Implement configuration management using environment variables and config files.

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

## Rollback Plan
If this phase needs to be reverted:
1. `git checkout main`
2. Delete `phase/1-core-game-loop` branch
3. Remove `assignments/active/phase-1-core-game-loop/`
4. Drop `data/events.db` if created

## Notes & Decisions

### Decision 1: SQLite for Event Store
- **Rationale**: Simple, embedded, ACID-compliant, no server needed
- **Alternatives Considered**: PostgreSQL (overkill), JSON files (no transactions)
- **Trade-offs**: Gained simplicity, acceptable performance for single-player game

### Decision 2: State Machine Pattern
- **Rationale**: Clear state transitions, easy to reason about, testable
- **Alternatives Considered**: Pure event sourcing (too complex for start)
- **Trade-offs**: Some boilerplate, but worth it for clarity

### Decision 3: No Rendering in Phase 1
- **Rationale**: Focus on architecture first, rendering is complex distraction
- **Alternatives Considered**: Build game + rendering together (risky)
- **Trade-offs**: Can't see visual progress, but architecture will be solid

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
- [ ] Documentation complete
- [ ] Ready to merge to `main`
- [ ] Ready to move to `assignments/completed/`

**Completed By**: _____________  
**Completion Date**: _____________  
**Review Status**: [ ] Approved / [ ] Needs Revision

