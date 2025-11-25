# Phase 2: Combat System

## Overview
This phase implements the core turn-based combat system for Temporal Echoes, building on the event sourcing and state machine foundation from Phase 1. Includes damage calculation, enemy AI, combat state management, and comprehensive testing.

## Status
🔄 **Research Phase In Progress**

## Quick Links
- **Research**: [research.md](./research.md)
- **Decisions**: [decisions.md](./decisions.md) _(Not yet created)_
- **Plan**: [PLAN.md](./PLAN.md) _(Not yet created)_
- **Branch**: `phase/2-combat-system`
- **Supervisors**: @architect-supervisor, @game-logic-worker, @data-worker

## SDD Workflow Status

| Phase | Status | Start Date | Completion Date |
|-------|--------|-----------|-----------------|
| 1. Research | 🔄 In Progress | 2025-11-25 | TBD |
| 2. Decisions | 🔲 Not Started | TBD | TBD |
| 3. Implementation | 🔲 Not Started | TBD | TBD |
| 4. Validation | 🔲 Not Started | TBD | TBD |

## Research Topics Status

| # | Topic | Priority | Status | Duration |
|---|-------|----------|--------|----------|
| 1 | Turn-Based Combat Mechanics | 🔴 High | 🔲 Not Started | 3-4h |
| 2 | Damage Calculation System | 🔴 High | 🔲 Not Started | 2-3h |
| 3 | Combat Event Schema | 🔴 High | 🔲 Not Started | 2-3h |
| 4 | Enemy AI Behavior | 🔴 High | 🔲 Not Started | 2-3h |
| 5 | Combat State/UI | 🟡 Medium | 🔲 Not Started | 2h |
| 6 | Testing Strategy | 🟡 Medium | 🔲 Not Started | 2h |

**Total Estimated Research Time**: 13-17 hours

## Implementation Steps (TBD After Research)

_Will be defined after research and decision phases complete_

Preliminary outline:
- Step 1: Combat entities and base classes
- Step 2: Damage calculation system
- Step 3: Combat event integration
- Step 4: Enemy AI implementation
- Step 5: Combat state machine integration
- Step 6: Integration testing

## Key Files to Create

### Combat Core
```
src/entities/
├── __init__.py
├── combatant.py        # Base Combatant class
├── player.py           # Player entity
├── enemy.py            # Enemy entity
└── abilities.py        # Combat abilities/skills

src/core/
├── combat.py           # Combat manager
├── damage.py           # Damage calculation
└── ai.py               # Enemy AI logic

tests/unit/
├── test_combat.py
├── test_damage.py
├── test_ai.py
└── test_combatant.py

tests/integration/
└── test_combat_flow.py
```

## Dependencies (From Phase 1)
- Python 3.13
- SQLite 3.x (event store)
- Pydantic 2.10.0 (validation)
- pytest (testing)
- Phase 1 foundation: EventStore, StateMachine, GameContext

**Potential New Dependencies** (Research will determine):
- NumPy (if needed for damage calculations)
- None expected - using stdlib + existing dependencies

## Constitution Compliance

Phase 2 must maintain all Phase 1 principles:
- ✅ Event sourcing (all combat actions as events)
- ✅ Dependency injection (no globals)
- ✅ Type safety (type hints on all functions)
- ✅ Separation of concerns (combat logic vs. display)
- ✅ >= 80% test coverage
- ✅ Specific error handling
- ✅ Google-style docstrings
- ✅ 60 FPS target maintained

## Success Criteria (Preliminary)

**Research Phase**:
- [ ] All 6 research topics completed and documented
- [ ] Performance benchmarks defined
- [ ] Assumptions documented and validated
- [ ] Constitution compliance verified
- [ ] Ready to create decision document

**Decision Phase**:
- [ ] All major design decisions documented as ADRs
- [ ] Trade-offs explicitly analyzed
- [ ] Implementation guidance provided
- [ ] Constitution compliance maintained

**Implementation Phase**:
- [ ] All combat features implemented
- [ ] >= 80% test coverage
- [ ] All integration tests passing
- [ ] Performance benchmarks met
- [ ] Zero technical debt

**Validation Phase**:
- [ ] Combat playable end-to-end (text-based)
- [ ] Event replay working for combat
- [ ] Documentation complete
- [ ] Retrospective written

## Key Design Questions (To Answer in Research)

1. What actions should Phase 2 support? (Attack, Defend, Item, Ability, Flee)
2. How complex should damage formulas be?
3. Should combat create timeline branch points?
4. Do we support multi-party combat in Phase 2?
5. What happens when the player dies?
6. How smart should enemy AI be?

## Getting Help
- Review MDC rules: `.cursor/rules/architect-supervisor.mdc`
- Ask: `@architect-supervisor` for design and coordination
- Ask: `@game-logic-worker` for combat mechanics and state machines
- Ask: `@data-worker` for event schema and persistence

## Previous Phase
**Phase 1: Core Game Loop** - ✅ Complete
- Event sourcing foundation established
- State machine with 8 game states
- Fixed timestep game loop (59.80 Hz)
- 161 tests, 100% passing
- 100% constitution compliance

## Next Phase
After completion, proceed to **Phase 3: Timeline Mechanics**

---

**Created**: 2025-11-25  
**Last Updated**: 2025-11-25  
**Phase Lead**: @architect-supervisor

