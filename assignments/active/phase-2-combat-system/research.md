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
**Status**: ✅ Complete  
**Priority**: 🔴 High  
**Assigned To**: AI Agent  
**Research Duration**: 2 hours

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
- [x] Octopath Traveler (modern 16-bit style RPG)
- [x] Final Fantasy IV, V, VI (ATB system)
- [x] Chrono Trigger (position-based combat)
- [x] Earthbound (rolling HP meter)
- [x] Pokémon series (simple turn-based)
- [x] Dragon Quest series (traditional turn-based)
- [x] Modern indie RPG combat design patterns

**Research Methodology**:
1. ✅ Analyzed combat systems from 6+ RPGs (classic + modern)
2. ✅ Evaluated complexity vs. implementation time trade-offs
3. ✅ Identified key mechanics patterns across games
4. ✅ Assessed determinism requirements for event sourcing
5. ✅ Evaluated integration with Phase 1 architecture

**Findings**:

**1. Action Economy Systems Analyzed**:

**Simple Single Action (Dragon Quest, Pokémon)**:
- One action per turn per character
- Pros: Simple to implement, easy to test, deterministic
- Cons: Less strategic depth, can feel limiting
- Best for: Quick implementation, accessible gameplay

**Boost Points System (Octopath Traveler)**:
- Characters accumulate 1 BP per turn (max 5 BP)
- BP can be spent to enhance actions (1-3 BP per boost)
- Effects: Multiple attacks, increased damage, extended buff duration
- Pros: Strategic resource management, rewards planning ahead
- Cons: More complex state tracking, requires balancing
- Best for: Deep strategic gameplay, replayability

**Active Time Battle (Final Fantasy IV-VI)**:
- Real-time gauge fills based on speed stat
- Character acts when gauge is full
- Pros: Dynamic, exciting, adds urgency
- Cons: Hard to make deterministic, complex for event replay
- Best for: Action-oriented gameplay (NOT for Phase 2)

**2. Turn Order Systems**:

**Speed-Based (Most JRPGs)**:
- Turn order calculated from Speed/Agility stat
- Recalculated each round
- Simple formula: `turn_order = sorted_by(speed + random(0-10))`
- Pros: Deterministic with seeded RNG, easy to implement
- Cons: High speed characters always go first

**Initiative-Based (D&D style)**:
- Roll initiative at combat start
- Order fixed for entire combat
- Pros: Very simple, completely deterministic
- Cons: Less dynamic, speed stat less important

**Hybrid (Recommended)**:
- Base turn order from speed stat
- Each action has a "speed cost" that affects next turn
- Fast actions → act sooner next turn
- Slow actions → act later next turn
- Pros: More strategic, rewards action choice
- Cons: More complex to implement

**3. Combat Actions Analysis**:

**Phase 2 Recommended Actions**:
- **Attack**: Basic physical attack (100% speed cost)
- **Defend**: Reduce incoming damage, gain gauge (50% speed cost)
- **Item**: Use consumable item (75% speed cost)
- **Ability**: Special skills/magic (varies: 100-150% speed cost)
- **Flee**: Attempt to escape combat (immediate)

**Phase 3+ Actions** (defer for scope):
- Combo attacks (multi-character)
- Position-based attacks (Chrono Trigger style)
- Job-specific abilities

**4. Multi-Enemy Combat**:

All researched games support 1vN combat:
- Display all enemies with identifiers (Enemy A, B, C)
- Player selects target for single-target actions
- Some actions can target all enemies (AOE)
- Turn order includes all combatants (player + enemies)

**Recommended for Phase 2**: 1v1 and 1v3 (max 3 enemies)

**5. Weakness/Break Systems**:

**Octopath Traveler's Break System** (highly recommended):
- Enemies have Shield Points (SP) and specific weaknesses
- Attacking weakness: deals normal damage + reduces SP by 1
- Attacking non-weakness: deals normal damage, no SP reduction
- When SP reaches 0: Enemy enters "Break" state
  - Stunned for 1 turn (loses next action)
  - Takes increased damage (1.5x multiplier)
  - SP resets after recovery

**Implementation Impact**:
- Adds strategic depth without complexity
- Encourages players to experiment with attack types
- Creates satisfying "break" moments
- Requires enemy to track: SP (current), SP (max), weaknesses list

**6. Combat State Flow**:

```
GameState.EXPLORING
  ↓ (enemy encounter)
GameState.COMBAT_START
  ↓ (initialize combat)
GameState.COMBAT_PLAYER_TURN
  ↓ (player selects action)
GameState.COMBAT_EXECUTING
  ↓ (resolve action, check victory/defeat)
GameState.COMBAT_ENEMY_TURN
  ↓ (enemy AI selects action)
GameState.COMBAT_EXECUTING
  ↓ (resolve action, check victory/defeat)
GameState.COMBAT_PLAYER_TURN (repeat)
  ↓ (combat end condition)
GameState.COMBAT_END
  ↓ (distribute rewards)
GameState.EXPLORING
```

