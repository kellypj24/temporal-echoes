# Phase 2: Combat System

**Status**: 🔲 Ready to Start  
**Started**: TBD  
**Completed**: TBD  
**Branch**: `phase/2-combat-system`

## Phase Workflow Status

This phase follows the Spec-Driven Development (SDD) approach:

1. **🔍 Research Phase** ✅ COMPLETE
   - All 6 research topics completed
   - 5 assumptions validated
   - Performance benchmarks defined
   - Duration: 9 hours

2. **📋 Decision Phase** ✅ COMPLETE
   - 10 ADRs documented in `decisions.md`
   - All alternatives analyzed
   - 0 constitution deviations
   - Trade-offs explicitly stated

3. **🛠️ Implementation Phase** 🔲 READY TO START
   - Execute 6 implementation steps
   - Follow decisions and research guidance
   - Maintain >= 80% test coverage
   - Target: 20-25 hours

4. **✅ Validation Phase** ⏳ PENDING
   - Integration tests
   - Performance benchmarks
   - Constitution compliance check
   - Retrospective

---

## Objectives

**Primary Objectives**:
- ✅ Implement turn-based combat system with Octopath-inspired mechanics
- ✅ Support Boost Points and Break System
- ✅ Create weighted random enemy AI with 4 archetypes
- ✅ Integrate combat events with Phase 1 event store
- ✅ Achieve deterministic replay with seeded RNG
- ✅ Maintain >= 80% test coverage
- ✅ Preserve 60 FPS performance target

**Success Metrics**:
- All combat features functional (attack, defend, item, ability, flee)
- 1v1 to 1v3 combat working
- Event replay produces identical outcomes
- All integration tests passing
- Text-based combat output validates correctness

---

## Prerequisites

### Hard Prerequisites
- [x] Phase 1 complete (event store, state machine, game context)
- [x] Poetry environment configured
- [x] Python 3.13 installed
- [x] SQLite available (built-in)
- [x] pytest installed

### Research Prerequisites
- [x] `research.md` completed (6/6 topics)
- [x] All high-priority research addressed
- [x] Assumptions validated (5/5)
- [x] Tech stack confirmed (no new dependencies)

### Decision Prerequisites
- [x] `decisions.md` created (10 ADRs)
- [x] Constitution compliance verified (0 deviations)
- [x] No technical debt identified
- [x] Implementation guidance documented

---

## Context

Phase 2 builds the combat system on top of Phase 1's event sourcing and state machine foundation. The combat system is deterministic, testable, and prepares for Phase 3 (timeline mechanics) and Phase 4 (AI narrative).

**Key Design Decisions**:
- Octopath Traveler-inspired mechanics (DEC-2001)
- Hybrid damage formula with multipliers (DEC-2002)
- No database migration needed (DEC-2003)
- Weighted random AI with 4 archetypes (DEC-2005)
- Deterministic with seeded RNG (DEC-2006)

**Related Documents**:
- `research.md` - Research findings (9 hours of research)
- `decisions.md` - 10 architecture decisions
- `RESEARCH_SUMMARY.md` - Quick reference
- `.cursor/rules/CONSTITUTION.md` - Development principles
- `.cursor/rules/architect-supervisor.mdc` - Phase workflow

---

## Implementation Steps

### Step 1: Combat Entities and Base Classes
**Supervisors**: `@architect-supervisor`, `@game-logic-worker`  
**Branch**: `feature/phase-2-step-1-entities`  
**Estimated Time**: 3-4 hours

**Description**:
Create the foundational entity classes for combat: `Combatant` (base class), `Player`, and `Enemy`. Implement Boost Point system and Break System mechanics per DEC-2001.

**Tasks**:
- [ ] Create `src/entities/__init__.py`
- [ ] Implement `Combatant` base class with shared attributes (HP, ATK, DEF, Speed)
- [ ] Implement `Player` class with Boost Points (0-5 BP)
- [ ] Implement `Enemy` class with Break System (shield points, weaknesses)
- [ ] Add `DamageType` enum (PHYSICAL, FIRE, ICE, etc.)
- [ ] Create entity factories for testing
- [ ] Write unit tests for all entity classes

