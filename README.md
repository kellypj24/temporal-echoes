# Temporal Echoes

> A 16-bit tribute RPG with an AI Dungeon Master - A time-travel adventure powered by Python, Pygame, and local LLMs

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-1.8.0-blue.svg)](https://python-poetry.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎮 Overview

Temporal Echoes is a turn-based RPG inspired by classics like Chrono Trigger and Undertale, featuring:

- **Time-Travel Mechanics**: Branch timelines and experience permanent consequences
- **AI Dungeon Master**: Dynamic narratives powered by local LLMs (Llama 3.2 via Ollama)
- **Event Sourcing Architecture**: Immutable event log enables timeline branching
- **16-bit Aesthetic**: Pixel-perfect graphics and retro sound design
- **Hybrid Database**: SQLite for OLTP, dbt-DuckDB for OLAP analytics

## 🏗️ Architecture

### Core Governance
All development follows **15 immutable principles** defined in `.cursor/rules/CONSTITUTION.md`:
- Event sourcing integrity (append-only)
- Dependency injection patterns
- Type safety requirements
- Separation of concerns
- >= 80% test coverage
- Async/await for AI (non-blocking)
- 60 FPS performance target
- And 8 more...

### Project Structure
```
temporal-echoes/
├── .cursor/rules/          # Cursor MDC agent rules + CONSTITUTION
│   ├── CONSTITUTION.md    # ⭐ 15 immutable development principles
│   ├── architect-supervisor.mdc
│   ├── ai-integration-supervisor.mdc
│   ├── data-worker.mdc
│   ├── game-logic-worker.mdc
│   ├── ai-worker.mdc
│   ├── pygame-worker.mdc
│   ├── prompt-worker.mdc
│   └── architecture-worker.mdc
├── src/                    # Game engine
│   ├── core/              # State machines, event store
│   ├── analytics/         # dbt integration bridge
│   ├── states/            # Game state implementations
│   ├── ai/                # AI manager, prompts
│   ├── ui/                # Pygame rendering, UI
│   └── entities/          # GameObjects (Player, NPC, Item)
├── dbt/                   # Analytics layer
│   ├── models/
│   │   ├── staging/       # Raw event transformations
│   │   ├── intermediate/  # Business logic
│   │   └── analytics/     # Game-ready aggregations
│   ├── tests/
│   ├── macros/
│   └── dbt_project.yml
├── assignments/           # Spec-Driven Development workflow
│   ├── active/           # Current phases
│   │   └── phase-X/
│   │       ├── research.md      # Research findings
│   │       ├── decisions.md     # Architecture decisions (ADRs)
│   │       ├── PLAN.md         # Implementation plan
│   │       ├── prompts/        # Step execution prompts
│   │       └── README.md       # Phase tracking
│   ├── completed/        # Finished phases with retrospectives
│   └── templates/        # SDD templates
│       ├── RESEARCH_TEMPLATE.md
│       ├── DECISIONS_TEMPLATE.md
│       ├── PHASE_TEMPLATE.md
│       ├── STEP_TEMPLATE.md
│       └── VALIDATION_TEMPLATE.md
├── tests/                # Test suite
│   ├── unit/
│   └── integration/
├── data/                 # Databases
│   ├── events.db        # SQLite OLTP
│   └── analytics.duckdb # DuckDB OLAP
├── assets/              # Game assets
│   ├── sprites/
│   ├── audio/
│   └── maps/
├── docker/              # Container configuration
│   ├── Dockerfile.game
│   ├── Dockerfile.ollama
│   └── scripts/
├── Makefile            # Task automation
├── pyproject.toml      # Poetry configuration
└── docker-compose.yml  # Container orchestration
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+**
- **Poetry** (for dependency management)
- **Docker & Docker Compose** (for Ollama LLM)
- **Git**

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/kellypj24/temporal-echoes.git
   cd temporal-echoes
   ```

2. **Complete development setup** (installs dependencies, initializes DB, starts Docker)
   ```bash
   make dev-setup
   ```

   Or manually:
   ```bash
   # Install dependencies
   make install

   # Start Ollama container
   make docker-up

   # Initialize databases
   make init-db
   ```

3. **Pull LLM model** (Llama 3.2)
   ```bash
   docker exec temporal-echoes-ollama ollama pull llama3.2
   ```

4. **Run the game**
   ```bash
   make run
   ```

## 📋 Development Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make install` | Install dependencies with Poetry |
| `make test` | Run test suite with coverage |
| `make lint` | Run linting and type checking |
| `make format` | Format code with ruff |
| `make run` | Start the game |
| `make dbt-run` | Run dbt analytics models |
| `make docker-up` | Start Docker containers |
| `make docker-down` | Stop Docker containers |
| `make clean` | Clean up generated files |

### Testing

```bash
# Run all tests with coverage
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run specific test file
poetry run pytest tests/unit/test_state_machine.py -v
```

### Linting & Type Checking

```bash
# Run all linters
make lint

# Auto-fix linting issues
make lint-fix

# Format code
make format
```

### dbt Analytics

```bash
# Run all dbt models
make dbt-run

# Run dbt tests
make dbt-test

# Generate and serve documentation
make dbt-docs

# Full pipeline (run + test)
make dbt-full
```

## 🤖 Cursor MDC Agent Rules & Spec-Driven Development

This project uses a **Spec-Driven Development (SDD)** workflow with comprehensive Cursor MDC agent rules:

### Core Governance
- **`CONSTITUTION.md`**: 15 immutable development principles
  - Architecture, Code Quality, AI Integration, Database, Performance
  - Deviation protocol for justified violations
  - Constitution checkpoints at all milestones

### Supervisors (Always Apply)
- **`architect-supervisor.mdc`**: System design orchestration, **SDD workflow enforcement**
  - **Critical Rule**: NO implementation until research.md and decisions.md complete
  - Constitution compliance checkpoints
- **`ai-integration-supervisor.mdc`**: AI/LLM coordination, prompt engineering oversight

### Workers (Auto-attach to files)
- **`game-logic-worker.mdc`**: State machines, combat, player mechanics (`src/states/`, `src/core/`)
- **`ai-worker.mdc`**: Ollama API integration (`src/ai/`)
- **`data-worker.mdc`**: SQLite/dbt/DuckDB operations (`src/core/persistence.py`, `dbt/`)
- **`pygame-worker.mdc`**: Rendering, sprites, UI (`src/ui/`, `src/entities/`)
- **`prompt-worker.mdc`**: Prompt templates and management (`src/ai/prompts/`)

### Manual Invocation
- **`architecture-worker.mdc`**: Design pattern selection, refactoring guidance (`@architecture-worker`)

### Using MDC Rules

In Cursor, the appropriate workers will automatically attach based on the files you're editing. For architecture questions, manually invoke:

```
@architecture-worker Should we use ECS for entity management?
```

### Spec-Driven Development Workflow

Every development phase follows this 4-step process:

1. **🔍 Research** (`research.md`) - Investigate unknowns, validate tech stack
2. **📋 Decisions** (`decisions.md`) - Document architectural decisions (ADR format)
3. **🛠️ Implementation** (`PLAN.md`) - Execute with constitution compliance
4. **✅ Validation** - Verify success criteria and retrospective

## 🗂️ Assignment Management (Spec-Driven Development)

Development follows a research-first approach inspired by Spec-Kit:

### Phase Structure
```
assignments/active/phase-X/
├── research.md          # Research findings and tech validation
├── decisions.md         # Architecture Decision Records (ADRs)
├── PLAN.md             # Implementation plan
├── prompts/            # Detailed step execution prompts
└── README.md           # Phase tracking
```

### Creating a New Phase

```bash
# 1. Research Phase (REQUIRED FIRST)
cp assignments/templates/RESEARCH_TEMPLATE.md assignments/active/phase-X/research.md
# Complete all research topics, validate assumptions, get approval

# 2. Decision Phase (REQUIRED BEFORE CODING)
cp assignments/templates/DECISIONS_TEMPLATE.md assignments/active/phase-X/decisions.md
# Document all major decisions using ADR format

# 3. Implementation Phase (AFTER research & decisions approved)
cp assignments/templates/PHASE_TEMPLATE.md assignments/active/phase-X/PLAN.md
# Break down into steps, execute with constitution compliance

# 4. Validation Phase
cp assignments/templates/VALIDATION_TEMPLATE.md assignments/active/phase-X/VALIDATION.md
# Verify success criteria, complete retrospective
```

### Supervisors Guide You Through:
1. **Research**: Investigating unknowns, validating tech stack
2. **Decisions**: Documenting architectural choices with trade-offs
3. **Implementation**: Breaking down phases into steps with constitution checkpoints
4. **Validation**: Running checklists, retrospectives
5. **Completion**: Moving finished work to `assignments/completed/`

### Constitution Compliance
Read `.cursor/rules/CONSTITUTION.md` for the **15 immutable principles** that govern all development. Constitution checkpoints occur at:
- Before creating phase plan
- Before starting implementation  
- During each step execution
- Before code review
- Before merging to main

## 🎯 Core Game Mechanics

### Timeline System
- **Echo Stones**: Consumable items to create timeline branches
- **Temporal Shrines**: Save points and timeline anchors
- **Convergence Points**: Fixed events across all timelines
- **Divergence Tracking**: Analytics on timeline differences

### Combat System
- Turn-based combat with combo mechanics
- Critical hit system based on luck stat
- AI-generated narrative descriptions
- Event sourcing for combat replay

### AI Dungeon Master
- Dynamic narrative generation
- Contextual NPC dialogue
- Quest generation based on player history
- Learning from player feedback

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Language** | Python 3.13 | Latest stable Python |
| **Game Engine** | Pygame 2.6+ | 2D game rendering |
| **OLTP Database** | SQLite | Event sourcing, fast writes |
| **OLAP Database** | DuckDB | Analytics, aggregations |
| **Analytics** | dbt-duckdb | Data transformations |
| **AI/LLM** | Ollama + Llama 3.2 | Local AI Dungeon Master |
| **Package Manager** | Poetry | Dependency management |
| **Task Runner** | Makefile | Development workflows |
| **Containers** | Docker Compose | Service orchestration |
| **Linting** | Ruff | Fast Python linter |
| **Type Checking** | MyPy | Static type checking |
| **Testing** | Pytest | Test framework |

## 📊 Event Sourcing

All game state is derived from an immutable event log:

```python
@dataclass
class GameEvent:
    event_id: str
    event_timestamp: datetime
    session_id: str
    timeline_id: str
    event_type: str
    player_id: str
    state_before: dict
    player_action: str
    ai_response: Optional[str]
    outcome: dict
    metadata: Optional[dict]
```

### Benefits
- **Time Travel**: Replay events to any point
- **Timeline Branching**: Fork from any event
- **Debugging**: Complete audit trail
- **Analytics**: Rich data for insights

## 🔮 Roadmap

### Phase 1: Core Game Loop ✅ **COMPLETE** (2025-11-24)
**Status**: All objectives met, 161 tests passing, 100% constitution compliance

**Completed**:
- [x] Event sourcing with SQLite (35 tests, < 1ms writes)
- [x] State machine pattern (47 tests, 8 states, explicit transitions)
- [x] Game context system (42 tests, dependency injection)
- [x] Game loop with fixed timestep (15 integration tests, 59.80 Hz achieved)
- [x] Configuration system (22 tests, Pydantic Settings)
- [x] 161 total tests (100% pass rate, >80% coverage)
- [x] Full event sourcing architecture
- [x] Hybrid CQRS ready (app read models + dbt analytics)
- [x] Zero technical debt

**Metrics**:
- Time: 12.5 hours (under 14-20 hour estimate)
- Tests: 161 passing (139 unit + 22 integration)
- Coverage: 100% on core modules
- Constitution: 11/11 applicable principles (100%)
- Lines of Code: ~4,500 (src + tests)

### Phase 2: Combat System
- [ ] Turn-based combat engine
- [ ] Combo system
- [ ] AI-generated combat narratives
- [ ] Enemy AI

### Phase 3: Timeline Mechanics
- [ ] Timeline branching
- [ ] Echo Stone implementation
- [ ] Temporal Shrines
- [ ] Convergence point detection

### Phase 4: AI Integration
- [ ] Full AI Dungeon Master
- [ ] Dynamic quest generation
- [ ] Contextual NPC dialogue
- [ ] Player feedback learning

### Phase 5: Polish & Content
- [ ] 16-bit art assets
- [ ] Sound design
- [ ] Story content
- [ ] Balance tuning

## 🤝 Contributing

This is a personal learning project, but contributions are welcome! Please:

1. **Read the Constitution**: Review `.cursor/rules/CONSTITUTION.md` for development principles
2. Check existing issues or create a new one
3. Fork the repository
4. Create a feature branch following Git conventions: `type/phase-short-description`
5. Follow the **Spec-Driven Development workflow**:
   - Complete research.md if introducing new patterns
   - Document decisions in decisions.md
   - Ensure constitution compliance
6. Follow code quality standards:
   - Type hints on all functions
   - >= 80% test coverage
   - `make lint` passes
7. Submit a pull request with:
   - Constitution compliance verification
   - Decision records (if applicable)
   - Test coverage report

## 📝 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- **Chrono Trigger** - Timeline mechanics inspiration
- **Undertale** - Permanent consequences design
- **Disco Elysium** - Narrative depth goals
- **Ollama** - Local LLM infrastructure
- **dbt** - Analytics engineering patterns

## 📧 Contact

PJ Kelly - [@kellypj24](https://github.com/kellypj24)

Project Link: [https://github.com/kellypj24/temporal-echoes](https://github.com/kellypj24/temporal-echoes)

---

*Built with ❤️ using Cursor AI and Python*

