# Temporal Echoes - Development Guidelines

## Project Overview
16-bit RPG with AI Dungeon Master capabilities. Event-sourced architecture with timeline branching.

**Developer Context**: Intermediate Python, advanced SQL/dbt, learning game dev & AI agents.

**Stack**: Python 3.13, Pygame, SQLite (OLTP), DuckDB (OLAP), dbt, Ollama (Llama 3.2), uv, just, Docker

## Current Status

| Phase | Name | Status |
|-------|------|--------|
| 1 | Core Game Loop | Done (161 tests, 100% coverage) |
| 2 | Combat System | Done (403 tests, 90.22% coverage) — pending final PR |
| 3 | Timeline Mechanics | Planned |
| 4 | AI Integration | Planned |
| 5 | Polish & Content | Planned |

**Active work**: `assignments/active/phase-2-combat-system/`
**Completed reference**: `assignments/completed/phase-1-core-game-loop/`

## Phase 4 Direction — LangGraph for AI-DM orchestration (decided 2026-06-13)

Phase 4 (AI Integration) will **evaluate LangGraph as the AI-DM orchestration
layer with the intent to adopt it**, scoping its infrastructure to our use case
rather than homebrewing agent orchestration from scratch. This decision should
**drive how much we build by hand now**: prefer leaning on LangGraph's
primitives (stateful graphs, tool-calling, checkpointing) over bespoke
machinery wherever the two overlap.

Key design tension to resolve during Phase 4 design (do not pre-decide in
implementation): LangGraph's checkpointing / persisted state / time-travel
overlap with our event-sourced store + timeline/rewind system (Principles 1 &
11). The event store remains the domain source of truth; the open question is
how LangGraph layers on top (orchestration nodes that **emit our events**)
versus introducing a competing state store. A Phase-4 spike should A/B a
LangGraph DM loop against native tool-use on the eval fixtures, same discipline
as the provider spike.

Context: a LangChain *provider* spike (parked branch
`experiment/langchain-provider-eval`, see `eval/COMPARISON.md`) concluded the
provider layer is neutral — both paths drive Ollama's `format` constrained
decoding. The real opportunity is **orchestration (LangGraph)**, hence its
deferral here rather than to the provider layer.

## Constitution (Non-Negotiable Principles)

### Architecture
1. **Event Sourcing is Sacred** - All state changes emit immutable events. INSERT only, never UPDATE/DELETE `game_events`.
2. **Dependency Injection Only** - Pass dependencies via constructors. No global state, no singletons (except AIManager).
3. **Type Safety Required** - Type hints on ALL function signatures and class attributes. No `Any` without justification.
4. **Separation of Concerns** - No rendering code in `src/core/` or `src/entities/`. No game logic in `src/ui/`. MVC: Model (core), View (ui), Controller (states).

### Code Quality
5. **>= 80% Test Coverage** - Write unit tests alongside implementation. No exceptions.
6. **Specific Error Handling** - Never bare `except:` or `except Exception:` without re-raising. Catch specific exceptions.
7. **Google-style Docstrings** - Required on all public methods and classes (Args, Returns, Raises).

### AI Integration
8. **Never Block Game Loop** - All AI/LLM calls MUST be async. 60 FPS target = <16ms frame time.
9. **Always Have Fallbacks** - Every AI feature needs a rule-based fallback. Game must work without AI.
10. **Token Budget: 4096 Hard Limit** - Validate before sending to Ollama. Count tokens, truncate if needed, cache responses.

### Database
11. **Events are Immutable** - NEVER UPDATE or DELETE from `game_events`. Append-only.
12. **Transaction Safety** - Always use transactions for multi-step database operations.
13. **Database Separation** - SQLite for OLTP, DuckDB for OLAP. Use dbt to transform SQLite events into DuckDB analytics.

### Performance
14. **60 FPS Target** - Frame time < 16ms. Never block game loop with long operations.
15. **< 5s AI Response Time** - Timeout to fallback. Never wait indefinitely.

## Project Structure

```
src/
  core/           # State machines, event store (NO pygame imports)
  states/         # Game state implementations (controllers)
  entities/       # GameObjects - Player, NPC, Item (NO pygame imports)
  ai/             # AI manager, prompts, Ollama integration
    prompts/      # Prompt templates and engineering
  ui/             # Pygame rendering, UI components (NO game logic)
  utils/          # Shared utilities
dbt/
  models/
    staging/      # Raw event transformations (incremental)
    intermediate/ # Business logic (table)
    analytics/    # Game-ready aggregations (incremental)
  macros/         # Reusable game calculations
  tests/          # dbt data tests
tests/
  unit/           # Unit tests
  integration/    # Integration tests
assignments/
  active/         # Current phase plans (SDD workflow)
  completed/      # Reference documentation
  templates/      # Reusable templates
```

## Development Workflow (Spec-Driven Development)

1. **Research** -> `research.md` - Investigate unknowns, validate assumptions
2. **Decisions** -> `decisions.md` - Document architectural decisions (ADR format)
3. **Implementation** -> `PLAN.md` - Execute based on research and decisions
4. **Validation** -> Verify constitution compliance and success criteria

**NO implementation until research and decisions are complete.**

## Tooling
- **Package Management**: uv (`uv add <package>`)
- **Task Runner**: just (`just test`, `just lint`, `just run`, `just --list`)
- **Containers**: Docker Compose (game + Ollama containers)
- **Testing**: Pytest with >= 80% coverage
- **Benchmarks ≠ tests**: Performance benchmarks live in `tests/benchmarks/` and
  are named `bench_*.py` (NOT `test_*.py`). They assert on timing (e.g. rewind
  median < 16ms for the 60 FPS budget), which is environment-sensitive. pytest's
  default `python_files = test_*.py` does not collect them, so `just test` /
  `just check` / `just ci` never run benchmarks — keeping the merge gate stable.
  Run them on demand with `just bench`. **Never** rename a benchmark to `test_*`
  to "make it run": that re-couples perf timing to the merge gate. Add new
  benchmarks as `tests/benchmarks/bench_<thing>.py`.

## Key Patterns
- **State Machine** with event emission for future event sourcing
- **Dependency Injection** via constructors (EventStore, StateMachine, AIManager)
- **Dataclasses** for entities, **Enums** for constants
- **Async/await** for all AI calls
- **Pydantic** for AI response validation

## Anti-Patterns (Never Do)
- Global variables for game state
- Synchronous HTTP requests in game loop
- Rendering code in game logic files
- Instantiating dependencies inside classes
- State changes without emitting events
- Hardcoded values (use config or constants)
- Bare `except:` clauses

## Deviation Protocol
Any deviation from constitution requires: Justification -> Documentation in `decisions.md` -> Human approval -> Tech debt issue -> Remediation plan.

## Reference Docs
Full detailed patterns and code examples are in `.cursor/rules/*.mdc` files.