**Success Criteria**:
- [ ] Unit tests pass: `pytest tests/unit/test_entities.py -v`
- [ ] Code coverage >= 80% for entities module
- [ ] No linting errors: `make lint`
- [ ] Manual validation: Can instantiate Player and Enemy with correct stats
- [ ] Boost Points gain/spend logic works correctly
- [ ] Shield points reduce correctly on weakness hits

**Files to Create**:
- `src/entities/__init__.py` - Module exports
- `src/entities/combatant.py` - Base Combatant class (~100 lines)
- `src/entities/player.py` - Player entity (~120 lines)
- `src/entities/enemy.py` - Enemy entity with Break system (~150 lines)
- `src/entities/damage_types.py` - DamageType enum (~30 lines)
- `tests/unit/test_entities.py` - Entity tests (~200 lines)
- `tests/fixtures/entity_fixtures.py` - Test fixtures (~50 lines)

**Implementation Guidance from Research**:
```python
@dataclass
class Combatant(ABC):
    """Base class for all combat participants."""
    id: str
    name: str
    level: int
    hp: int
    max_hp: int
    attack: int
    defense: int
    speed: int
    
    @property
    def hp_percent(self) -> float:
        """HP as percentage (0-100)."""
        return (self.hp / self.max_hp) * 100 if self.max_hp > 0 else 0
    
    @property
    def is_alive(self) -> bool:
        """Check if combatant can act."""
        return self.hp > 0
    
    @abstractmethod
    def take_damage(self, damage: int, damage_type: DamageType) -> DamageResult:
        """Apply damage and return result."""
        pass

@dataclass
class Player(Combatant):
    """Player character with Boost Points."""
    boost_points: int = 0
    max_boost_points: int = 5
    
    def gain_bp(self) -> None:
        """Gain 1 BP per turn (max 5)."""
        self.boost_points = min(self.boost_points + 1, self.max_boost_points)
    
    def spend_bp(self, amount: int) -> float:
        """Spend BP and return damage multiplier."""
        if amount > self.boost_points:
            raise ValueError(f"Not enough BP: have {self.boost_points}, need {amount}")
        
        self.boost_points -= amount
        return {0: 1.0, 1: 1.5, 2: 2.0, 3: 2.5}[amount]

@dataclass
class Enemy(Combatant):
    """Enemy with Break System."""
    shield_points: int
    max_shield_points: int
    weaknesses: list[DamageType]
    is_broken: bool = False
    break_turns_remaining: int = 0
    
    def take_damage(self, damage: int, damage_type: DamageType) -> DamageResult:
        """Apply damage with break system."""
        # Break multiplier
        multiplier = 1.5 if self.is_broken else 1.0
        actual_damage = int(damage * multiplier)
        
        # Check weakness
        weakness_hit = damage_type in self.weaknesses
        if weakness_hit and not self.is_broken:
            self.shield_points -= 1
            if self.shield_points <= 0:
                self.trigger_break()
        
        self.hp = max(0, self.hp - actual_damage)
        
        return DamageResult(
            damage=actual_damage,
            weakness_hit=weakness_hit,
            shield_broken=(self.shield_points == 0 and weakness_hit)
        )
    
    def trigger_break(self) -> None:
        """Break enemy (stun for 1 turn)."""
        self.is_broken = True
        self.break_turns_remaining = 1
```

**Related Decisions**: DEC-2001, DEC-2009

---

### Step 2: Damage Calculation System
**Supervisors**: `@architect-supervisor`, `@game-logic-worker`  
**Branch**: `feature/phase-2-step-2-damage`  
**Estimated Time**: 2-3 hours

**Description**:
Implement the hybrid damage formula with all multipliers (boost, type, critical, break) per DEC-2002. Include deterministic RNG for variance and critical hits.

**Tasks**:
- [ ] Create `src/core/damage.py` module
- [ ] Implement `DamageCalculator` class with seeded RNG
- [ ] Implement hybrid damage formula
- [ ] Add all multiplier calculations (boost, type, crit, break)
- [ ] Add damage clamping (1-9999 range)
- [ ] Write comprehensive unit tests
- [ ] Add property-based tests for edge cases

