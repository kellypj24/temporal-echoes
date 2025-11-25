# Research Document: Combat System

**Phase**: Phase 2  
**Created**: 2025-11-25  
**Status**: 🔄 In Progress  

## Overview

Phase 2 implements the core turn-based combat system for Temporal Echoes. This research validates our combat mechanics design, damage calculation formulas, and integration with the event sourcing architecture established in Phase 1. 

**Key Challenge**: Designing a combat system that is deterministic (for event replay), extensible (for timeline mechanics), and maintains 60 FPS performance while integrating with our existing state machine and event store.

## Research Summary

**Total Topics**: 6  
**Completed**: 0  
**High Priority**: 4  
**Research Time**: TBD  

---

## Research Topics

### Topic 1: Turn-Based Combat Mechanics
**Status**: 🔲 Not Started  
**Priority**: 🔴 High  
**Assigned To**: AI Agent  

**Why Research Needed**:
We need to design a turn-based combat system that integrates with our existing state machine, supports deterministic replay through event sourcing, and provides a solid foundation for AI narrative generation (Phase 4). The action economy and turn order must be both engaging and mathematically sound.

**Questions to Answer**:
1. What is the optimal action economy for a 16-bit RPG? (Actions per turn, action points, cooldowns)
2. How should turn order be calculated? (Speed-based, initiative-based, or hybrid)
3. How do combat state transitions integrate with our existing GameState enum?
4. What combat actions should Phase 2 support? (Attack, Defend, Item, Ability, Flee)
5. How do we handle multi-enemy combat scenarios?
6. How should combo systems or chain attacks work?

**Research Sources**:
- [ ] Classic 16-bit RPG mechanics analysis (Final Fantasy, Chrono Trigger)
- [ ] Modern turn-based game design patterns
- [ ] Game design documentation for action economy
- [ ] Academic papers on game balance
- [ ] Community forums for game design best practices

**Research Methodology**:
1. Analyze combat systems from reference 16-bit RPGs
2. Evaluate complexity vs. implementation time trade-offs
3. Design state transition diagram for combat flow
4. Prototype damage formulas for balance testing
5. Validate determinism for event replay

**Findings**:
[To be completed]

**Key Insights**:
- [To be added after research]

**Decision**:
[To be made based on findings]

**Implementation Guidance**:
[To be provided after research completion]

**Confidence Level**: 🔲 Not Yet Assessed

**References**:
- [To be added]

---

### Topic 2: Damage Calculation System
**Status**: 🔲 Not Started  
**Priority**: 🔴 High  
**Assigned To**: AI Agent  

**Why Research Needed**:
The damage calculation system is critical for game balance and must be deterministic for event sourcing replay. We need formulas that are simple enough to implement and test but deep enough to support progression, equipment, and elemental mechanics.

**Questions to Answer**:
1. What is the base damage formula? (ATK - DEF, multiplicative, or hybrid)
2. How should critical hits be calculated? (% chance, multiplier)
3. How do elemental weaknesses/resistances work?
4. How do status effects modify damage? (Poison, Burn, Buffs)
5. How do we ensure damage scales properly with level progression?
6. What variance should damage have? (Fixed, ±10%, ±20%)
7. How do we make damage calculation deterministic for replay?

**Research Sources**:
- [ ] RPG damage formula documentation (D&D, Final Fantasy)
- [ ] Game balance spreadsheets and simulators
- [ ] Academic papers on RPG combat balance
- [ ] Community discussions on damage scaling
- [ ] YouTube videos analyzing classic RPG formulas

**Research Methodology**:
1. Collect damage formulas from 5+ classic 16-bit RPGs
2. Analyze scaling behavior across levels 1-50
3. Design spreadsheet to test balance scenarios
4. Validate determinism with fixed random seeds
5. Test edge cases (0 defense, max damage, overflow)

**Findings**:
[To be completed]

**Key Insights**:
- [To be added after research]

**Decision**:
[To be made based on findings]

