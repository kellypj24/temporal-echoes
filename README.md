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

```
temporal-echoes/
├── .cursor/rules/          # Cursor MDC agent rules
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
├── assignments/           # AI task planning
│   ├── active/           # Current work items
│   ├── completed/        # Finished work
│   └── templates/        # Reusable templates
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

## 🤖 Cursor MDC Agent Rules

This project includes comprehensive Cursor MDC agent rules for AI-assisted development:

### Supervisors (Always Apply)
- **`architect-supervisor.mdc`**: System design orchestration, assignment management
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

## 🗂️ Assignment Management

Track development phases using the assignment templates:

```bash
# Create a new phase
cp assignments/templates/PHASE_TEMPLATE.md assignments/active/phase-1-core-game-loop/PLAN.md

# Create step documentation
cp assignments/templates/STEP_TEMPLATE.md assignments/active/phase-1-core-game-loop/step-1.md

# Validate completed work
cp assignments/templates/VALIDATION_TEMPLATE.md assignments/active/phase-1-core-game-loop/VALIDATION.md
```

Supervisors will guide you through:
1. Breaking down phases into steps
2. Defining success criteria
3. Running validation checklists
4. Moving completed work to `assignments/completed/`

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

### Phase 1: Core Game Loop *(In Progress)*
- [ ] Base state machine
- [ ] Player movement system
- [ ] Event store implementation
- [ ] Basic rendering

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

1. Check existing issues or create a new one
2. Fork the repository
3. Create a feature branch
4. Follow the code quality standards (`make check`)
5. Submit a pull request

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