**Success Criteria**:
- [ ] Unit tests pass: `pytest tests/unit/test_damage.py -v`
- [ ] Property tests validate formula properties (never < 1, never > 9999)
- [ ] Determinism test: same seed = same damage
- [ ] Code coverage >= 80%
- [ ] Benchmark: damage calc < 0.01ms per calculation
- [ ] No linting errors

**Files to Create**:
- `src/core/damage.py` - DamageCalculator class (~250 lines)
- `tests/unit/test_damage.py` - Damage tests (~300 lines)
- `tests/unit/test_damage_properties.py` - Property tests (~100 lines)

**Implementation Guidance from Research**:
```python
class DamageCalculator:
    """Deterministic damage calculation with all modifiers."""
    
    def __init__(self, rng_seed: int):
        self.rng = random.Random(rng_seed)
    
    def calculate(
        self,
        attacker_atk: int,
        defender_def: int,
        skill_power: int = 100,
        boost_points: int = 0,
        damage_type: DamageType = DamageType.PHYSICAL,
        defender_weaknesses: list[DamageType] = [],
        defender_is_broken: bool = False,
        crit_chance: int = 5,
    ) -> DamageResult:
        """
        Calculate damage with formula:
        Damage = (ATK * Power / (DEF * 0.5 + 10))
                 * Random(0.85, 1.00)
                 * Boost_Mult * Type_Mult * Crit_Mult * Break_Mult
                 → Clamped [1, 9999]
        """
        # Base damage
        safe_def = max(1, defender_def)
        base_damage = (attacker_atk * skill_power) / (safe_def * 0.5 + 10)
        
        # Random variance (85-100%)
        random_factor = self.rng.uniform(0.85, 1.00)
        damage = base_damage * random_factor
        
        # Boost multiplier
        boost_mult = {0: 1.0, 1: 1.5, 2: 2.0, 3: 2.5}[min(boost_points, 3)]
        damage *= boost_mult
        
        # Type effectiveness
        type_mult = 2.0 if damage_type in defender_weaknesses else 1.0
        damage *= type_mult
        
        # Critical hit
        is_crit = self.rng.randint(1, 100) <= crit_chance
        crit_mult = 1.5 if is_crit else 1.0
        damage *= crit_mult
        
        # Break bonus
        break_mult = 1.5 if defender_is_broken else 1.0
        damage *= break_mult
        
        # Clamp to valid range
        final_damage = int(damage)
        final_damage = max(1, min(final_damage, 9999))
        
        return DamageResult(
            damage=final_damage,
            is_critical=is_crit,
            is_weakness=type_mult > 1.0,
            multipliers={
                "boost": boost_mult,
                "type": type_mult,
                "critical": crit_mult,
                "break": break_mult
            }
        )
```

**Related Decisions**: DEC-2002, DEC-2006

---

### Step 3: Combat Event Integration
**Supervisors**: `@architect-supervisor`, `@data-worker`  
**Branch**: `feature/phase-2-step-3-events`  
**Estimated Time**: 2-3 hours

**Description**:
Extend Phase 1's event system with combat event types and builders per DEC-2003 and DEC-2004. No database migration needed - only Python code additions.

**Tasks**:
- [ ] Add combat event types to `src/core/events.py` EventTypes class
- [ ] Create `src/core/combat_events.py` event builder module
- [ ] Implement `CombatEventBuilder` class for creating combat events
- [ ] Add Pydantic schemas for event validation (optional but recommended)
- [ ] Write unit tests for event creation
- [ ] Validate events can be stored/retrieved from Phase 1 EventStore

**Success Criteria**:
- [ ] Unit tests pass: `pytest tests/unit/test_combat_events.py -v`
- [ ] Events store successfully in existing game_events table
- [ ] Events retrieve correctly by aggregate_id (combat_id)
- [ ] JSON payloads match research specifications
- [ ] Code coverage >= 80%
- [ ] No database migration required (validate with existing DB)

