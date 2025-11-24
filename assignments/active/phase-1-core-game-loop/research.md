# Research Document: Phase 1 - Core Game Loop

**Phase**: Phase 1  
**Created**: 2024-11-24  
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
**Status**: 🔲 Not Started  
**Priority**: 🔴 High  
**Assigned To**: @data-worker  

**Why Research Needed**:
Event sourcing is the architectural foundation for timeline branching. Need to validate SQLite performance for append-only event logs and ensure proper indexing strategies.

**Questions to Answer**:
1. What schema design best supports event sourcing in SQLite?
2. What indexes are needed for timeline replay performance?
3. How should we handle event versioning/schema evolution?
4. What's the expected write throughput for event logging?
5. Should we use WAL mode for better concurrency?

**Research Sources**:
- [ ] SQLite documentation on WAL mode
- [ ] Martin Fowler's Event Sourcing pattern
- [ ] Greg Young's Event Store design principles
- [ ] SQLite performance best practices
- [ ] Python sqlite3 module documentation

**Research Methodology**:
- Review SQLite transaction patterns for high-write scenarios
- Benchmark append-only INSERT performance
- Research event schema versioning strategies
- Investigate SQLite's date/time handling for event timestamps

**Findings**:
[To be filled]

**Key Insights**:
- [To be filled]

**Decision**:
[To be filled - document in decisions.md]

**Implementation Guidance**:
[To be filled]

**Confidence Level**: 🔴 Low  

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
**Status**: 🔲 Not Started  
**Priority**: 🟡 Medium  
**Assigned To**: @architect-supervisor  

**Why Research Needed**:
Need a clean way to manage game configuration (screen size, FPS target, AI settings) that's easy to test and doesn't use global state.

**Questions to Answer**:
1. What's the best Python library for configuration? (pydantic-settings, dynaconf, etc.)
2. How to handle environment-specific configs (dev, test, prod)?
3. Should config be injected like other dependencies?
4. How to validate configuration at startup?
5. What format: YAML, TOML, Python dataclass?

**Research Sources**:
- [ ] Pydantic BaseSettings documentation
- [ ] dynaconf library
- [ ] Python configparser vs modern alternatives
- [ ] 12-factor app methodology
- [ ] Configuration management best practices

**Research Methodology**:
- Compare pydantic-settings vs dynaconf vs python-decouple
- Research type-safe configuration patterns
- Investigate environment variable handling
- Consider testability of different approaches

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
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [The Twelve-Factor App](https://12factor.net/config)

---

### Topic 6: Testing Strategy
**Status**: 🔲 Not Started  
**Priority**: 🟡 Medium  
**Assigned To**: @architect-supervisor  

**Why Research Needed**:
Need to establish testing patterns for event sourcing, state machines, and Pygame integration to achieve >= 80% coverage.

**Questions to Answer**:
1. How to mock Pygame for unit tests?
2. How to test event sourcing replay logic?
3. How to test async AI calls without hitting real Ollama?
4. What fixtures are needed for common test scenarios?
5. How to test state machine transitions comprehensively?

**Research Sources**:
- [ ] Pytest best practices
- [ ] Pygame testing patterns
- [ ] pytest-asyncio documentation
- [ ] Mock/MagicMock best practices
- [ ] Event sourcing testing strategies

**Research Methodology**:
- Research Pygame mocking strategies (pygame.locals, surfaces, etc.)
- Investigate pytest-mock and pytest-asyncio
- Review event sourcing testing patterns
- Consider property-based testing with hypothesis

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

