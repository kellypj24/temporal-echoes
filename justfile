set dotenv-load

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

# Aggregate: lint + test (what to run before commit)
check: lint test

# Aggregate: full CI pipeline locally
ci: install lint test

# Remove build/cache artifacts
clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    rm -rf dist/ build/