**Integration with Phase 1 StateMachine**:
- Add COMBAT_START, COMBAT_PLAYER_TURN, COMBAT_ENEMY_TURN, COMBAT_EXECUTING, COMBAT_END
- Existing COMBAT state → remove or use as parent state
- All transitions emit events for replay

**Key Insights**:
1. **Boost Point System** (Octopath) offers best balance of depth vs. complexity for Phase 2
2. **Speed-based turn order** with seeded RNG is deterministic and engaging
3. **Break system** adds strategic depth without major complexity increase
4. **Defer ATB and position-based** mechanics to Phase 3+ (too complex for event sourcing)
5. **5 core actions** (Attack, Defend, Item, Ability, Flee) sufficient for Phase 2
6. **Multi-enemy combat** (1v3 max) is achievable with current architecture
7. **Combat substates** needed in StateMachine for proper event tracking

**Decision**:
**Adopt Octopath Traveler-inspired system with simplifications**:
- ✅ Boost Points (BP) accumulation (1 per turn, max 5)
- ✅ Enemy Break system with weaknesses
- ✅ Speed-based turn order (recalculated each round)
- ✅ 5 core combat actions
- ✅ Support 1v1 to 1v3 enemies
- ❌ NO ATB (defer to Phase 3+)
- ❌ NO position-based mechanics (defer to Phase 3+)
- ❌ NO party members (defer to Phase 3+)

**Rationale**:
- Octopath's systems are modern, tested, and loved by players
- BP system adds depth without overwhelming complexity
- Break system creates satisfying gameplay moments
- Speed-based turns are deterministic with seeded RNG
- Scope is achievable in Phase 2 timeline
- Architecture supports future expansion

**Implementation Guidance**:

**1. Extend StateMachine** (`state_machine.py`):
```python
class GameState(Enum):
    # ... existing states ...
    COMBAT_START = auto()
    COMBAT_PLAYER_TURN = auto()
    COMBAT_ENEMY_TURN = auto()
    COMBAT_EXECUTING = auto()
    COMBAT_END = auto()
```

**2. Create Combat Manager** (`src/core/combat.py`):
```python
@dataclass
class CombatState:
    combatants: list[Combatant]  # Player + enemies
    turn_order: list[str]  # Combatant IDs in order
    current_turn_index: int
    round_number: int
    
    def calculate_turn_order(self, rng: random.Random) -> list[str]:
        """Calculate turn order based on speed + random factor."""
        order = [(c.id, c.speed + rng.randint(0, 10)) 
                 for c in self.combatants if c.is_alive]
        return [id for id, _ in sorted(order, key=lambda x: x[1], reverse=True)]
```

**3. Create Combatant Base Class** (`src/entities/combatant.py`):
```python
@dataclass
class Combatant(ABC):
    id: str
    name: str
    hp: int
    max_hp: int
    speed: int
    boost_points: int = 0  # 0-5 BP
    
    @abstractmethod
    def select_action(self, combat_state: CombatState) -> CombatAction:
        """Select an action (implemented by Player/Enemy)."""
        pass
```

**4. Implement Enemy Break System** (`src/entities/enemy.py`):
```python
@dataclass
class Enemy(Combatant):
    shield_points: int
    max_shield_points: int
    weaknesses: list[DamageType]  # [FIRE, SWORD, etc.]
    is_broken: bool = False
    break_turns_remaining: int = 0
    
    def take_damage(self, damage: int, damage_type: DamageType) -> DamageResult:
        """Apply damage and check for break."""
        multiplier = 1.5 if self.is_broken else 1.0
        actual_damage = int(damage * multiplier)
        
        # Check weakness
        if damage_type in self.weaknesses:
            self.shield_points -= 1
            if self.shield_points <= 0:
                self.trigger_break()
        
        self.hp -= actual_damage
        return DamageResult(actual_damage, self.is_broken, self.hp <= 0)
```

**5. Event Schema for Combat**:
```python
# combat_started event
{
    "event_type": "combat_started",
    "player": {"id": "player", "hp": 100, "max_hp": 100, ...},
    "enemies": [{"id": "enemy_1", "type": "goblin", ...}],
    "rng_seed": 12345  # For deterministic replay
}

# turn_started event
{
    "event_type": "turn_started",
    "combatant_id": "player",
    "round": 1,
    "boost_points": 3
}

# action_executed event
{
    "event_type": "action_executed",
    "actor_id": "player",
    "action": "attack",
    "target_id": "enemy_1",
    "boost_spent": 2,
    "damage_dealt": 45,
    "enemy_broken": true
}
```

**Confidence Level**: 🟢 High

