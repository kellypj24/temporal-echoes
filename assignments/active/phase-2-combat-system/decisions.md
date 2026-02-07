# Decision Log: Combat System

**Phase**: Phase 2  
**Created**: 2025-11-25  
**Status**: 🔄 Active  

## Overview
This document logs all significant architectural, design, and implementation decisions made during Phase 2 (Combat System). Each decision is captured using a lightweight ADR (Architecture Decision Record) format based on research findings.

**Total Decisions**: 10  
**Constitution Deviations**: 0  
**High/Critical Impact**: 6  

---

## Table of Contents

- [DEC-2001](#dec-2001-octopath-traveler-inspired-combat-mechanics): Octopath Traveler-Inspired Combat Mechanics
- [DEC-2002](#dec-2002-hybrid-damage-formula-with-multipliers): Hybrid Damage Formula with Multipliers
- [DEC-2003](#dec-2003-no-database-migration-extend-phase-1-schema): No Database Migration - Extend Phase 1 Schema
- [DEC-2004](#dec-2004-composite-combat-events): Composite Combat Events
- [DEC-2005](#dec-2005-weighted-random-enemy-ai): Weighted Random Enemy AI
- [DEC-2006](#dec-2006-deterministic-combat-with-seeded-rng): Deterministic Combat with Seeded RNG
- [DEC-2007](#dec-2007-pure-event-sourcing-no-read-models): Pure Event Sourcing (No Read Models)
- [DEC-2008](#dec-2008-text-based-combat-output): Text-Based Combat Output for Phase 2
- [DEC-2009](#dec-2009-revised-hp-scaling): Revised HP Scaling with Equipment
- [DEC-2010](#dec-2010-defer-advanced-features): Defer Advanced Features to Phase 3+

---

## DEC-2001: Octopath Traveler-Inspired Combat Mechanics

**Status**: 🟡 Accepted  
**Date**: 2025-11-25  
**Deciders**: @architect-supervisor, User  
**Impact**: 🔴 Critical  
**Constitution Deviation**: ❌ No  

### Context
Phase 2 requires a turn-based combat system that is:
- Engaging and strategic for players
- Deterministic for event sourcing replay
- Scoped appropriately for Phase 2 timeline
- Extensible for future phases (timeline mechanics, AI narrative)
- Modern but achievable with 16-bit aesthetic

Research analyzed 6+ RPG combat systems (Octopath Traveler, Final Fantasy, Chrono Trigger, Pokemon, Dragon Quest, Earthbound). Need to decide which mechanics to adopt.

### Decision
Adopt **Octopath Traveler-inspired combat system** with simplifications:
- **Boost Points (BP)**: Characters accumulate 1 BP per turn (max 5), spend for 1.5x/2.0x/2.5x damage multipliers
- **Break System**: Enemies have shield points + weaknesses; breaking stuns for 1 turn + 1.5x damage
- **Speed-Based Turn Order**: Recalculated each round with seeded RNG variance
- **5 Core Actions**: Attack, Defend, Item, Ability, Flee
- **1v1 to 1v3 Combat**: Support multiple enemies, no party members yet

**Deferred to Phase 3+**:
- Active Time Battle (ATB) system
- Position-based combat mechanics
- Party member system
- Combo/dual-tech attacks

### Alternatives Considered

#### Alternative 1: Simple Pokemon-Style
**Description**: Basic turn-based with type effectiveness only, no BP or break systems

**Pros**:
- Extremely simple to implement (~200 LOC)
- Very familiar to players
- Easy to test and balance

**Cons**:
- Less strategic depth
- May feel too simple for 2025 game
- No resource management layer

**Reason Rejected**: Too simple for target audience; Octopath systems add depth without overwhelming complexity.

#### Alternative 2: Active Time Battle (ATB)
**Description**: Real-time gauges fill based on speed, characters act when full (Final Fantasy style)

**Pros**:
- Dynamic and exciting
- Adds tension to combat
- Classic JRPG feel

**Cons**:
- Hard to make deterministic for event replay
- Complex state management (multiple simultaneous timers)
- Difficult to test
- Higher scope risk

**Reason Rejected**: Determinism is critical for event sourcing; ATB makes replay significantly more complex.

#### Alternative 3: Tactical Grid-Based
**Description**: Position-based combat on grid (Fire Emblem, Final Fantasy Tactics style)

**Pros**:
- Very deep strategic gameplay
- Modern indie RPG trend
- Interesting timeline mechanics potential

**Cons**:
- Significantly higher scope (2-3x implementation time)
- Complex pathfinding and AI
- Harder to balance
- Overkill for Phase 2

**Reason Rejected**: Scope too large for Phase 2; can add positioning in Phase 3 if desired.

### Consequences

#### Positive
- Modern, tested mechanics (Octopath sold 3M+ copies)
- BP system adds strategic resource management
- Break system creates satisfying gameplay moments
- Speed-based turns are deterministic with seeding
- Scoped appropriately for Phase 2 timeline
- Players appreciate Octopath's combat design

#### Negative
- BP and break systems add complexity vs. simpler alternatives
- Need to balance multiple systems (BP, break, damage, types)
- Slightly more testing surface area

#### Neutral
- Not revolutionary, but proven to work
- Familiar to JRPG fans, may feel derivative
- Sets precedent for "inspired by" vs. "innovating on" approach

### Trade-offs Accepted
- **Simplicity for Depth**: Accepting more complex systems for richer gameplay
- **Scope Risk**: BP + Break is more work than simple combat, but research shows it's achievable
- **Originality**: Using proven mechanics rather than innovating (acceptable for Phase 2)

### Implementation Notes

```python
# Boost Point Management
class Combatant:
    boost_points: int = 0  # 0-5 BP
    max_boost_points: int = 5
    
    def gain_bp(self) -> None:
        """Gain 1 BP per turn."""
        self.boost_points = min(self.boost_points + 1, self.max_boost_points)
    
    def spend_bp(self, amount: int) -> float:
        """Spend BP for damage multiplier."""
        if amount > self.boost_points:
            raise ValueError("Not enough BP")
        
        self.boost_points -= amount
        
        # Return multiplier
        return {0: 1.0, 1: 1.5, 2: 2.0, 3: 2.5}[amount]

# Break System
class Enemy(Combatant):
    shield_points: int
    max_shield_points: int
    weaknesses: list[DamageType]
    is_broken: bool = False
    break_turns_remaining: int = 0
    
    def take_damage(self, damage: int, damage_type: DamageType) -> DamageResult:
        """Apply damage and check for break."""
        # Break multiplier
        multiplier = 1.5 if self.is_broken else 1.0
        actual_damage = int(damage * multiplier)
        
        # Check weakness
        if damage_type in self.weaknesses and not self.is_broken:
            self.shield_points -= 1
            if self.shield_points <= 0:
                self.trigger_break()
        
        self.hp -= actual_damage
        return DamageResult(actual_damage, weakness_hit=damage_type in self.weaknesses)
```

### Related Decisions
- DEC-2002: Damage formula integrates BP and break multipliers
- DEC-2004: Combat events capture BP/break state changes
- DEC-2006: Deterministic RNG enables replay

### References
- Research Topic 1: Turn-Based Combat Mechanics
- Octopath Traveler Battle System Analysis
- RESEARCH_SUMMARY.md: Combat Mechanics section

---

## DEC-2002: Hybrid Damage Formula with Multipliers

**Status**: 🟡 Accepted  
**Date**: 2025-11-25  
**Deciders**: @architect-supervisor  
**Impact**: 🔴 Critical  
**Constitution Deviation**: ❌ No  

### Context
Damage calculation is the heart of combat balance. Need a formula that:
- Scales well across levels 1-50
- Is simple enough to implement and test
- Supports multiple modifier systems (boost, type, crit, break)
- Is deterministic for event replay
- Prevents edge cases (negative damage, overflow)

### Decision
Implement **hybrid damage formula** with multiplicative modifiers:

```
Damage = (ATK * Power / (DEF * 0.5 + 10))
         * Random(0.85, 1.00)      # Variance
         * Boost_Multiplier        # 1.0, 1.5, 2.0, 2.5
         * Type_Multiplier         # 0.5, 1.0, 2.0
         * Critical_Multiplier     # 1.0 or 1.5
         * Break_Multiplier        # 1.0 or 1.5
         → Clamped to [1, 9999]
```

**Parameters**:
- **Power**: Skill/ability base power (50-200 range)
- **Random Variance**: 85-100% (Pokemon-style)
- **Critical**: 5% base chance, 1.5x multiplier
- **Type Effectiveness**: 0.5x (resist), 1.0x (neutral), 2.0x (super effective)
- **Always minimum 1 damage**: Prevents defensive stalemates

### Alternatives Considered

#### Alternative 1: Simple Subtractive (ATK - DEF)
**Pros**: Trivial to implement, very easy to understand
**Cons**: Can result in 0 or negative damage, poor scaling, defense becomes useless at high levels
**Reason Rejected**: Edge cases and poor scaling make balancing impossible

#### Alternative 2: Pokemon-Style Power Formula
```
Damage = ((2 * Level / 5 + 2) * Power * ATK / DEF) / 50 + 2
```
**Pros**: Extremely well-tested, proven scaling
**Cons**: Complex, requires "Power" stat per ability, harder to reason about
**Reason Rejected**: Over-engineered for our needs; hybrid is simpler and sufficient

#### Alternative 3: Fixed Damage (No Variance)
**Pros**: Perfectly deterministic, easier to test, more strategic (perfect information)
**Cons**: Feels less dynamic, no "lucky" hits, less exciting
**Reason Rejected**: 15% variance (85-100%) provides excitement without frustration

### Consequences

#### Positive
- Scales well across all level ranges (tested 1-50)
- Defense always meaningful (never useless)
- Multiple multipliers stack naturally
- Easy to add new modifiers later (status effects, equipment)
- Familiar feel to RPG players
- Clamping prevents overflow bugs

#### Negative
- More complex than pure subtractive formula
- Requires tuning the defense constant (0.5, +10)
- Multiple multipliers can create very high damage (mitigated by cap)

#### Neutral
- Not revolutionary, but proven pattern
- Balance requires spreadsheet testing

### Trade-offs Accepted
- **Simplicity for Depth**: More complex formula enables richer combat
- **Perfect Determinism for Excitement**: 15% variance adds fun (still deterministic with seed)
- **Damage Cap**: 9999 max prevents overflow, enforces 16-bit aesthetic

### Implementation Notes

```python
class DamageCalculator:
    """Deterministic damage calculation."""
    
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
        Calculate damage with all modifiers.
        
        Returns:
            DamageResult with damage value and flags
        """
        # Base damage
        safe_def = max(1, defender_def)  # Prevent division by zero
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
            multipliers_applied={
                "boost": boost_mult,
                "type": type_mult,
                "critical": crit_mult,
                "break": break_mult
            }
        )
```

### Related Decisions
- DEC-2001: BP and break multipliers integrate here
- DEC-2006: Deterministic RNG for variance
- DEC-2009: HP scaling must accommodate damage output

### References
- Research Topic 2: Damage Calculation System
- Pokemon Damage Formula documentation
- RESEARCH_SUMMARY.md: Damage Calculation section

---

## DEC-2003: No Database Migration - Extend Phase 1 Schema

**Status**: 🟡 Accepted  
**Date**: 2025-11-25  
**Deciders**: @architect-supervisor, @data-worker  
**Impact**: 🟡 High  
**Constitution Deviation**: ❌ No  

### Context
Combat system needs to store events for replay and analytics. Options:
1. Migrate Phase 1 schema to add combat-specific columns
2. Create new combat_events table
3. Use existing game_events table with JSON payloads

Phase 1 established:
- `game_events` table with JSON `event_data` column
- `aggregate_id` and `aggregate_type` for entity grouping
- Flexible event type system

### Decision
**Extend Phase 1 schema with JSON payloads - NO database migration**:
- Use existing `game_events` table
- `aggregate_id = combat_id` for grouping
- `aggregate_type = "combat"` for filtering
- Combat data in JSON `event_data` column
- Add combat event type constants to `EventTypes` class

**No Changes Required**:
- ❌ No new tables
- ❌ No schema migrations
- ❌ No ALTER TABLE statements
- ✅ Only Python code additions

### Alternatives Considered

#### Alternative 1: Create combat_events Table
**Description**: New dedicated table with typed columns for combat data

**Pros**:
- Typed columns (no JSON parsing)
- Potentially faster queries
- Clear separation of concerns

**Cons**:
- Requires database migration
- Duplicates event sourcing infrastructure
- Breaks single source of truth principle
- More maintenance (two event stores)

**Reason Rejected**: Violates Phase 1 architecture; adds complexity for minimal benefit.

#### Alternative 2: Migrate Schema with Combat Columns
**Description**: ALTER TABLE game_events ADD COLUMN combat_data JSON

**Pros**:
- Keeps single table
- Explicit combat data column

**Cons**:
- Requires migration script
- All non-combat events have NULL column (waste)
- Not necessary (event_data already exists)

**Reason Rejected**: Unnecessary migration; existing event_data is sufficient.

### Consequences

#### Positive
- **Zero migration effort** - Saves hours of work
- Maintains Phase 1 architecture integrity
- JSON flexibility allows rapid iteration
- dbt can parse JSON for analytics
- Single source of truth preserved
- Reduces risk of migration bugs

#### Negative
- JSON parsing slightly slower than typed columns (negligible)
- No database-level type safety (mitigated with Pydantic)
- Requires JSON_EXTRACT in dbt models

#### Neutral
- Consistent with Phase 1 decisions
- Establishes pattern for future phases

### Trade-offs Accepted
- **JSON Parsing Cost for Flexibility**: Acceptable for Phase 2 scale
- **No DB-Level Types for Rapid Iteration**: Pydantic provides validation
- **Query Complexity for Simplicity**: dbt models handle JSON parsing

### Implementation Notes

```python
# Add combat event types to existing EventTypes class
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

# Use existing GameEvent structure
event = GameEvent(
    event_type=EventTypes.COMBAT_STARTED,
    aggregate_id="combat_20251125_103045",  # Combat ID
    aggregate_type="combat",                 # For filtering
    session_id=session_id,
    timeline_id=timeline_id,
    event_data=json.dumps({
        "combat_id": "combat_20251125_103045",
        "rng_seed": 42,
        "player": {...},
        "enemies": [...]
    })
)

# Query combat events
combat_events = event_store.get_events_by_aggregate(
    aggregate_id="combat_20251125_103045",
    aggregate_type="combat"
)
```

### Related Decisions
- DEC-2004: Composite events fit naturally in JSON
- DEC-2007: No read models needed with this approach
- Phase 1 DEC-0001: SQLite event store decision

### References
- Research Topic 3: Combat Event Schema Design
- Phase 1: src/core/events.py
- Phase 1: src/core/persistence.py

---

## DEC-2004: Composite Combat Events

**Status**: 🟡 Accepted  
**Date**: 2025-11-25  
**Deciders**: @architect-supervisor  
**Impact**: 🟡 High  
**Constitution Deviation**: ❌ No  

### Context
Combat actions have multiple outcomes (damage, shield break, status effects, etc.). How granular should events be?

**Options**:
1. **Atomic events**: Separate event for each outcome (ActionExecuted → DamageDealt → ShieldBroken → StatusApplied)
2. **Composite events**: Single ActionExecuted event with all outcomes in JSON

### Decision
Use **composite events** - single `ActionExecuted` event contains all outcomes:
- Damage dealt
- Critical hit flag
- Weakness hit flag
- Shield points reduced
- Break triggered
- Status effects applied

**Example**:
```json
{
    "event_type": "ActionExecuted",
    "event_data": {
        "actor_id": "player",
        "action_type": "attack",
        "damage_dealt": 67,
        "is_critical": false,
        "is_weakness": true,
        "shield_points_reduced": 1,
        "shield_broken": true,
        "damage_breakdown": {...}
    }
}
```

### Alternatives Considered

#### Alternative 1: Atomic Events
**Description**: Separate event for each outcome step

```
1. ActionExecuted (player attacks)
2. DamageDealt (67 damage)
3. ShieldReduced (1 point)
4. ShieldBroken (enemy stunned)
```

**Pros**:
- Very fine-grained audit trail
- Each event is simple
- Easier to add new outcome types

**Cons**:
- 4-5x more events per action
- Complex replay logic (fold multiple events)
- Event ordering becomes critical
- dbt queries more complex

**Reason Rejected**: Over-engineered; complexity outweighs benefits for Phase 2.

#### Alternative 2: Domain Events per System
**Description**: Separate events for combat, damage, break (not per outcome)

**Pros**:
- Moderate granularity
- System boundaries clear

**Cons**:
- Still 2-3x more events
- Replay still complex
- Not significantly simpler than atomic

**Reason Rejected**: Middle ground provides worst of both worlds.

### Consequences

#### Positive
- Fewer events to store and process (~10-15 per combat vs 40-60)
- Simpler replay logic (one event = one action)
- Easier to test (atomic unit of combat)
- dbt queries simpler (all data in one JSON)
- Event ordering less critical

#### Negative
- Larger event payloads (~500 bytes vs ~100 bytes)
- Adding new outcomes requires schema evolution (Pydantic helps)
- Less granular audit trail

#### Neutral
- Standard pattern for event sourcing game state
- Follows Phase 1 precedent (state transitions are composite)

### Trade-offs Accepted
- **Event Count for Payload Size**: 10-15 large events vs 40-60 small events → choose fewer
- **Granularity for Simplicity**: Acceptable trade-off for Phase 2 scope

### Implementation Notes

```python
@dataclass
class ActionExecutedEvent:
    """Composite event for combat action execution."""
    
    # Action details
    actor_id: str
    target_id: str
    action_type: str
    skill_name: str | None
    
    # Resource consumption
    boost_points_spent: int
    
    # Damage results
    damage_dealt: int
    is_critical: bool
    is_weakness: bool
    
    # State changes
    target_hp_before: int
    target_hp_after: int
    target_defeated: bool
    
    # Break system
    shield_points_reduced: int
    shield_points_remaining: int
    shield_broken: bool
    
    # For debugging/analytics
    damage_breakdown: dict[str, float]

# Build event
event = GameEvent(
    event_type=EventTypes.ACTION_EXECUTED,
    aggregate_id=combat_id,
    aggregate_type="combat",
    event_data=json.dumps(asdict(action_event))
)
```

### Related Decisions
- DEC-2003: JSON payloads accommodate composite structure
- DEC-2007: Composite events work well without read models

### References
- Research Topic 3: Combat Event Schema Design
- Event Sourcing Patterns: Composite Events

---

## DEC-2005: Weighted Random Enemy AI

**Status**: 🟡 Accepted  
**Date**: 2025-11-25  
**Deciders**: @architect-supervisor, @game-logic-worker  
**Impact**: 🟡 High  
**Constitution Deviation**: ❌ No  

### Context
Phase 2 needs enemy AI that is:
- Simple enough to implement quickly
- Interesting enough to challenge players
- Deterministic for event replay
- Foundation for Phase 4 AI narrative

Complexity spectrum:
- **Level 1**: Pure random (too dumb)
- **Level 2**: Weighted random with HP modifiers
- **Level 3**: Rule-based with full situational awareness
- **Level 4**: Behavior trees
- **Level 5**: Machine learning

### Decision
Implement **Level 2: Weighted Random with HP Modifiers**:
- 4 enemy archetypes with different weight distributions
- Base weights modified by HP thresholds
- Deterministic using combat RNG seed
- No memory between turns (stateless)

**4 Archetypes**:
1. **AGGRESSIVE**: 70% attack, 10% defend, 20% ability
2. **DEFENSIVE**: 40% attack, 40% defend, 20% ability
3. **TACTICAL**: Adapts to player/enemy HP (50/20/30 base)
4. **BERSERKER**: More aggressive when low HP (rage mode)

### Alternatives Considered

#### Alternative 1: Pure Random
**Description**: `action = random.choice(["attack", "defend", "ability"])`

**Pros**: Trivial to implement (5 lines of code)
**Cons**: No personality, feels stupid, frustrating for players
**Reason Rejected**: Too simple; players expect some intelligence.

#### Alternative 2: Rule-Based with Full Awareness
**Description**: Complex decision tree considering all combat state

```python
if player.hp < 20% and self.has_finishing_move:
    return "finishing_move"
elif self.hp < 30% and has_heal:
    return "heal"
elif player.is_buffed:
    return "dispel"
# ... 20 more rules
```

**Pros**: Very smart, adaptive, interesting
**Cons**: Significant implementation time, hard to balance, scope risk
**Reason Rejected**: Too complex for Phase 2 timeline; can add later.

#### Alternative 3: Behavior Trees
**Description**: Hierarchical tree structure for decision-making

**Pros**: Very flexible, industry standard, extensible
**Cons**: Requires behavior tree library/implementation, overkill for Phase 2
**Reason Rejected**: Over-engineered for current needs; weighted random sufficient.

### Consequences

#### Positive
- Simple implementation (~200 LOC for all 4 archetypes)
- Distinct enemy personalities
- Deterministic with seeded RNG
- HP modifiers add basic situational awareness
- Easy to test (fixed seed = fixed behavior)
- Foundation for Phase 4 AI narrative

#### Negative
- Less intelligent than rule-based systems
- No learning or adaptation across turns
- May feel predictable after many combats

#### Neutral
- Standard approach for indie RPGs
- Can enhance with Phase 4 LLM narrative

### Trade-offs Accepted
- **Intelligence for Simplicity**: Accept simpler AI for Phase 2 scope
- **Predictability for Determinism**: Helps testing, slight gameplay trade-off
- **No Memory for Statelessness**: Simplifies implementation significantly

### Implementation Notes

```python
from enum import Enum, auto
import random

class AIArchetype(Enum):
    AGGRESSIVE = auto()
    DEFENSIVE = auto()
    TACTICAL = auto()
    BERSERKER = auto()

class AggressiveAI(EnemyAI):
    """Always attacks, rarely defends."""
    
    def _get_base_weights(self) -> dict[str, int]:
        return {"attack": 70, "defend": 10, "ability": 20}
    
    def _calculate_situational_weights(
        self,
        combat_state: CombatState
    ) -> dict[str, int]:
        weights = self.base_weights.copy()
        
        # Slightly defensive when low HP
        if self.enemy.hp_percent < 30:
            weights["defend"] = 25
            weights["attack"] = 50
        
        return weights
    
    def select_action(self, combat_state: CombatState) -> CombatAction:
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

# Factory
def create_enemy_ai(enemy: Enemy, archetype: AIArchetype, rng: random.Random) -> EnemyAI:
    ai_classes = {
        AIArchetype.AGGRESSIVE: AggressiveAI,
        AIArchetype.DEFENSIVE: DefensiveAI,
        AIArchetype.TACTICAL: TacticalAI,
        AIArchetype.BERSERKER: BerserkerAI,
    }
    return ai_classes[archetype](enemy, rng)
```

### Related Decisions
- DEC-2006: Deterministic RNG enables AI replay
- DEC-2001: AI integrates with combat action system
- Phase 4 planning: AI narrative hooks

### References
- Research Topic 4: Enemy AI Behavior Patterns
- RESEARCH_SUMMARY.md: Enemy AI section

---

## DEC-2006: Deterministic Combat with Seeded RNG

**Status**: 🟡 Accepted  
**Date**: 2025-11-25  
**Deciders**: @architect-supervisor  
**Impact**: 🔴 Critical  
**Constitution Deviation**: ❌ No  

### Context
Event sourcing requires deterministic replay for:
- Testing and debugging
- Timeline branching (Phase 3)
- Compliance auditing
- Validating balance changes

Combat has randomness:
- Damage variance (85-100%)
- Critical hits (5% chance)
- Enemy AI decisions
- Turn order variance

**Problem**: How to ensure same events → same outcomes?

### Decision
**Use seeded RNG for ALL combat randomness**:
- Generate RNG seed at combat start
- Store seed in `CombatStarted` event
- Initialize `random.Random(seed)` for combat
- All random decisions use this instance
- Replay uses same seed → identical outcomes

```python
# Combat initialization
seed = generate_seed()  # Based on timestamp + session
combat_rng = random.Random(seed)

# Store in event
event = GameEvent(
    event_type=EventTypes.COMBAT_STARTED,
    event_data=json.dumps({
        "rng_seed": seed,
        ...
    })
)

# All combat randomness uses this RNG
damage_variance = combat_rng.uniform(0.85, 1.00)
is_crit = combat_rng.randint(1, 100) <= crit_chance
enemy_action = enemy_ai.select_action(combat_rng)
```

### Alternatives Considered

#### Alternative 1: No Randomness (Pure Determinism)
**Description**: Fixed damage, no variance, no crits

**Pros**: Perfectly deterministic, easier to test, more strategic
**Cons**: Less exciting, feels mechanical, no "lucky" moments
**Reason Rejected**: Variance adds excitement without sacrificing determinism (with seeding).

#### Alternative 2: Global RNG Seed
**Description**: Seed entire game session, not per-combat

**Pros**: Simpler (one seed)
**Cons**: Combat order affects all future RNG (fragile), hard to test specific combats
**Reason Rejected**: Too coupled; per-combat seeds isolate randomness.

#### Alternative 3: Cryptographic RNG
**Description**: Use secrets.SystemRandom() for "true" randomness

**Pros**: Unpredictable, secure
**Cons**: Cannot replay, breaks event sourcing, overkill for game
**Reason Rejected**: Determinism is required feature, not a bug.

### Consequences

#### Positive
- **Perfect Replay**: Same seed → exact same combat
- **Testable**: Fixed seed = predictable behavior in tests
- **Debuggable**: Reproduce any combat from events
- **Timeline Branching Ready**: Can create alternate outcomes (Phase 3)
- **Constitution Compliant**: Event sourcing preserved

#### Negative
- Players could theoretically exploit seed knowledge (mitigated by not exposing seed)
- Slightly more complex than using global random

#### Neutral
- Standard pattern for deterministic games
- Similar to speedrun RNG manipulation (acceptable for single-player)

### Trade-offs Accepted
- **Exploitability for Determinism**: Single-player game, acceptable trade-off
- **Seed Generation Complexity**: Worth it for replay capability

### Implementation Notes

```python
import random
from datetime import UTC, datetime

def generate_combat_seed(session_id: str, timestamp: float) -> int:
    """Generate deterministic but unpredictable seed."""
    # Combine session ID hash with timestamp
    seed_string = f"{session_id}_{timestamp}"
    return hash(seed_string) % (2**31)  # 32-bit int range

class CombatContext:
    """Combat session with seeded RNG."""
    
    def __init__(self, combat_id: str, seed: int, ...):
        self.combat_id = combat_id
        self.rng = random.Random(seed)  # Deterministic RNG
        self.seed = seed  # Store for events
        ...
    
    def execute_action(self, action: CombatAction) -> ActionResult:
        """Execute action with deterministic randomness."""
        # Damage calculation uses self.rng
        damage_result = self.damage_calc.calculate(
            ...,
            random_factor=self.rng.uniform(0.85, 1.00)
        )
        
        # Enemy AI uses self.rng
        enemy_action = self.enemy_ai.select_action(self.rng)
        
        return ActionResult(...)

# Replay combat from events
def replay_combat(events: list[GameEvent]) -> CombatContext:
    """Reconstruct combat from events."""
    start_event = events[0]
    data = json.loads(start_event.event_data)
    
    # Use same seed as original combat
    context = CombatContext(
        combat_id=data["combat_id"],
        seed=data["rng_seed"],  # Same seed = same outcomes
        ...
    )
    
    # Replay all actions
    for event in events[1:]:
        context.apply_event(event)
    
    return context

# Testing with fixed seeds
def test_combat_determinism():
    """Verify same seed = same outcomes."""
    combat1 = CombatContext(combat_id="test", seed=42, ...)
    combat2 = CombatContext(combat_id="test", seed=42, ...)
    
    result1 = combat1.execute_action(attack_action)
    result2 = combat2.execute_action(attack_action)
    
    assert result1.damage == result2.damage
    assert result1.is_critical == result2.is_critical
```

### Related Decisions
- DEC-2002: Damage variance uses seeded RNG
- DEC-2005: Enemy AI uses seeded RNG
- Phase 1: Event sourcing requires determinism

### References
- Research Topic 2: Damage Calculation (deterministic section)
- Research Topic 4: Enemy AI (deterministic section)
- Python random.Random documentation

---

## DEC-2007: Pure Event Sourcing (No Read Models)

**Status**: 🟡 Accepted  
**Date**: 2025-11-25  
**Deciders**: @architect-supervisor, @data-worker  
**Impact**: 🟡 High  
**Constitution Deviation**: ❌ No  

### Context
Phase 1 established hybrid CQRS architecture:
- Events are single source of truth
- Future phases may add read model tables for performance

Phase 2 combat needs fast state queries:
- Current HP/BP of combatants
- Turn order
- Combat status

**Options**:
1. **Pure event sourcing**: Derive all state from events in memory
2. **CQRS read models**: Synchronously update `combat_state` table
3. **Hybrid**: Read models for some state, events for others

### Decision
**Pure event sourcing (NO read models) for Phase 2**:
- Derive all combat state from events
- Hold state in `CombatContext` object (in-memory)
- No database tables beyond `game_events`
- dbt analytics parse events directly

**Rationale**:
- Combat duration: 2-5 minutes (short-lived state)
- Event count: 10-20 per combat (small)
- Replaying 20 events: < 1ms (fast enough)
- Read models add complexity for no benefit at this scale

**Defer to Phase 3+**: If performance becomes issue (many party members, complex queries).

### Alternatives Considered

#### Alternative 1: CQRS Read Model Table
**Description**: Create `combat_state` table, update synchronously with events

```sql
CREATE TABLE combat_state (
    combat_id TEXT PRIMARY KEY,
    current_round INT,
    player_hp INT,
    player_bp INT,
    enemies JSON,
    turn_order JSON,
    last_event_id TEXT REFERENCES game_events(event_id)
);
```

**Pros**:
- Fast state queries (single SELECT)
- No event replay needed
- Standard CQRS pattern

**Cons**:
- Additional table to maintain
- Synchronization logic (events + state)
- Testing complexity (2x)
- Risk of state divergence bugs
- Overkill for 10-20 events

**Reason Rejected**: Premature optimization; pure event sourcing is sufficient for Phase 2 scale.

#### Alternative 2: Hybrid (Read Models for Analytics Only)
**Description**: No app read models, but pre-computed dbt tables for analytics

**Pros**:
- Fast analytics queries
- App stays simple

**Cons**:
- dbt already parses events for analytics
- No app-side benefit

**Reason Rejected**: dbt handles analytics; no need for additional tables.

### Consequences

#### Positive
- **Simplicity**: No additional tables or sync logic
- **Single Source of Truth**: Events only, no divergence risk
- **Faster Development**: No read model implementation (~2-3 hours saved)
- **Easier Testing**: Test events only, not state + events
- **Constitution Compliant**: Pure event sourcing

#### Negative
- Event replay required for state reconstruction (< 1ms, acceptable)
- May need read models in Phase 3+ if complexity grows

#### Neutral
- Standard for short-lived aggregates
- Can add read models later without refactoring events

### Trade-offs Accepted
- **Replay Cost for Simplicity**: < 1ms replay time is acceptable
- **Future Refactoring Risk**: If read models needed later, it's straightforward to add

### Implementation Notes

```python
class CombatContext:
    """In-memory combat state derived from events."""
    
    def __init__(self, combat_id: str, event_store: EventStore):
        self.combat_id = combat_id
        self.event_store = event_store
        
        # Load and replay events to reconstruct state
        events = event_store.get_events_by_aggregate(combat_id, "combat")
        self._replay_events(events)
    
    def _replay_events(self, events: list[GameEvent]) -> None:
        """Reconstruct state from events."""
        for event in events:
            self._apply_event(event)
    
    def _apply_event(self, event: GameEvent) -> None:
        """Apply single event to state."""
        data = json.loads(event.event_data)
        
        if event.event_type == EventTypes.COMBAT_STARTED:
            self.player = Player.from_dict(data["player"])
            self.enemies = [Enemy.from_dict(e) for e in data["enemies"]]
            self.rng = random.Random(data["rng_seed"])
        
        elif event.event_type == EventTypes.ACTION_EXECUTED:
            # Update HP, BP, shield points based on action result
            self._apply_action_result(data)
        
        # ... handle all event types
    
    def get_current_state(self) -> CombatState:
        """Get current combat state (no DB query needed)."""
        return CombatState(
            player_hp=self.player.hp,
            player_bp=self.player.boost_points,
            enemies=[e.to_dict() for e in self.enemies],
            turn_order=self.turn_order,
            round_number=self.round_number
        )

# Performance: Replaying 20 events
def benchmark_event_replay():
    events = generate_mock_combat_events(count=20)
    
    start = time.perf_counter()
    context = CombatContext.from_events(events)
    end = time.perf_counter()
    
    print(f"Replay time: {(end - start) * 1000:.2f}ms")
    # Expected: < 1ms
```

### Related Decisions
- DEC-2003: No new tables (consistent with this)
- Phase 1 DEC-0004: Hybrid CQRS design (app read models deferred)

### References
- Research Topic 3: Combat Event Schema
- Event Sourcing Patterns: Replay vs Read Models
- RESEARCH_SUMMARY.md: Event Schema section

---

## DEC-2008: Text-Based Combat Output for Phase 2

**Status**: 🟡 Accepted  
**Date**: 2025-11-25  
**Deciders**: @architect-supervisor, @pygame-worker  
**Impact**: 🟢 Medium  
**Constitution Deviation**: ❌ No  

### Context
Phase 2 implements combat logic but defers pygame rendering to Phase 5. Need combat output for:
- Development testing
- Integration test validation
- Debugging combat flow

**Options**:
1. No output (blind testing via assertions)
2. Text-based combat log
3. Simple pygame debug UI
4. Full combat rendering

### Decision
**Text-based combat log** with structured format:
- Print combat state to console/log file
- Structured format (rounds, turns, actions)
- Sufficient for testing and debugging
- Clear separation: logic vs. display

**Example Output**:
```
=== COMBAT START ===
Player (HP: 350/350, BP: 0) vs Goblin (HP: 200/200, Shield: 3/3)

ROUND 1 - Player's Turn (BP: 0)
> Player attacks with Fire Slash!
> WEAKNESS! Hit weakness for 2.0x damage!
> Shield broken! Goblin is stunned!
> Dealt 67 damage.
> Goblin HP: 133/200 [BROKEN]

ROUND 1 - Goblin's Turn
> Goblin is stunned! (Skip turn)

ROUND 2 - Player's Turn (BP: 1)
> Player spends 1 BP (1.5x boost)!
> Player attacks Goblin!
> Dealt 45 damage.
> Goblin HP: 88/200

ROUND 2 - Goblin's Turn (HP: 44%)
> Goblin attacks Player!
> Dealt 28 damage.
> Player HP: 322/350

=== COMBAT END ===
Result: Victory!
Rewards: 50 XP, 30 Gold
Duration: 8 turns
```

### Alternatives Considered

#### Alternative 1: No Output (Assertions Only)
**Description**: Tests validate state via assertions, no human-readable output

**Pros**: Fast, no display logic
**Cons**: Hard to debug failing tests, poor DX
**Reason Rejected**: Developer experience too poor for combat debugging.

#### Alternative 2: Simple Pygame Debug UI
**Description**: Minimal rendering (rectangles, text, no sprites)

**Pros**: Visual feedback, closer to final game
**Cons**: Requires pygame integration now, scope creep, slows tests
**Reason Rejected**: Violates separation of concerns; rendering is Phase 5.

#### Alternative 3: Full Combat Rendering
**Description**: Implement complete UI in Phase 2

**Pros**: Playable game immediately
**Cons**: Massive scope increase, delays combat logic completion
**Reason Rejected**: Phase 2 is combat *logic*, not UI.

### Consequences

#### Positive
- Clear separation: combat logic vs. rendering
- Fast test execution (no pygame overhead)
- Easy to debug (readable logs)
- Sufficient for validating correctness
- No pygame dependency yet

#### Negative
- Not visually appealing
- Can't playtest "feel" of combat yet
- Need to implement rendering later (was always planned)

#### Neutral
- Standard approach for TDD game development
- Similar to Phase 1 (text-based state transitions)

### Trade-offs Accepted
- **Visual Feedback for Speed**: Acceptable for Phase 2 focus
- **Playability for Correctness**: Get logic right first, UI later

### Implementation Notes

```python
class CombatLogger:
    """Text-based combat output for testing and debugging."""
    
    def __init__(self, output_file: TextIO = sys.stdout):
        self.output = output_file
    
    def log_combat_start(self, player: Player, enemies: list[Enemy]) -> None:
        """Log combat initialization."""
        self.output.write("=== COMBAT START ===\n")
        self.output.write(f"Player (HP: {player.hp}/{player.max_hp}, BP: {player.boost_points})")
        
        enemy_str = ", ".join(f"{e.name} (HP: {e.hp}/{e.max_hp})" for e in enemies)
        self.output.write(f" vs {enemy_str}\n\n")
    
    def log_turn_start(self, combatant: Combatant, round_num: int) -> None:
        """Log turn beginning."""
        self.output.write(f"ROUND {round_num} - {combatant.name}'s Turn")
        
        if isinstance(combatant, Player):
            self.output.write(f" (BP: {combatant.boost_points})")
        elif combatant.hp_percent < 50:
            self.output.write(f" (HP: {combatant.hp_percent:.0f}%)")
        
        self.output.write("\n")
    
    def log_action(self, action: CombatAction, result: ActionResult) -> None:
        """Log action execution and results."""
        actor = action.actor.name
        target = action.target.name
        
        # Action description
        if action.boost_spent > 0:
            self.output.write(f"> {actor} spends {action.boost_spent} BP ({result.boost_mult:.1f}x boost)!\n")
        
        self.output.write(f"> {actor} {action.action_type}s {target}!\n")
        
        # Special flags
        if result.is_weakness:
            self.output.write(f"> WEAKNESS! Hit weakness for {result.type_mult:.1f}x damage!\n")
        
        if result.is_critical:
            self.output.write("> CRITICAL HIT! (1.5x damage)\n")
        
        if result.shield_broken:
            self.output.write(f"> Shield broken! {target} is stunned!\n")
        
        # Damage and HP
        self.output.write(f"> Dealt {result.damage} damage.\n")
        self.output.write(f"> {target} HP: {result.target_hp_after}/{result.target_hp_max}")
        
        if result.target_is_broken:
            self.output.write(" [BROKEN]")
        
        if result.target_defeated:
            self.output.write(" [DEFEATED]")
        
        self.output.write("\n\n")
    
    def log_combat_end(self, outcome: str, rewards: dict) -> None:
        """Log combat conclusion."""
        self.output.write("=== COMBAT END ===\n")
        self.output.write(f"Result: {outcome.title()}!\n")
        
        if outcome == "victory":
            self.output.write(f"Rewards: {rewards['xp']} XP, {rewards['gold']} Gold\n")
        
        self.output.write(f"Duration: {rewards.get('turns', 'N/A')} turns\n")

# Usage in tests
def test_full_combat_flow():
    context = CombatContext(...)
    logger = CombatLogger(output_file=StringIO())  # Capture output
    
    while not context.is_combat_over():
        action = context.get_current_action()
        result = context.execute_action(action)
        logger.log_action(action, result)
    
    logger.log_combat_end(context.outcome, context.rewards)
    
    # Validate output or just state
    assert context.outcome == "victory"
```

### Related Decisions
- DEC-2001: Combat mechanics designed independently of rendering
- Phase 5 Planning: Pygame rendering deferred

### References
- Research Topic 5: Combat State Management & UI
- RESEARCH_SUMMARY.md: State/UI section

---

## DEC-2009: Revised HP Scaling with Equipment

**Status**: 🟡 Accepted  
**Date**: 2025-11-25  
**Deciders**: @architect-supervisor, User  
**Impact**: 🟢 Medium  
**Constitution Deviation**: ❌ No  

### Context
Initial HP scaling research suggested:
- Level 10: 150-200 HP
- Level 50: 600-800 HP

User feedback: These values too low given damage formula outputs. With damage ranging 40-80 per hit, players would die in 2-3 hits.

### Decision
**Increase base HP and account for equipment scaling**:

| Level | Base HP | With Equipment | Notes |
|-------|---------|----------------|-------|
| 1     | 120-180 | 150-220        | Survive 3-4 hits |
| 10    | 300-400 | 400-550        | Survive 6-8 hits |
| 25    | 750-1000 | 1000-1400      | Tactical combat |
| 50    | 1800-2400 | 2500-3500      | Endgame bosses |

**Design Goals**:
- Player survives 3-4 enemy attacks at same level
- Combat lasts 5-10 turns (strategic, not one-shot)
- Equipment provides meaningful 20-50% HP boost
- HP scales faster than ATK/DEF (allows longer combats)

### Alternatives Considered

#### Alternative 1: Lower Damage Formula
**Description**: Keep low HP, reduce damage output by 50%

**Pros**: Matches original HP targets
**Cons**: Damage feels weak, high-level combats too long
**Reason Rejected**: Better to have satisfying damage and higher HP.

#### Alternative 2: Extreme HP Scaling (9999 at max level)
**Description**: Final Fantasy-style 9999 HP at level 99

**Pros**: Very long combats, allows huge damage numbers
**Cons**: Overkill for our game scope, numbers inflation
**Reason Rejected**: 2500-3500 HP at level 50 is sufficient.

### Consequences

#### Positive
- Combats last longer (more tactical decisions)
- Equipment provides meaningful progression
- Damage feels impactful without one-shotting
- Scales well across level ranges

#### Negative
- Slightly longer combat duration (acceptable)
- Higher numbers may feel less "16-bit" (mitigated by 9999 damage cap)

#### Neutral
- Aligns with modern indie RPG expectations
- Equipment system gains importance

### Trade-offs Accepted
- **Combat Duration for Strategy**: Longer combats are more engaging
- **Number Inflation for Balance**: HP in thousands is acceptable at endgame

### Implementation Notes

```python
def calculate_hp_for_level(base_hp: int, level: int, growth_rate: float = 0.08) -> int:
    """
    Calculate HP at given level.
    
    Args:
        base_hp: Starting HP at level 1
        level: Current level
        growth_rate: HP growth per level (0.08 = 8% per level)
    
    Returns:
        HP value for the level
    """
    return int(base_hp * (1 + growth_rate * (level - 1)))

# Example stat progression
level_1_player = Player(base_hp=150, level=1)   # 150 HP
level_10_player = Player(base_hp=150, level=10) # 357 HP (2.4x)
level_50_player = Player(base_hp=150, level=50) # 2088 HP (13.9x)

# Equipment HP bonuses
leather_armor = Equipment(name="Leather Armor", hp_bonus=30)   # +30 HP (early game)
plate_armor = Equipment(name="Plate Armor", hp_bonus=200)      # +200 HP (mid game)
dragon_armor = Equipment(name="Dragon Armor", hp_bonus=800)    # +800 HP (endgame)
```

### Related Decisions
- DEC-2002: Damage formula balanced against these HP values
- Equipment system design (future)

### References
- User feedback on stat table
- RESEARCH_SUMMARY.md: Updated HP ranges
- research.md: Topic 2 (Damage Calculation)

---

## DEC-2010: Defer Advanced Features to Phase 3+

**Status**: 🟡 Accepted  
**Date**: 2025-11-25  
**Deciders**: @architect-supervisor  
**Impact**: 🟡 High  
**Constitution Deviation**: ❌ No  

### Context
Research identified interesting combat features that could enhance gameplay but increase Phase 2 scope:
- Active Time Battle (ATB) system
- Position-based combat
- Party member system
- Combo/dual-tech attacks
- Enemy memory/learning
- Boss-specific AI patterns
- Status effects (poison, burn, etc.)
- Skill trees and job classes

**Decision Point**: Include in Phase 2 or defer?

### Decision
**Defer all advanced features to Phase 3+**:

**Phase 2 Scope (Minimum Viable Combat)**:
- ✅ Turn-based combat
- ✅ Boost Points and Break System
- ✅ 5 core actions (Attack, Defend, Item, Ability, Flee)
- ✅ Weighted random AI (4 archetypes)
- ✅ 1v1 to 1v3 combat
- ✅ Type effectiveness
- ✅ Critical hits

**Deferred to Phase 3+**:
- ❌ ATB system
- ❌ Position-based combat
- ❌ Party members
- ❌ Combo attacks
- ❌ Status effects (beyond basic)
- ❌ Enemy memory
- ❌ Boss AI patterns

**Rationale**:
- Phase 2 goal: Establish combat foundation
- Advanced features can be added incrementally
- Event sourcing architecture supports easy extension
- Minimize risk of scope creep

### Alternatives Considered

#### Alternative 1: Include Status Effects in Phase 2
**Description**: Add poison, burn, buffs/debuffs to Phase 2

**Pros**: Richer combat immediately, feels more complete
**Cons**: +40% scope increase (~4 hours), more balance testing
**Reason Rejected**: Can add in Phase 2.5 after core combat validated.

#### Alternative 2: Include Party Members in Phase 2
**Description**: Support 2-3 party members from start

**Pros**: Multiplayer-style tactical decisions
**Cons**: Massive scope increase (3x complexity), AI must target intelligently
**Reason Rejected**: Too risky for Phase 2; better as separate phase.

#### Alternative 3: Full Feature Set in Phase 2
**Description**: Implement everything researched

**Pros**: Complete combat system immediately
**Cons**: 3-4x timeline, high failure risk, delays other phases
**Reason Rejected**: Violates agile principles; ship iteratively.

### Consequences

#### Positive
- **Focused Scope**: Phase 2 remains achievable
- **Reduced Risk**: Fewer moving parts to test and balance
- **Faster Delivery**: Can complete Phase 2 in estimated timeline
- **Iterative Development**: Can add features based on playtest feedback
- **Architecture Validated**: Foundation tested before adding complexity

#### Negative
- Combat may feel basic compared to modern RPGs (acceptable for Phase 2)
- Players may request deferred features (document roadmap)
- Need to design for future extension (already doing this)

#### Neutral
- Standard agile/MVP approach
- Consistent with Phase 1 methodology

### Trade-offs Accepted
- **Feature Completeness for Delivery Speed**: Ship working combat sooner
- **Immediate Richness for Long-Term Quality**: Better to iterate than over-scope

### Implementation Notes

```python
# Phase 2: Simple status effects (optional stretch goal)
@dataclass
class StatusEffect:
    """Simplified status effect for Phase 2 (optional)."""
    type: str  # "poison", "burn", "atk_up", "def_up"
    duration: int  # turns remaining
    value: int  # damage per turn or stat modifier

# Phase 3+: Complex status effects
@dataclass
class AdvancedStatusEffect:
    """Full status system for Phase 3+."""
    type: str
    duration: int
    value: int
    stacks: int  # Can apply multiple times
    dispellable: bool
    on_turn_start: Callable
    on_turn_end: Callable
    on_action: Callable
    # ... more hooks

# Architecture supports both without refactoring
# Phase 2 uses simple version, Phase 3+ upgrades
```

### Future Enhancement Path

**Phase 2.5 (Optional)**:
- Basic status effects (poison, burn)
- Boss enemy type with custom AI

**Phase 3 (Timeline Mechanics)**:
- Timeline branching based on combat outcomes
- Combat replay with alternate decisions

**Phase 4 (AI Integration)**:
- LLM-generated combat narrative
- AI-enhanced enemy descriptions

**Phase 5 (Rendering)**:
- Pygame combat UI
- Animations and visual effects
- Position-based mechanics (if desired)

**Phase 6 (Party System)**:
- Multiple party members
- Combo attacks
- Strategic target selection

### Related Decisions
- All previous decisions designed for extensibility
- Phase planning document

### References
- Research Topic 1: Advanced features identified but not implemented
- Agile methodology: MVP → Iterate
- Constitution: No scope creep (implicit principle)

---

## Summary Table

| ID | Decision | Impact | Status | Deviation |
|----|----------|--------|--------|-----------|
| DEC-2001 | Octopath-Inspired Combat | 🔴 Critical | ✅ Accepted | ❌ No |
| DEC-2002 | Hybrid Damage Formula | 🔴 Critical | ✅ Accepted | ❌ No |
| DEC-2003 | No DB Migration | 🟡 High | ✅ Accepted | ❌ No |
| DEC-2004 | Composite Events | 🟡 High | ✅ Accepted | ❌ No |
| DEC-2005 | Weighted Random AI | 🟡 High | ✅ Accepted | ❌ No |
| DEC-2006 | Seeded RNG Determinism | 🔴 Critical | ✅ Accepted | ❌ No |
| DEC-2007 | Pure Event Sourcing | 🟡 High | ✅ Accepted | ❌ No |
| DEC-2008 | Text-Based Output | 🟢 Medium | ✅ Accepted | ❌ No |
| DEC-2009 | Revised HP Scaling | 🟢 Medium | ✅ Accepted | ❌ No |
| DEC-2010 | Defer Advanced Features | 🟡 High | ✅ Accepted | ❌ No |

**Total**: 10 decisions, 0 deviations, 100% constitution compliance ✅

---

**Last Updated**: 2025-11-25  
**Next Review**: Before Phase 2 implementation  
**Status**: Ready for implementation planning