**Implementation Guidance**:
[To be provided after research completion]

**Confidence Level**: 🔲 Not Yet Assessed

**References**:
- [To be added]

---

### Topic 3: Combat Event Schema Design
**Status**: 🔲 Not Started  
**Priority**: 🔴 High  
**Assigned To**: AI Agent  

**Why Research Needed**:
Combat must integrate seamlessly with our existing event sourcing architecture. We need to define combat event types, their JSON payloads, and how they support replay, analytics, and timeline branching.

**Questions to Answer**:
1. What combat event types do we need? (combat_started, turn_start, action_executed, damage_dealt, combat_ended)
2. What data must each event contain for complete replay?
3. How do combat events integrate with the existing game_events table?
4. How do we handle multi-step actions (attack → damage → status effect)?
5. What combat events should trigger timeline branch points?
6. How do combat events support dbt analytics queries?
7. Should combat have its own read model table or derive from events?

**Research Sources**:
- [ ] Event sourcing best practices for game state
- [ ] CQRS patterns for combat systems
- [ ] Review Phase 1 event store implementation
- [ ] GitHub examples of event-sourced game engines
- [ ] dbt modeling patterns for event data

**Research Methodology**:
1. Review Phase 1 GameEvent schema and EventStore implementation
2. Design combat event type taxonomy
3. Create sample event payloads for all combat actions
4. Validate replay completeness with sample combat sequences
5. Design dbt models for combat analytics
6. Prototype read model table schema if needed

**Findings**:
[To be completed]

**Key Insights**:
- [To be added after research]

**Decision**:
[To be made based on findings]

**Implementation Guidance**:
[To be provided after research completion]

**Confidence Level**: 🔲 Not Yet Assessed

**References**:
- [To be added]

---

### Topic 4: Enemy AI Behavior Patterns
**Status**: 🔲 Not Started  
**Priority**: 🔴 High  
**Assigned To**: AI Agent  

**Why Research Needed**:
Phase 2 needs simple rule-based AI for enemy decision-making that is deterministic, testable, and provides a foundation for AI narrative enhancement in Phase 4. The AI must be good enough to challenge players without requiring LLM integration yet.

**Questions to Answer**:
1. What is the simplest viable enemy AI system? (Random, weighted random, rule-based)
2. How should enemy difficulty scale? (Health/damage multipliers, smarter behavior)
3. What personality types should enemies have? (Aggressive, Defensive, Balanced, Healer)
4. How do we make AI decisions deterministic for replay?
5. How does enemy AI integrate with the event store?
6. What hooks do we need for Phase 4 AI narrative generation?
7. Should enemies have "memory" of previous turns?

**Research Sources**:
- [ ] Game AI programming patterns
- [ ] Finite state machine AI for games
- [ ] Behavior tree basics
- [ ] Classic RPG enemy AI analysis
- [ ] Academic papers on deterministic game AI

**Research Methodology**:
1. Analyze enemy AI patterns from 3-5 classic 16-bit RPGs
2. Design simple decision tree for enemy actions
3. Create enemy archetypes with distinct behaviors
4. Prototype deterministic random selection with seeded RNG
5. Design integration points for Phase 4 AI narrative
6. Test AI decision-making in isolation

**Findings**:
[To be completed]

**Key Insights**:
- [To be added after research]

**Decision**:
[To be made based on findings]

**Implementation Guidance**:
[To be provided after research completion]

**Confidence Level**: 🔲 Not Yet Assessed

**References**:
- [To be added]

---

### Topic 5: Combat State Management & UI Requirements
**Status**: 🔲 Not Started  
**Priority**: 🟡 Medium  
**Assigned To**: AI Agent  

**Why Research Needed**:
While Phase 2 won't have full pygame rendering, we need to define what combat state must be tracked and how it will be displayed (text-based output). This ensures Phase 5 rendering can be added without refactoring core combat logic.