**Files to Create/Modify**:
- `src/core/events.py` - Add combat event type constants (~20 lines added)
- `src/core/combat_events.py` - CombatEventBuilder class (~300 lines)
- `tests/unit/test_combat_events.py` - Event tests (~200 lines)

**Implementation Guidance from Research**:
```python
# Add to src/core/events.py EventTypes class
class EventTypes:
    # ... existing events ...
    
    # Combat events (Phase 2)
    COMBAT_STARTED = "CombatStarted"
    COMBAT_ENDED = "CombatEnded"
    TURN_STARTED = "TurnStarted"
    ACTION_EXECUTED = "ActionExecuted"
    SHIELD_BROKEN = "ShieldBroken"
    BOOST_POINT_GAINED = "BoostPointGained"
    COMBATANT_DEFEATED = "CombatantDefeated"
    COMBAT_FLED = "CombatFled"

# src/core/combat_events.py
@dataclass
class CombatEventBuilder:
    """Helper to build combat events with correct schema."""
    
    session_id: str
    timeline_id: str
    combat_id: str
    
    def combat_started(
        self,
        rng_seed: int,
        player: dict,
        enemies: list[dict],
        **kwargs
    ) -> GameEvent:
        """Create CombatStarted event with all combatant data."""
        return GameEvent(
            event_type=EventTypes.COMBAT_STARTED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            event_data=json.dumps({
                "combat_id": self.combat_id,
                "rng_seed": rng_seed,
                "player": player,
                "enemies": enemies,
                **kwargs
            })
        )
    
    def action_executed(
        self,
        actor_id: str,
        target_id: str,
        damage_dealt: int,
        **kwargs
    ) -> GameEvent:
        """Create composite ActionExecuted event."""
        return GameEvent(
            event_type=EventTypes.ACTION_EXECUTED,
            aggregate_id=self.combat_id,
            aggregate_type="combat",
            session_id=self.session_id,
            timeline_id=self.timeline_id,
            event_data=json.dumps({
                "combat_id": self.combat_id,
                "actor_id": actor_id,
                "target_id": target_id,
                "damage_dealt": damage_dealt,
                **kwargs
            })
        )
```

**Related Decisions**: DEC-2003, DEC-2004

---

### Step 4: Enemy AI Implementation
**Supervisors**: `@architect-supervisor`, `@game-logic-worker`  
**Branch**: `feature/phase-2-step-4-ai`  
**Estimated Time**: 3-4 hours

**Description**:
Implement weighted random enemy AI with 4 archetypes (Aggressive, Defensive, Tactical, Berserker) per DEC-2005. AI uses deterministic RNG for replay.

**Tasks**:
- [ ] Create `src/core/ai.py` module
- [ ] Implement `EnemyAI` base class
- [ ] Implement 4 archetype classes (Aggressive, Defensive, Tactical, Berserker)
- [ ] Add HP-based weight modifiers
- [ ] Create AI factory function
- [ ] Write unit tests for each archetype
- [ ] Validate determinism (same seed = same decisions)

**Success Criteria**:
- [ ] Unit tests pass: `pytest tests/unit/test_ai.py -v`
- [ ] Determinism test: same seed produces same action sequence
- [ ] Archetype behavior test: aggressive attacks more than defensive
- [ ] Benchmark: AI decision < 0.1ms
- [ ] Code coverage >= 80%
- [ ] HP modifier logic works correctly

**Files to Create**:
- `src/core/ai.py` - AI classes (~400 lines)
- `tests/unit/test_ai.py` - AI tests (~250 lines)