**References**:
- [Octopath Traveler Battle System Guide](https://www.gamerguides.com/octopath-traveler/guide/introduction/game-mechanics/battle-system)
- [Wikipedia: Octopath Traveler](https://en.wikipedia.org/wiki/Octopath_Traveler)
- [ATB System Analysis](https://en.wikipedia.org/wiki/Chrono_Trigger)
- Web research: Modern turn-based RPG design patterns
- Web research: Action economy in game design

---

### Topic 2: Damage Calculation System
**Status**: ✅ Complete  
**Priority**: 🔴 High  
**Assigned To**: AI Agent  
**Research Duration**: 1.5 hours

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
- [x] RPG damage formula patterns (D&D, Final Fantasy, Pokemon)
- [x] Game balance principles and design patterns
- [x] Octopath Traveler damage mechanics
- [x] Classic 16-bit RPG formula analysis
- [x] Deterministic random number generation

**Research Methodology**:
1. ✅ Analyzed common RPG damage formula patterns
2. ✅ Evaluated simplicity vs. depth trade-offs
3. ✅ Designed formula with boost point integration
4. ✅ Planned deterministic RNG with seeding
5. ✅ Identified edge cases to test

**Findings**:

**1. Common RPG Damage Formula Patterns**:

**Pattern A: Subtractive (Simple)**
```
Damage = ATK - DEF
```
- Pros: Extremely simple, easy to understand
- Cons: Can result in 0 or negative damage, poor scaling
- Used in: Early Dragon Quest games
- Not recommended for Phase 2

**Pattern B: Multiplicative with Defense Reduction**
```
Damage = ATK * (100 / (100 + DEF))
```
- Pros: Never negative, scales well, defense always meaningful
- Cons: More complex math, harder for players to calculate
- Used in: League of Legends, MOBAs
- Good for Phase 2

**Pattern C: Hybrid (Recommended)**
```
Base_Damage = (ATK * ATK) / (DEF + constant)
Actual_Damage = Base_Damage * Random(0.85, 1.00)
```
- Pros: Good scaling, easy to balance, familiar feel
- Cons: Requires tuning the constant
- Used in: Pokemon, Final Fantasy series
- **Best for Phase 2**

**Pattern D: Power Formula (Pokemon)**
```
Damage = ((2 * Level / 5 + 2) * Power * ATK / DEF) / 50 + 2
```
- Pros: Extremely well-balanced, tested formula
- Cons: Complex, requires "Power" stat per ability
- Used in: Pokemon (with move power values)
- Too complex for Phase 2

**2. Recommended Base Formula for Temporal Echoes**:

```python
def calculate_damage(
    attacker_atk: int,
    defender_def: int,
    skill_power: int = 100,  # Base power (50-200 range)
    random_factor: float,    # 0.85-1.00 from seeded RNG
    boost_multiplier: float = 1.0,  # From boost points
    weakness_multiplier: float = 1.0,  # From break system
    critical_multiplier: float = 1.0,  # 1.0 or 1.5
    break_multiplier: float = 1.0,  # 1.0 or 1.5 (if enemy broken)
) -> int:
    """
    Calculate damage with all modifiers.
    
    Formula breakdown:
    1. Base = (ATK * skill_power) / (DEF * 0.5 + 10)
    2. Apply random variance (85%-100%)
    3. Apply boost multiplier
    4. Apply weakness bonus
    5. Apply critical hit
    6. Apply break bonus
    7. Clamp to range [1, 9999]
    """
    # Base damage calculation
    base_damage = (attacker_atk * skill_power) / (defender_def * 0.5 + 10)
    
    # Apply random variance
    damage = base_damage * random_factor
    
    # Apply multipliers (order matters!)
    damage *= boost_multiplier
    damage *= weakness_multiplier
    damage *= critical_multiplier
    damage *= break_multiplier
    
    # Convert to integer and clamp
    final_damage = int(damage)
    return max(1, min(final_damage, 9999))  # Always deal at least 1 damage
```

**3. Boost Point Damage Multipliers**:

Based on Octopath Traveler's system:
- **0 BP spent**: 1.0x damage (base)
- **1 BP spent**: 1.5x damage (+50%)
- **2 BP spent**: 2.0x damage (+100%)
- **3 BP spent**: 2.5x damage (+150%)

Implementation:
```python
boost_multipliers = {
    0: 1.0,
    1: 1.5,
    2: 2.0,
    3: 2.5
}
```

**4. Critical Hit Mechanics**:

**Simple System (Recommended for Phase 2)**:
- Base critical chance: 5% (1 in 20)
- Can be modified by equipment/skills later
- Critical multiplier: 1.5x damage
- Calculation: `if random(0, 100) < crit_chance: apply 1.5x multiplier`

**Formula**:
```python
def check_critical(crit_chance: int, rng: random.Random) -> bool:
    """Check if attack is critical. Default crit_chance = 5."""
    return rng.randint(1, 100) <= crit_chance
```

**5. Elemental/Type Effectiveness**:

Based on Pokemon and Octopath Traveler patterns:
- **Super Effective** (hits weakness): 2.0x damage
- **Neutral**: 1.0x damage
- **Not Very Effective** (resistance): 0.5x damage
- **Immune**: 0.0x damage (no damage)

**Weakness System Integration**:
- Hitting weakness triggers shield point reduction (Topic 1)
- Damage multiplier applies separately
- Example: Fire attack on Ice enemy = 2.0x damage + reduce SP by 1

**6. Random Variance**:

**Recommended: 85%-100% variance** (Pokemon-style):
- Provides unpredictability without frustration
- Range: `random_uniform(0.85, 1.00)`
- With seeded RNG, completely deterministic for replay
- Allows for "lucky" hits without being swingy

**Alternative: Fixed damage** (no variance):
- Easier to test and balance
- More strategic (perfect information)
- Could feel less dynamic
- Consider for Phase 2 simplification

**7. Status Effect Damage Modifiers**:

**Buffs/Debuffs** (multiplicative):
- **ATK Up**: Attacker ATK * 1.5
- **ATK Down**: Attacker ATK * 0.67
- **DEF Up**: Defender DEF * 1.5
- **DEF Down**: Defender DEF * 0.67

**Damage Over Time** (fixed per turn):
- **Poison**: 5% of max HP per turn
- **Burn**: 3% of max HP + ATK down
- **Regen**: Heal 5% of max HP per turn

**8. Level Scaling**:

**Stat Growth Curves**:
```python
def calculate_stat(base_stat: int, level: int, growth_rate: float = 0.05) -> int:
    """
    Calculate stat at given level.
    
    Formula: stat = base_stat * (1 + growth_rate * level)
    
    Example:
    - Base ATK: 10
    - Growth: 0.05 (5% per level)
    - Level 1: 10 * (1 + 0.05*1) = 10.5 ≈ 11
    - Level 10: 10 * (1 + 0.05*10) = 15
    - Level 50: 10 * (1 + 0.05*50) = 35
    """
    return int(base_stat * (1 + growth_rate * (level - 1)))
```

**Stat Ranges by Level**:
| Level | ATK Range | DEF Range | HP Range (Base) | HP Range (w/ Equipment) |
|-------|-----------|-----------|-----------------|-------------------------|
| 1     | 8-12      | 5-8       | 120-180         | 150-220                 |
| 10    | 15-20     | 10-15     | 300-400         | 400-550                 |
| 25    | 30-40     | 20-30     | 750-1000        | 1000-1400               |
| 50    | 60-80     | 40-60     | 1800-2400       | 2500-3500               |

**Notes**: 
- **Base HP**: Character stats without equipment
- **Equipment HP**: Armor/accessories add +20-50% HP at endgame
- **Design Goal**: Player should survive 3-4 enemy attacks at same level
- **Damage Check**: Level 10 enemy (ATK 15) vs Level 10 player (DEF 12, HP 350)
  - Expected damage: ~45-60 per hit
  - Player survives 5-7 hits ✅
- **Scaling**: HP grows faster than ATK/DEF to allow for longer, more strategic combats

**9. Edge Cases to Handle**:

```python
# Edge Case 1: Defense is 0
def safe_defense(defense: int) -> int:
    """Ensure defense is never 0 to avoid division issues."""
    return max(1, defense)

# Edge Case 2: Damage overflow
MAX_DAMAGE = 9999
def clamp_damage(damage: int) -> int:
    """Clamp damage to valid range."""
    return max(1, min(damage, MAX_DAMAGE))

# Edge Case 3: Negative ATK/DEF (from debuffs)
def clamp_stat(stat: int, minimum: int = 1) -> int:
    """Ensure stats don't go below minimum."""
    return max(minimum, stat)
```

**10. Determinism for Event Replay**:

**Seeded RNG Approach**:
```python
class CombatRNG:
    """Deterministic RNG for combat replay."""
    
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.seed = seed
    
    def random_variance(self) -> float:
        """Generate variance factor (0.85-1.00)."""
        return self.rng.uniform(0.85, 1.00)
    
    def check_critical(self, crit_chance: int) -> bool:
        """Check for critical hit."""
        return self.rng.randint(1, 100) <= crit_chance
```

**Combat Event with Seed**:
```json
{
    "event_type": "combat_started",
    "rng_seed": 42,
    "timestamp": "2025-11-25T10:30:00Z",
    "player": {...},
    "enemies": [...]
}
```

**Replay Guarantee**:
- Same seed → Same RNG sequence → Same damage rolls
- All random events are deterministic
- Event log can perfectly replay combat

**Key Insights**:
1. **Hybrid formula** balances simplicity and depth better than pure subtractive/multiplicative
2. **85-100% variance** provides excitement without frustration
3. **1.5x critical multiplier** is industry standard and feels impactful
4. **Boost multipliers** (1.5x, 2.0x, 2.5x) from Octopath are well-tested
5. **Type effectiveness** (0.5x, 1.0x, 2.0x) creates strategic depth
6. **Seeded RNG** makes all randomness deterministic for replay
7. **Always deal minimum 1 damage** prevents defensive stalemates
8. **Cap at 9999 damage** prevents overflow and maintains 16-bit aesthetic
9. **Defense curve** ensures it's always valuable (never "useless")
10. **Status effects as multipliers** stack naturally with other modifiers

**Decision**:
**Implement hybrid damage formula with Octopath-inspired boost system**:

```python
Damage = (ATK * Power / (DEF * 0.5 + 10)) 
         * Random(0.85, 1.00)
         * Boost_Multiplier
         * Type_Multiplier
         * Critical_Multiplier
         * Break_Multiplier
         → Clamped to [1, 9999]
```

**Rationale**:
- Formula is simple enough to implement and test
- Scales well across levels 1-50
- Supports all planned systems (boost, break, types, crits)
- Completely deterministic with seeded RNG
- Familiar feel for RPG players
- Easy to balance with stat tuning

**Implementation Guidance**:

**1. Create Damage Calculator Module** (`src/core/damage.py`):
```python
from dataclasses import dataclass
from enum import Enum
import random

class DamageType(Enum):
    PHYSICAL = auto()
    FIRE = auto()
    ICE = auto()
    LIGHTNING = auto()
    HOLY = auto()
    DARK = auto()

@dataclass
class DamageResult:
    damage: int
    is_critical: bool
    is_weakness: bool
    is_break_bonus: bool
    multipliers_applied: dict[str, float]

class DamageCalculator:
    """Deterministic damage calculation for combat."""
    
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
        """Calculate damage with all modifiers (see formula above)."""
        # ... implementation from findings ...
```

**2. Integration with Combat System**:
```python
# In CombatManager
def execute_attack(
    self,
    attacker: Combatant,
    defender: Combatant,
    skill: Skill,
    boost_points: int
) -> CombatActionResult:
    """Execute attack and return result."""
    
    # Calculate damage
    result = self.damage_calc.calculate(
        attacker_atk=attacker.attack,
        defender_def=defender.defense,
        skill_power=skill.power,
        boost_points=boost_points,
        damage_type=skill.damage_type,
        defender_weaknesses=defender.weaknesses,
        defender_is_broken=defender.is_broken,
        crit_chance=attacker.crit_rate,
    )
    
    # Apply damage to defender
    defender.take_damage(result.damage, skill.damage_type)
    
    # Emit event for sourcing
    self.emit_event("action_executed", {
        "attacker_id": attacker.id,
        "defender_id": defender.id,
        "skill": skill.name,
        "boost_spent": boost_points,
        "damage": result.damage,
        "critical": result.is_critical,
        "weakness": result.is_weakness,
    })
    
    return CombatActionResult(damage=result.damage, ...)
```

**3. Testing Strategy**:
```python
# Test determinism
def test_damage_determinism():
    """Same inputs = same damage."""
    calc1 = DamageCalculator(seed=42)
    calc2 = DamageCalculator(seed=42)
    
    result1 = calc1.calculate(atk=50, def=30, ...)
    result2 = calc2.calculate(atk=50, def=30, ...)
    
    assert result1.damage == result2.damage
    assert result1.is_critical == result2.is_critical

# Test edge cases
def test_damage_edge_cases():
    """Test minimum damage, maximum damage, zero defense."""
    calc = DamageCalculator(seed=1)
    
    # Zero defense
    result = calc.calculate(atk=10, def=0, ...)
    assert result.damage >= 1
    
    # Massive defense
    result = calc.calculate(atk=10, def=9999, ...)
    assert result.damage >= 1  # Always deal at least 1
    
    # Overflow
    result = calc.calculate(atk=9999, def=1, ...)
    assert result.damage <= 9999  # Capped
```

**Confidence Level**: 🟢 High

**References**:
- Pokemon Damage Calculation: Community documented formulas
- Octopath Traveler Boost System: Player guides and mechanics analysis
- RPG Damage Formula Design: Game development best practices
- Deterministic RNG: Python random.Random documentation

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
**Status**: ✅ Complete  
**Priority**: 🔴 High  
**Assigned To**: AI Agent  
**Research Duration**: 2 hours

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
- [x] Classic RPG enemy AI patterns (Final Fantasy, Dragon Quest, Earthbound)
- [x] Game AI programming patterns (weighted random, state-based)
- [x] Deterministic AI decision systems
- [x] Enemy personality archetypes

**Research Methodology**:
1. ✅ Analyzed enemy AI from classic 16-bit RPGs
2. ✅ Designed weighted decision system with personality modifiers
3. ✅ Created 4 distinct enemy archetypes
4. ✅ Designed deterministic AI using combat RNG seed
5. ✅ Identified Phase 4 AI narrative integration points
6. ✅ Evaluated state/memory requirements

**Findings**:

**1. AI Complexity Levels**:

**Level 1: Pure Random** (too simple):
```python
action = random.choice(["attack", "defend", "ability"])
```
- Pros: Trivial to implement
- Cons: Unpredictable, no strategy, feels stupid

**Level 2: Weighted Random** (Recommended for Phase 2):
```python
weights = {"attack": 60, "defend": 20, "ability": 20}
action = random.choices(actions, weights=weights.values())[0]
```
- Pros: Simple, deterministic with seed, personality-driven
- Cons: No situational awareness

**Level 3: Rule-Based with Conditions** (Future enhancement):
```python
if self.hp < 30%:
    return "defend" or "heal"
elif player.hp < 20%:
    return "powerful_attack"
else:
    return weighted_choice()
```
- Pros: Smarter, responds to situation
- Cons: More complexity, harder to balance

**Decision for Phase 2**: **Weighted Random with HP-based modifiers**

**2. Enemy Personality Archetypes**:

**Archetype 1: AGGRESSIVE**
```python
class AggressiveAI(EnemyAI):
    """Always attacks, rarely defends."""
    
    base_weights = {
        "attack": 70,
        "defend": 10,
        "ability": 20,
    }
    
    def get_action(self, combat_state: CombatState) -> CombatAction:
        # Modify weights based on situation
        weights = self.base_weights.copy()
        
        # If low HP, slightly increase defense
        if self.hp_percent < 30:
            weights["defend"] = 25
            weights["attack"] = 50
        
        return self.weighted_choice(weights)
```

**Archetype 2: DEFENSIVE**
```python
class DefensiveAI(EnemyAI):
    """Defends often, attacks cautiously."""
    
    base_weights = {
        "attack": 40,
        "defend": 40,
        "ability": 20,
    }
    
    def get_action(self, combat_state: CombatState) -> CombatAction:
        weights = self.base_weights.copy()
        
        # Defend more when low HP
        if self.hp_percent < 50:
            weights["defend"] = 60
            weights["attack"] = 20
        
        return self.weighted_choice(weights)
```

**Archetype 3: TACTICAL**
```python
class TacticalAI(EnemyAI):
    """Adapts to player behavior, uses abilities strategically."""
    
    base_weights = {
        "attack": 50,
        "defend": 20,
        "ability": 30,
    }
    
    def get_action(self, combat_state: CombatState) -> CombatAction:
        weights = self.base_weights.copy()
        
        # Use ability when player HP is low (finish them off)
        if combat_state.player.hp_percent < 40:
            weights["ability"] = 50
            weights["attack"] = 30
        
        # Defend when own HP is low
        if self.hp_percent < 30:
            weights["defend"] = 50
        
        return self.weighted_choice(weights)
```

**Archetype 4: BERSERKER**
```python
class BerserkerAI(EnemyAI):
    """Attacks MORE when low HP (rage mode)."""
    
    base_weights = {
        "attack": 60,
        "defend": 20,
        "ability": 20,
    }
    
    def get_action(self, combat_state: CombatState) -> CombatAction:
        weights = self.base_weights.copy()
        
        # RAGE MODE: Attack more when low HP
        if self.hp_percent < 30:
            weights["attack"] = 80
            weights["defend"] = 5
            weights["ability"] = 15
        
        return self.weighted_choice(weights)
```

**3. Deterministic AI Decision System**:

**Implementation**:
```python
class EnemyAI:
    """Base class for enemy AI with deterministic decisions."""
    
    def __init__(self, enemy_id: str, archetype: str, rng_seed: int):
        self.enemy_id = enemy_id
        self.archetype = archetype
        self.rng = random.Random(rng_seed)  # Deterministic!
        self.base_weights = self._get_archetype_weights(archetype)
    
    def select_action(
        self,
        combat_state: CombatState,
        available_actions: list[str]
    ) -> CombatAction:
        """
        Select action deterministically based on archetype and situation.
        
        Returns:
            CombatAction with action_type and target
        """
        # Get weights for current situation
        weights = self._calculate_weights(combat_state)
        
        # Filter to available actions only
        available_weights = {
            action: weights[action]
            for action in available_actions
            if action in weights
        }
        
        # Weighted random choice (deterministic with seed)
        action_type = self.rng.choices(
            population=list(available_weights.keys()),
            weights=list(available_weights.values()),
            k=1
        )[0]
        
        # Select target (usually player, but could be self for defend)
        target_id = self._select_target(action_type, combat_state)
        
        return CombatAction(
            action_type=action_type,
            target_id=target_id,
            boost_points=0  # Enemies don't use BP in Phase 2
        )
    
    def _calculate_weights(
        self,
        combat_state: CombatState
    ) -> dict[str, int]:
        """Calculate situational weights (override in subclasses)."""
        return self.base_weights.copy()
    
    def _select_target(
        self,
        action_type: str,
        combat_state: CombatState
    ) -> str:
        """Select action target."""
        if action_type in ["defend", "heal"]:
            return self.enemy_id  # Target self
        else:
            return "player"  # Target player
```

**Determinism Guarantee**:
- Same combat RNG seed → Same AI decisions
- Perfect replay from events
- Testable with fixed seeds

**4. Difficulty Scaling**:

**Approach: Stat Multipliers + Smarter AI**

| Difficulty | HP Mult | ATK Mult | DEF Mult | AI Archetype | Notes |
|------------|---------|----------|----------|--------------|-------|
| Easy       | 0.8x    | 0.8x     | 0.8x     | Aggressive   | Simple, predictable |
| Normal     | 1.0x    | 1.0x     | 1.0x     | Mixed        | Balanced |
| Hard       | 1.3x    | 1.2x     | 1.2x     | Tactical     | Uses abilities more |
| Very Hard  | 1.6x    | 1.4x     | 1.4x     | Tactical     | Adaptive behavior |

**Boss Enemies**: Custom AI with unique patterns (Phase 2.5+)

**5. Event Store Integration**:

**AI Decision Event**:
```json
{
    "event_type": "ActionSelected",
    "aggregate_id": "combat_123",
    "aggregate_type": "combat",
    "event_data": {
        "actor_id": "enemy_1",
        "actor_type": "enemy",
        "ai_archetype": "aggressive",
        "hp_percent": 75,
        "available_actions": ["attack", "defend", "ability"],
        "weights": {"attack": 70, "defend": 10, "ability": 20},
        "selected_action": "attack",
        "selected_target": "player",
        "decision_seed_offset": 42  // For exact replay
    }
}
```

**Benefits**:
- Complete AI decision audit trail
- Can analyze AI behavior patterns with dbt
- Debug AI "mistakes" in testing
- Transparent for game balance

**6. Phase 4 AI Narrative Hooks**:

**Integration Points**:
```python
class EnemyAI:
    def select_action_with_narrative(
        self,
        combat_state: CombatState,
        ai_manager: AIManager  # Phase 4
    ) -> tuple[CombatAction, str]:
        """
        Select action and generate narrative.
        
        Phase 2: Returns (action, "")
        Phase 4: Returns (action, "The goblin snarls and lunges!")
        """
        action = self.select_action(combat_state)
        
        # Phase 4: Generate narrative asynchronously
        narrative = await ai_manager.generate_action_narrative(
            enemy=self,
            action=action,
            context=combat_state,
            fallback=lambda: f"{self.name} uses {action.action_type}!"
        )
        
        return (action, narrative)
```

**Narrative Context**:
- Enemy archetype (affects tone: aggressive → menacing)
- Current HP (low HP → desperate actions)
- Combat history (revenge for previous damage)
- Player state (finish them off vs. cautious)

**7. Enemy Memory / State**:

**Decision for Phase 2**: **NO memory** (stateless per turn)
- Simpler implementation
- Easier to test
- Still challenging with archetypes
- Memory can be added in Phase 3+

**Future Memory System** (Phase 3+):
```python
@dataclass
class EnemyMemory:
    """Track combat history for smarter AI."""
    turns_since_last_ability: int = 0
    turns_defending: int = 0
    player_weakness_discovered: DamageType | None = None
    times_hit_by_type: dict[DamageType, int] = field(default_factory=dict)
```

**Key Insights**:
1. **Weighted random** strikes best balance of simple + interesting
2. **4 archetypes** provide personality without over-complexity
3. **Deterministic with seed** enables perfect replay
4. **HP-based weight modifiers** add situational awareness
5. **Stat multipliers** for difficulty > complex AI behavior
6. **ActionSelected events** provide complete AI audit trail
7. **Phase 4 hooks** designed but not implemented yet
8. **No memory needed** for Phase 2 - archetypes sufficient
9. **Bosses need custom AI** - defer to Phase 2.5
10. **Testing is straightforward** - fixed seed = fixed behavior

**Decision**:
**Implement weighted random AI with 4 archetypes and HP-based modifiers**:
- ✅ **AGGRESSIVE**: 70% attack, 10% defend, 20% ability
- ✅ **DEFENSIVE**: 40% attack, 40% defend, 20% ability
- ✅ **TACTICAL**: Adapts to player/self HP
- ✅ **BERSERKER**: More aggressive when low HP (rage mode)
- ✅ **Deterministic**: Uses combat RNG seed
- ✅ **Situational**: Weights modified by HP thresholds
- ✅ **Event Integration**: ActionSelected events for audit
- ✅ **Phase 4 Ready**: Narrative hooks designed
- ❌ **NO memory/state** in Phase 2 (add later if needed)
- ❌ **NO boss AI** in Phase 2 (defer to Phase 2.5)

**Rationale**:
- Simple enough for Phase 2 timeline
- Interesting enough to challenge players
- Deterministic for event replay
- Extensible for Phase 4 narrative
- Testable with fixed seeds
- Personality variety without complexity
- HP thresholds add basic situational awareness

**Implementation Guidance**:

**1. Base AI Class** (`src/core/ai.py`):
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
import random

class AIArchetype(Enum):
    AGGRESSIVE = auto()
    DEFENSIVE = auto()
    TACTICAL = auto()
    BERSERKER = auto()

@dataclass
class CombatAction:
    action_type: str  # "attack", "defend", "ability"
    target_id: str
    skill_name: str | None = None
    boost_points: int = 0

class EnemyAI(ABC):
    """Base class for enemy AI decision-making."""
    
    def __init__(self, enemy: 'Enemy', rng: random.Random):
        self.enemy = enemy
        self.rng = rng
        self.base_weights = self._get_base_weights()
    
    @abstractmethod
    def _get_base_weights(self) -> dict[str, int]:
        """Return archetype-specific base weights."""
        pass
    
    def select_action(self, combat_state: 'CombatState') -> CombatAction:
        """Select action based on weights and situation."""
        weights = self._calculate_situational_weights(combat_state)
        
        action_type = self.rng.choices(
            population=list(weights.keys()),
            weights=list(weights.values()),
            k=1
        )[0]
        
        return CombatAction(
            action_type=action_type,
            target_id="player" if action_type == "attack" else self.enemy.id
        )
    
    def _calculate_situational_weights(
        self,
        combat_state: 'CombatState'
    ) -> dict[str, int]:
        """Modify weights based on situation (override in subclasses)."""
        return self.base_weights.copy()
```

**2. Archetype Implementations** (`src/core/ai.py`):
```python
class AggressiveAI(EnemyAI):
    """Always attacks, rarely defends."""
    
    def _get_base_weights(self) -> dict[str, int]:
        return {"attack": 70, "defend": 10, "ability": 20}
    
    def _calculate_situational_weights(
        self,
        combat_state: 'CombatState'
    ) -> dict[str, int]:
        weights = self.base_weights.copy()
        
        # Slightly more defensive when low HP
        if self.enemy.hp_percent < 30:
            weights["defend"] = 25
            weights["attack"] = 50
        
        return weights

class DefensiveAI(EnemyAI):
    """Cautious, defends often."""
    
    def _get_base_weights(self) -> dict[str, int]:
        return {"attack": 40, "defend": 40, "ability": 20}
    
    def _calculate_situational_weights(
        self,
        combat_state: 'CombatState'
    ) -> dict[str, int]:
        weights = self.base_weights.copy()
        
        # Even more defensive when low HP
        if self.enemy.hp_percent < 50:
            weights["defend"] = 60
            weights["attack"] = 20
        
        return weights

class TacticalAI(EnemyAI):
    """Adaptive, uses abilities strategically."""
    
    def _get_base_weights(self) -> dict[str, int]:
        return {"attack": 50, "defend": 20, "ability": 30}
    
    def _calculate_situational_weights(
        self,
        combat_state: 'CombatState'
    ) -> dict[str, int]:
        weights = self.base_weights.copy()
        
        # Finish off low HP player
        if combat_state.player.hp_percent < 40:
            weights["ability"] = 50
        
        # Defend when low HP
        if self.enemy.hp_percent < 30:
            weights["defend"] = 50
        
        return weights

class BerserkerAI(EnemyAI):
    """Attacks MORE when low HP (rage mode)."""
    
    def _get_base_weights(self) -> dict[str, int]:
        return {"attack": 60, "defend": 20, "ability": 20}
    
    def _calculate_situational_weights(
        self,
        combat_state: 'CombatState'
    ) -> dict[str, int]:
        weights = self.base_weights.copy()
        
        # RAGE MODE: More aggressive when low HP
        if self.enemy.hp_percent < 30:
            weights["attack"] = 80
            weights["defend"] = 5
            weights["ability"] = 15
        
        return weights
```

**3. AI Factory** (`src/entities/enemy.py`):
```python
def create_enemy_ai(enemy: Enemy, archetype: AIArchetype, rng: random.Random) -> EnemyAI:
    """Factory to create AI based on archetype."""
    ai_classes = {
        AIArchetype.AGGRESSIVE: AggressiveAI,
        AIArchetype.DEFENSIVE: DefensiveAI,
        AIArchetype.TACTICAL: TacticalAI,
        AIArchetype.BERSERKER: BerserkerAI,
    }
    
    ai_class = ai_classes[archetype]
    return ai_class(enemy, rng)
```

**4. Testing Strategy**:
```python
def test_ai_determinism():
    """Same seed = same decisions."""
    enemy = Enemy(id="enemy_1", ...)
    
    ai1 = AggressiveAI(enemy, random.Random(42))
    ai2 = AggressiveAI(enemy, random.Random(42))
    
    action1 = ai1.select_action(combat_state)
    action2 = ai2.select_action(combat_state)
    
    assert action1.action_type == action2.action_type

def test_archetype_behavior():
    """Aggressive AI attacks more than defensive."""
    aggressive = AggressiveAI(enemy, rng)
    defensive = DefensiveAI(enemy, rng)
    
    # Run 100 decisions
    agg_attacks = sum(1 for _ in range(100) 
                      if aggressive.select_action(...).action_type == "attack")
    def_attacks = sum(1 for _ in range(100) 
                      if defensive.select_action(...).action_type == "attack")
    
    assert agg_attacks > def_attacks
```

**Confidence Level**: 🟢 High

**References**:
- Classic RPG AI patterns: Dragon Quest, Final Fantasy
- Game AI Pro book chapters on decision-making
- Python random.choices() documentation for weighted selection
- Deterministic game AI articles

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