**Questions to Answer**:
1. What combat state must be tracked? (HP, turn order, active combatants, status effects)
2. How should combat state integrate with GameContext?
3. What text output is needed for Phase 2 testing?
4. What data structures prepare for Phase 5 pygame rendering?
5. How do we display combat state without violating separation of concerns?
6. How should combat logs be structured for debugging and AI narrative?

**Research Sources**:
- [ ] Review Phase 1 GameContext implementation
- [ ] MVC pattern for game state display
- [ ] Terminal-based RPG combat examples
- [ ] Pygame combat UI patterns (for future planning)
- [ ] Combat log design patterns

**Research Methodology**:
1. Review existing GameContext implementation
2. Design CombatContext data structure
3. Create text-based combat output format
4. Identify separation boundaries (logic vs. display)
5. Design hooks for Phase 5 pygame integration
6. Prototype combat log structure

**Findings**:
[To be completed]

**Key Insights**:
- [To be added after research]

**Decision**:
[To be made based on findings]

**Implementation Guidance**:
[To be provided after research completion]

**Confidence Level**: 🔲 Not Yet Assessed

**References**:
- [To be added]

---

### Topic 6: Combat Testing Strategy
**Status**: 🔲 Not Started  
**Priority**: 🟡 Medium  
**Assigned To**: AI Agent  

**Why Research Needed**:
Combat systems are complex and prone to edge cases. We need a comprehensive testing strategy that covers determinism, balance validation, event replay, and integration with the existing test suite.

**Questions to Answer**:
1. How do we test combat deterministically? (Fixed random seeds)
2. What are the critical test scenarios? (Player wins, loses, flees, multi-enemy)
3. How do we test damage formula edge cases? (0 defense, max damage, overflow)
4. How do we validate event replay for combat sequences?
5. How do we test enemy AI behavior patterns?
6. What performance benchmarks must combat meet? (60 FPS with X enemies)
7. How do we structure integration tests for combat flow?

**Research Sources**:
- [ ] Review Phase 1 testing patterns (161 tests, 100% coverage)
- [ ] pytest best practices for game logic
- [ ] Property-based testing for combat formulas
- [ ] Game testing articles and conference talks
- [ ] Test fixture design for combat scenarios

**Research Methodology**:
1. Review existing test suite structure
2. Design test fixtures for common combat scenarios
3. Identify edge cases and error conditions
4. Create test data generators for combat entities
5. Design property-based tests for damage formulas
6. Prototype integration tests for full combat sequences

**Findings**:
[To be completed]

**Key Insights**:
- [To be added after research]

**Decision**:
[To be made based on findings]

**Implementation Guidance**:
[To be provided after research completion]

**Confidence Level**: 🔲 Not Yet Assessed

**References**:
- [To be added]

---

## Tech Stack Validation

**Purpose**: Validate that existing Phase 1 dependencies are sufficient for combat implementation.

| Component | Current Version | Phase 2 Needs | Breaking Changes? | Action | Notes |
|-----------|----------------|---------------|-------------------|--------|-------|
| Python | 3.13 | ✅ Sufficient | N/A | ✅ OK | Dataclasses, type hints |
| Pydantic | 2.10.0 | ✅ Sufficient | N/A | ✅ OK | Combat entity validation |
| SQLite | System | ✅ Sufficient | N/A | ✅ OK | Event store established |
| pytest | Latest | ✅ Sufficient | N/A | ✅ OK | Testing patterns established |
| NumPy | Not installed | ⚠️ Optional | N/A | 🔍 Research | Damage formula optimization? |

**Legend**:
- ✅ OK to use
- ⚠️ Needs investigation
- ❌ Must add/upgrade

**Action Items**:
- [ ] Determine if NumPy needed for damage calculations (performance vs. simplicity)
- [ ] Verify existing test fixtures can support combat scenarios
- [ ] Validate that event store schema can handle combat events without migration

---

## Assumptions Made