**Implementation Guidance from Research**:
```python
class AIArchetype(Enum):
    AGGRESSIVE = auto()
    DEFENSIVE = auto()
    TACTICAL = auto()
    BERSERKER = auto()

class EnemyAI(ABC):
    """Base class for enemy AI with deterministic decisions."""
    
    def __init__(self, enemy: Enemy, rng: random.Random):
        self.enemy = enemy
        self.rng = rng
        self.base_weights = self._get_base_weights()
    
    @abstractmethod
    def _get_base_weights(self) -> dict[str, int]:
        """Return archetype-specific base weights."""
        pass
    
    def select_action(self, combat_state: 'CombatState') -> CombatAction:
        """Select action using weighted random choice."""
        weights = self._calculate_situational_weights(combat_state)
        
        action_type = self.rng.choices(
            population=list(weights.keys()),
            weights=list(weights.values()),
            k=1
        )[0]
        
        return CombatAction(
            action_type=action_type,
            target_id="player"
        )

class AggressiveAI(EnemyAI):
    """Always attacks, rarely defends."""
    
    def _get_base_weights(self) -> dict[str, int]:
        return {"attack": 70, "defend": 10, "ability": 20}
    
    def _calculate_situational_weights(self, combat_state) -> dict[str, int]:
        weights = self.base_weights.copy()
        
        # Slightly defensive when low HP
        if self.enemy.hp_percent < 30:
            weights["defend"] = 25
            weights["attack"] = 50
        
        return weights
```

**Related Decisions**: DEC-2005, DEC-2006

---

### Step 5: Combat Manager and State Integration
**Supervisors**: `@architect-supervisor`, `@game-logic-worker`  
**Branch**: `feature/phase-2-step-5-combat-manager`  
**Estimated Time**: 4-5 hours

**Description**:
Implement `CombatContext` manager that orchestrates combat flow, integrates all systems (entities, damage, AI, events), and extends Phase 1's state machine with combat states.

**Tasks**:
- [ ] Extend `GameState` enum with combat substates
- [ ] Create `src/core/combat.py` module
- [ ] Implement `CombatContext` class
- [ ] Implement turn order calculation
- [ ] Implement combat action execution
- [ ] Integrate damage calculator, AI, and event builder
- [ ] Add text-based combat logger (DEC-2008)
- [ ] Write integration tests

**Success Criteria**:
- [ ] Integration tests pass: `pytest tests/integration/test_combat.py -v`
- [ ] Full combat sequence executes correctly (start → turns → end)
- [ ] Events are emitted for all actions
- [ ] Replay from events produces identical outcomes
- [ ] Text output shows combat flow clearly
- [ ] Code coverage >= 80%
- [ ] Performance: full combat < 100ms

**Files to Create/Modify**:
- `src/core/state_machine.py` - Add combat states (~30 lines added)
- `src/core/combat.py` - CombatContext class (~500 lines)
- `src/core/combat_logger.py` - Text output logger (~150 lines)
- `tests/integration/test_combat.py` - Integration tests (~400 lines)
- `tests/fixtures/combat_fixtures.py` - Combat fixtures (~100 lines)

**Implementation Guidance from Research**:
```python
# Extend GameState enum
class GameState(Enum):
    # ... existing states ...
    COMBAT_START = auto()
    COMBAT_PLAYER_TURN = auto()
    COMBAT_ENEMY_TURN = auto()
    COMBAT_EXECUTING = auto()
    COMBAT_END = auto()

# CombatContext
class CombatContext:
    """Combat session manager with all systems integrated."""
    
    def __init__(
        self,
        combat_id: str,
        seed: int,
        player: Player,
        enemies: list[Enemy],
        event_store: EventStore,
        session_id: str,
        timeline_id: str
    ):
        self.combat_id = combat_id
        self.rng = random.Random(seed)
        self.player = player
        self.enemies = enemies
        self.event_store = event_store
        
        # Initialize systems
        self.damage_calc = DamageCalculator(seed)
        self.event_builder = CombatEventBuilder(session_id, timeline_id, combat_id)
        self.logger = CombatLogger()
        
        # Initialize enemy AI
        self.enemy_ais = {
            enemy.id: create_enemy_ai(enemy, enemy.archetype, self.rng)
            for enemy in enemies
        }
        
        # Combat state
        self.turn_order = []
        self.current_turn_index = 0
        self.round_number = 1
        self.is_over = False
        self.outcome = None
        
        # Emit start event
        self._emit_combat_started(seed)
    
    def execute_turn(self) -> None:
        """Execute one turn (player or enemy)."""
        current_combatant = self._get_current_combatant()
        
        # Emit turn start
        self._emit_turn_started(current_combatant)
        
        # Get action (player input or AI decision)
        if isinstance(current_combatant, Player):
            action = self._get_player_action()
        else:
            ai = self.enemy_ais[current_combatant.id]
            action = ai.select_action(self)
        
        # Execute action
        result = self._execute_action(action)
        
        # Emit action event
        self._emit_action_executed(action, result)
        
        # Check combat end conditions
        self._check_combat_end()
        
        # Advance turn
        self._advance_turn()
    
    def _execute_action(self, action: CombatAction) -> ActionResult:
        """Execute combat action and return result."""
        if action.action_type == "attack":
            # Calculate damage
            damage_result = self.damage_calc.calculate(
                attacker_atk=action.actor.attack,
                defender_def=action.target.defense,
                skill_power=action.skill_power,
                boost_points=action.boost_spent,
                damage_type=action.damage_type,
                defender_weaknesses=action.target.weaknesses,
                defender_is_broken=action.target.is_broken
            )
            
            # Apply damage
            action.target.take_damage(damage_result.damage, action.damage_type)
            
            return ActionResult(damage_result=damage_result, ...)
        
        # ... handle other action types
```

