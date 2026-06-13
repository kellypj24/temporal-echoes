# Recipes pass through to `uv run`, which loads .env via pydantic-settings.
# No need for just to load it as shell env — that breaks on unquoted spaces.

# List available commands
default:
    @just --list

# Install all dependencies (incl. dev group)
install:
    uv sync

# Run the full test suite with coverage
test:
    uv run pytest tests/ -v --cov=src --cov-report=term-missing

# Run unit tests only
test-unit:
    uv run pytest tests/unit/ -v

# Run integration tests only
test-integration:
    uv run pytest tests/integration/ -v

# Run performance benchmarks (tests/benchmarks/bench_*.py).
# Benchmarks are a SEPARATE concern from correctness tests: their timing
# assertions are environment-sensitive, so they are deliberately excluded
# from `just test` / `just check` / `just ci` to keep the merge gate stable.
# bench_*.py is not matched by pytest's default python_files, so override it.
bench *args:
    uv run pytest tests/benchmarks/ -o python_files="bench_*.py" -v -s {{ args }}

# Lint + type check (mirrors CI scope exactly)
lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/
    uv run mypy src/

# Auto-fix lint + format
fmt:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Run the game
run:
    uv run python -m src.main

# Run the game in debug mode
run-debug:
    DEBUG=1 uv run python -m src.main

# Initialize database schemas
init-db:
    uv run python -m src.core.persistence --init

# Run dbt models
dbt-run:
    cd dbt && uv run dbt run

# Run dbt tests
dbt-test:
    cd dbt && uv run dbt test

# Generate and serve dbt docs
dbt-docs:
    cd dbt && uv run dbt docs generate
    cd dbt && uv run dbt docs serve

# Run dbt models + tests
dbt-full:
    cd dbt && uv run dbt run && uv run dbt test

# Start Docker containers (Ollama + game)
docker-up:
    docker compose up -d

# Stop Docker containers
docker-down:
    docker compose down

# Tail Docker logs
docker-logs:
    docker compose logs -f

# Open shell in game container
docker-shell-game:
    docker compose exec game /bin/bash

# Open shell in Ollama container
docker-shell-ollama:
    docker compose exec ollama /bin/bash

# Run the AI-DM eval harness against the mock provider (fast, deterministic).
# Use just eval-real to run against the real LLM (Ollama / Anthropic).
eval *args:
    TEMPORAL_LLM_PROVIDER=mock go -C eval run . -root `pwd` {{ args }}

# Run the eval harness against whichever provider is configured (Ollama, Anthropic).
# Pass through flags: just eval-real -filter combat -timeout 120s
eval-real *args:
    go -C eval run . -root `pwd` {{ args }}

# Filter fixtures by ID substring against the mock provider.
# Usage: just eval-filter combat
eval-filter substr *args:
    TEMPORAL_LLM_PROVIDER=mock go -C eval run . -root `pwd` -filter {{ substr }} {{ args }}

# Run a single fixture by id with rich output (mock provider by default).
# Usage: just ask-fixture eval/fixtures/combat.yaml combat_basic_strike
ask-fixture file id:
    TEMPORAL_LLM_PROVIDER=mock uv run python scripts/eval_runner.py --fixture {{ file }} --id {{ id }}

# Compile the Go eval runner to eval/te-eval (for distribution / CI cache).
eval-build:
    go -C eval build -o te-eval .

# Run Go unit tests (eval/scorer_test.go)
eval-go-test:
    go -C eval test ./...

# Aggregate: lint + test (what to run before commit)
check: lint test eval-go-test

# Aggregate: full CI pipeline locally
ci: install lint test eval-go-test

# Remove build/cache artifacts
clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    rm -rf dist/ build/