### Assumption 1: Event Store Schema is Extensible
**Assumption**: The Phase 1 event store JSON payload can accommodate all combat events without schema migration.

**Why Made**: Phase 1 used flexible JSON for event data; combat events should fit naturally.

**Risk if Wrong**: 
- **Severity**: 🟡 Moderate - Would require schema migration
- **Likelihood**: 🟢 Low - JSON is flexible

**Validation Plan**: 
1. Review Phase 1 GameEvent schema
2. Create sample combat event payloads
3. Verify no schema changes needed

**Timeline**: During Topic 3 research (Combat Event Schema)

**Mitigation**: If schema change needed, create migration script and test with existing events

**Status**: 🔲 Not Yet Validated

---

### Assumption 2: 60 FPS Maintained with Combat Logic
**Assumption**: Combat calculations can execute within 16.67ms frame budget without optimization.

**Why Made**: Phase 1 achieved 59.80 Hz with event store writes; combat logic should be similarly fast.

**Risk if Wrong**:
- **Severity**: 🟡 Moderate - Would violate constitution principle #14
- **Likelihood**: 🟢 Low - Combat logic is simple arithmetic

**Validation Plan**:
1. Benchmark damage calculation formulas
2. Test with multiple simultaneous combats (edge case)
3. Profile combat event emission

**Timeline**: During implementation, before Step 1 completion

**Mitigation**: If too slow, optimize hot paths or simplify formulas

**Status**: 🔲 Not Yet Validated

---

### Assumption 3: No External Combat Library Needed
**Assumption**: We can implement combat from scratch without libraries like pygame-rpg or similar.

**Why Made**: 
- Educational value for developer
- Full control over architecture
- Simple combat system doesn't justify dependency

**Risk if Wrong**:
- **Severity**: 🟢 Low - Worst case: more implementation time
- **Likelihood**: 🟡 Medium - Combat systems can be complex

**Validation Plan**:
1. Research available Python combat libraries
2. Evaluate features vs. implementation effort
3. Assess learning value of from-scratch implementation

**Timeline**: During Topic 1 research (Combat Mechanics)

**Mitigation**: If complexity exceeds estimate, evaluate lightweight library or simplify feature set

**Status**: 🔲 Not Yet Validated

---

### Assumption 4: Text-Based Output Sufficient for Phase 2
**Assumption**: We can validate combat logic with text output, deferring pygame rendering to Phase 5.

**Why Made**: Separation of concerns; want to perfect logic before UI.

**Risk if Wrong**:
- **Severity**: 🟢 Low - Only impacts development UX
- **Likelihood**: 🟢 Low - Testing doesn't require rendering

**Validation Plan**:
1. Design clear text-based combat output format
2. Validate that all combat state is observable via text
3. Ensure integration tests don't require pygame

**Timeline**: During Topic 5 research (Combat State Management)

**Mitigation**: If text output insufficient, add minimal pygame debug UI

**Status**: 🔲 Not Yet Validated

---

### Assumption 5: Simple Rule-Based AI Sufficient for Phase 2
**Assumption**: Players will accept simple enemy AI without LLM narrative enhancement until Phase 4.

**Why Made**: Phased approach; want combat mechanics solid before adding AI complexity.

**Risk if Wrong**:
- **Severity**: 🟢 Low - Only impacts playability testing
- **Likelihood**: 🟢 Low - Classic RPGs had simple AI

**Validation Plan**:
1. Design 3-4 distinct enemy behavior patterns
2. Playtest combat for engagement
3. Document AI limitations for Phase 4 enhancement

**Timeline**: During Topic 4 research (Enemy AI)

**Mitigation**: If too simplistic, add behavior trees or weighted decision-making

**Status**: 🔲 Not Yet Validated

---

## Performance Benchmarks

**Purpose**: Establish performance targets for combat system.

### Benchmark 1: Damage Calculation Speed
**Component**: Damage formula execution

**Method**: 
1. Execute 10,000 damage calculations
2. Measure average time per calculation
3. Test with various stat ranges (level 1 to 50)