**Related Decisions**: DEC-2001, DEC-2006, DEC-2007, DEC-2008

---

### Step 6: Integration Testing and Validation
**Supervisors**: `@architect-supervisor`  
**Branch**: `phase/2-combat-system`  
**Estimated Time**: 3-4 hours

**Description**:
Comprehensive integration testing, performance benchmarking, and constitution compliance validation. Complete retrospective and documentation.

**Tasks**:
- [ ] Run full test suite: `make test`
- [ ] Verify >= 80% code coverage
- [ ] Run performance benchmarks
- [ ] Test all critical combat scenarios (10 scenarios from research)
- [ ] Validate event replay for determinism
- [ ] Constitution compliance check
- [ ] Update README and documentation
- [ ] Complete retrospective

**Success Criteria**:
- [ ] All 10 critical test scenarios pass
- [ ] Code coverage >= 80% overall
- [ ] Performance benchmarks met:
  - Damage calc < 0.01ms
  - AI decision < 0.1ms
  - Full combat < 100ms
- [ ] Event replay produces identical outcomes
- [ ] Constitution: 0 deviations
- [ ] No linting errors
- [ ] Documentation updated

**Critical Test Scenarios** (from Research Topic 6):
1. Player Victory: 1v1 combat, player wins
2. Player Defeat: Combat where player HP reaches 0
3. Shield Break: Trigger break system with weakness
4. Boost System: Spend BP for 1.5x/2.0x/2.5x multipliers
5. Critical Hit: Validate 1.5x damage multiplier
6. Type Effectiveness: 2.0x super effective damage
7. Multi-Enemy: 1v3 combat with turn order
8. Flee Success: Player escapes combat
9. Event Replay: Reconstruct combat from events
10. AI Determinism: Same seed = same AI decisions

**Files to Create**:
- `tests/integration/test_combat_scenarios.py` - Critical scenarios (~500 lines)
- `tests/benchmarks/bench_combat.py` - Performance tests (~150 lines)
- `RETROSPECTIVE.md` - Lessons learned

**Performance Benchmark Tests**:
```python
def bench_damage_calculation():
    """Benchmark: < 0.01ms per calc."""
    calc = DamageCalculator(seed=42)
    
    start = time.perf_counter()
    for _ in range(10000):
        calc.calculate(atk=50, def=30, skill_power=100)
    end = time.perf_counter()
    
    avg_time_ms = ((end - start) / 10000) * 1000
    assert avg_time_ms < 0.01, f"Too slow: {avg_time_ms:.4f}ms"

def bench_full_combat():
    """Benchmark: Full 10-turn combat < 100ms."""
    context = CombatContext(...)
    
    start = time.perf_counter()
    while not context.is_over:
        context.execute_turn()
    end = time.perf_counter()
    
    duration_ms = (end - start) * 1000
    assert duration_ms < 100, f"Too slow: {duration_ms:.2f}ms"
```

**Related Decisions**: All decisions