**Target**: < 0.01ms per calculation (100,000+ calcs per second)

**Rationale**: Must support multiple enemies attacking in same frame

**Status**: 🔲 Not Yet Measured

**Action**: Benchmark during Topic 2 research

---

### Benchmark 2: Combat Event Write Performance
**Component**: Event store writes for combat events

**Method**:
1. Simulate full combat sequence (10 turns)
2. Measure total event write time
3. Compare to Phase 1 baseline (< 1ms per event)

**Target**: Full combat sequence events < 20ms (not in critical path)

**Rationale**: Must not block game loop

**Status**: 🔲 Not Yet Measured

**Action**: Benchmark during Topic 3 research

---

### Benchmark 3: Enemy AI Decision Time
**Component**: Enemy action selection logic

**Method**:
1. Execute 1,000 AI decisions
2. Measure average time per decision
3. Test with varying complexity levels

**Target**: < 0.1ms per decision

**Rationale**: Multiple enemies must decide actions within frame budget

**Status**: 🔲 Not Yet Measured

**Action**: Benchmark during Topic 4 research

---

## Security Considerations

**Purpose**: Identify security risks in combat system.

### Risk 1: Integer Overflow in Damage Calculations
**Description**: Extremely high ATK or DEF values could cause integer overflow, leading to negative damage or instant kills.

**Severity**: 🟡 High - Could break game balance

**Mitigation**: 
1. Define maximum stat values (MAX_STAT = 9999)
2. Use Python's arbitrary precision integers
3. Clamp damage values to reasonable range [0, MAX_DAMAGE]
4. Add overflow tests to test suite

**Status**: 🔲 Planned

---

### Risk 2: Deterministic Random Number Manipulation
**Description**: If players discover random seed mechanism, they could manipulate combat outcomes.

**Severity**: 🟢 Medium - Single-player game, less critical

**Mitigation**:
1. Use cryptographically secure random for seed generation
2. Don't expose seed in save files
3. Re-seed on timeline branch to prevent exploit reuse
4. Document as known limitation for single-player context

**Status**: 🔲 Planned

---

### Risk 3: Event Replay Exploit
**Description**: Players could replay favorable combat outcomes by manipulating event store.

**Severity**: 🟢 Medium - Single-player, player choice

**Mitigation**:
1. Accept as feature rather than bug (player agency)
2. Document that event store tampering is player's choice
3. Consider checksum validation for future multiplayer
4. Don't spend dev time preventing single-player "cheating"

**Status**: ✅ Mitigated - Accepted as design decision

---

## Questions for Expert Review

**Purpose**: Identify areas requiring human expertise or design decisions.

1. **Combat Complexity vs. Scope**:
   - **Context**: We could build a simple attack/defend system OR include items, abilities, status effects
   - **Impact**: Determines Phase 2 timeline and testing complexity
   - **Urgency**: 🔴 High - Affects all research topics

2. **Timeline Branching in Combat**:
   - **Context**: Should combat outcomes create timeline branches? Or only story choices?
   - **Impact**: Affects combat event schema and Phase 3 integration
   - **Urgency**: 🟡 Medium - Can defer to Phase 3

3. **Multi-Party Combat**:
   - **Context**: Should Phase 2 support party members, or only 1v1 and 1vN?
   - **Impact**: Significantly increases complexity
   - **Urgency**: 🟡 Medium - Could defer to Phase 3

4. **Death/Game Over Handling**:
   - **Context**: What happens when player dies? Respawn, reload, timeline branch?
   - **Impact**: Affects save system and game loop state transitions
   - **Urgency**: 🟡 Medium - Related to timeline mechanics

---

## Research Timeline

| Topic | Priority | Estimated Duration | Dependencies | Blocker? |
|-------|----------|-------------------|--------------|----------|
| Topic 1: Combat Mechanics | 🔴 High | 3-4 hours | None | No |
| Topic 2: Damage Calculation | 🔴 High | 2-3 hours | Topic 1 | No |
| Topic 3: Combat Event Schema | 🔴 High | 2-3 hours | Phase 1 event store | No |
| Topic 4: Enemy AI | 🔴 High | 2-3 hours | Topic 1 | No |
| Topic 5: Combat State/UI | 🟡 Medium | 2 hours | Topic 1, Topic 3 | No |
| Topic 6: Testing Strategy | 🟡 Medium | 2 hours | Phase 1 tests | No |

**Total Estimated Research Time**: 13-17 hours

**Critical Path**: Topics 1-4 must complete before decisions phase

**Parallelization**: Topics 2, 3, and 4 can be researched in parallel after Topic 1

---

## Lessons Learned

**Purpose**: Capture insights for future phases.

### What Worked Well in Phase 1
1. **Research-First Approach**: Eliminated rework and technical debt
2. **Decision Documentation (ADRs)**: Made trade-offs explicit and reviewable
3. **Constitution Checkpoints**: Prevented shortcuts that would accumulate debt
4. **Test-Driven Development**: 161 tests gave confidence to refactor
5. **Detailed PR Descriptions**: Moderate length hit sweet spot for review

### What to Apply to Phase 2
1. Complete all research before creating decision document
2. Use ADR format for all major combat design decisions
3. Maintain >= 80% test coverage throughout
4. Document assumptions and validate them early
5. Benchmark performance during research, not after implementation

### Research Improvements for Phase 2
1. **Parallel Research**: Topics 2-4 can be done simultaneously
2. **Prototype Early**: Build damage calculator spreadsheet during research
3. **Visual Aids**: Create state diagrams and flowcharts during research
4. **Reference Games**: Play 2-3 classic RPGs to validate design choices
5. **Expert Questions**: Front-load design questions to unblock research

---

## Constitution Compliance

**Purpose**: Verify research findings align with Phase 1 principles.

### Pre-Research Checklist
- [ ] Research plan supports event sourcing (Principle #1)
- [ ] Combat design allows dependency injection (Principle #2)
- [ ] Type hints planned for all combat entities (Principle #3)
- [ ] Separation of concerns: combat logic vs. display (Principle #4)
- [ ] Testing strategy targets >= 80% coverage (Principle #5)
- [ ] Error handling patterns planned (Principle #6)
- [ ] Documentation standards defined (Principle #7)
- [ ] Events will be immutable (Principle #11)
- [ ] Transaction safety maintained (Principle #12)
- [ ] 60 FPS target considered (Principle #14)

### Potential Conflicts
**None identified yet** - Research phase will validate compatibility

### Resolution Plan
If conflicts emerge during research:
1. Document the specific conflict
2. Evaluate trade-offs (game design vs. architecture)
3. Propose solution that minimizes constitution deviation
4. Get explicit approval before proceeding
5. Track as technical debt if deviation accepted

---

## Sign-off

- [ ] All high-priority research complete (Topics 1-4)
- [ ] Medium-priority research complete or deferred with justification (Topics 5-6)
- [ ] Critical decisions identified for decision phase
- [ ] Assumptions documented and validation plan created
- [ ] Performance benchmarks defined
- [ ] Security risks identified and mitigation planned
- [ ] Constitution compliance verified
- [ ] Ready to proceed with decision phase

**Research Lead**: AI Agent (Architect Supervisor)  
**Start Date**: 2025-11-25  
**Completion Date**: TBD  
**Approved By**: [Human Developer]  
**Approval Date**: TBD

---

## Next Steps After Research Completion

1. **Create `decisions.md`**: Document all architecture decisions as ADRs
2. **Update `PLAN.md`**: Create detailed implementation plan with steps
3. **Create Step Prompts**: Detailed execution prompts for each implementation step
4. **Constitution Checkpoint**: Final verification before implementation
5. **Begin Implementation**: Execute plan following SDD workflow