---

## Success Metrics

### Code Quality
- [ ] >= 80% test coverage (target: 90%+)
- [ ] 150+ tests passing (unit + integration)
- [ ] 0 linting errors (ruff + mypy)
- [ ] 100% type hint coverage
- [ ] Google-style docstrings on all public APIs

### Performance
- [ ] Damage calculation: < 0.01ms per calc
- [ ] AI decision: < 0.1ms per decision
- [ ] Full combat: < 100ms for 10-turn sequence
- [ ] 60 FPS maintained (combat logic < 16.67ms per frame)

### Functionality
- [ ] All 5 combat actions working (Attack, Defend, Item, Ability, Flee)
- [ ] Boost Points system functional
- [ ] Break System functional with stun
- [ ] 4 AI archetypes behaving distinctly
- [ ] 1v1, 1v2, 1v3 combat working
- [ ] Event replay produces identical outcomes
- [ ] Text-based output validates correctness

### Constitution Compliance
- [ ] Principle #1: Events append-only ✅
- [ ] Principle #2: Dependency injection ✅
- [ ] Principle #3: Type safety ✅
- [ ] Principle #4: Separation of concerns ✅
- [ ] Principle #5: >= 80% test coverage ✅
- [ ] Principle #6: Specific error handling ✅
- [ ] Principle #7: Google-style docstrings ✅
- [ ] Principle #11: Event immutability ✅
- [ ] Principle #12: Transaction safety ✅
- [ ] Principle #14: 60 FPS target ✅

**Target**: 0 deviations (same as Phase 1)

---

## Timeline Estimate

| Step | Description | Estimated Time |
|------|-------------|----------------|
| Step 1 | Combat Entities | 3-4 hours |
| Step 2 | Damage Calculation | 2-3 hours |
| Step 3 | Combat Events | 2-3 hours |
| Step 4 | Enemy AI | 3-4 hours |
| Step 5 | Combat Manager | 4-5 hours |
| Step 6 | Integration Testing | 3-4 hours |
| **Total** | | **17-23 hours** |

**Target Completion**: 3-4 days of focused work

---

## Risk Management

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Damage formula imbalance | 🟡 Medium | 🟡 High | Spreadsheet testing, easy to tune constants |
| AI too simple/predictable | 🟢 Low | 🟢 Medium | Acceptable for Phase 2, enhance in Phase 4 |
| Event replay bugs | 🟢 Low | 🔴 Critical | Comprehensive determinism tests, seeded RNG |
| Performance issues | 🟢 Low | 🟡 High | Benchmarks defined, simple calculations |
| Scope creep (status effects) | 🟡 Medium | 🟡 High | Stick to Phase 2 scope per DEC-2010 |

---

## Related Documents

- `research.md` - 6 research topics, 9 hours of research
- `decisions.md` - 10 architectural decisions (ADRs)
- `RESEARCH_SUMMARY.md` - Quick reference for key findings
- `README.md` - Phase tracking and status
- Phase 1 `PLAN.md` - Reference for patterns and structure

---

## Notes & Decisions

### Key Decisions Reference
- **DEC-2001**: Octopath-inspired mechanics (BP + Break)
- **DEC-2002**: Hybrid damage formula with multipliers
- **DEC-2003**: No database migration (extend Phase 1 schema)
- **DEC-2004**: Composite events (not atomic)
- **DEC-2005**: Weighted random AI (4 archetypes)
- **DEC-2006**: Deterministic RNG with seeding
- **DEC-2007**: Pure event sourcing (no read models)
- **DEC-2008**: Text-based output for Phase 2
- **DEC-2009**: Revised HP scaling (3x higher)
- **DEC-2010**: Defer advanced features to Phase 3+

### Deferred Features (Phase 3+)
- Active Time Battle (ATB) system
- Position-based combat
- Party member system
- Status effects (poison, burn, buffs/debuffs)
- Combo/dual-tech attacks
- Boss-specific AI patterns
- Enemy memory between turns

---

**Last Updated**: 2025-11-25  
**Status**: Ready for implementation  
**Next**: Create feature branch and begin Step 1

