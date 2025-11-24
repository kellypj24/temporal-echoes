.PHONY: install test lint run dbt-run docker-up docker-down clean help

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Temporal Echoes - Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

install: ## Install dependencies with Poetry
	@echo "$(BLUE)Installing dependencies...$(NC)"
	poetry install
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: ## Install with dev dependencies
	@echo "$(BLUE)Installing dev dependencies...$(NC)"
	poetry install --with dev
	@echo "$(GREEN)✓ Dev dependencies installed$(NC)"

test: ## Run test suite with coverage
	@echo "$(BLUE)Running tests...$(NC)"
	poetry run pytest tests/ -v --cov=src --cov-report=term-missing
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	poetry run pytest tests/unit/ -v
	@echo "$(GREEN)✓ Unit tests complete$(NC)"

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	poetry run pytest tests/integration/ -v
	@echo "$(GREEN)✓ Integration tests complete$(NC)"

lint: ## Run linting and type checking
	@echo "$(BLUE)Running linters...$(NC)"
	poetry run ruff check src/ tests/
	@echo "$(BLUE)Running type checker...$(NC)"
	poetry run mypy src/
	@echo "$(GREEN)✓ Linting complete$(NC)"

lint-fix: ## Fix auto-fixable linting issues
	@echo "$(BLUE)Fixing linting issues...$(NC)"
	poetry run ruff check --fix src/ tests/
	@echo "$(GREEN)✓ Fixes applied$(NC)"

format: ## Format code with ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	poetry run ruff format src/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

run: ## Run the game
	@echo "$(BLUE)Starting Temporal Echoes...$(NC)"
	poetry run python -m src.main

run-debug: ## Run the game in debug mode
	@echo "$(BLUE)Starting Temporal Echoes (DEBUG)...$(NC)"
	DEBUG=1 poetry run python -m src.main

dbt-run: ## Run dbt models
	@echo "$(BLUE)Running dbt models...$(NC)"
	cd dbt && poetry run dbt run
	@echo "$(GREEN)✓ dbt models updated$(NC)"

dbt-test: ## Run dbt tests
	@echo "$(BLUE)Running dbt tests...$(NC)"
	cd dbt && poetry run dbt test
	@echo "$(GREEN)✓ dbt tests complete$(NC)"

dbt-docs: ## Generate dbt documentation
	@echo "$(BLUE)Generating dbt docs...$(NC)"
	cd dbt && poetry run dbt docs generate
	cd dbt && poetry run dbt docs serve
	@echo "$(GREEN)✓ dbt docs available at http://localhost:8080$(NC)"

dbt-full: ## Run dbt models and tests
	@echo "$(BLUE)Running full dbt pipeline...$(NC)"
	cd dbt && poetry run dbt run && poetry run dbt test
	@echo "$(GREEN)✓ dbt pipeline complete$(NC)"

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker compose build
	@echo "$(GREEN)✓ Docker images built$(NC)"

docker-up: ## Start Docker containers
	@echo "$(BLUE)Starting Docker containers...$(NC)"
	docker compose up -d
	@echo "$(GREEN)✓ Containers started$(NC)"
	@echo "$(BLUE)Ollama available at http://localhost:11434$(NC)"

docker-down: ## Stop Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	docker compose down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

docker-logs: ## View Docker container logs
	docker compose logs -f

docker-shell-game: ## Open shell in game container
	docker compose exec game /bin/bash

docker-shell-ollama: ## Open shell in Ollama container
	docker compose exec ollama /bin/bash

clean: ## Clean up generated files
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-db: ## Remove database files (WARNING: deletes data)
	@echo "$(RED)WARNING: This will delete all database files!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -f data/events.db data/analytics.duckdb; \
		echo "$(GREEN)✓ Databases deleted$(NC)"; \
	else \
		echo "Cancelled"; \
	fi

init-db: ## Initialize database schemas
	@echo "$(BLUE)Initializing databases...$(NC)"
	poetry run python -m src.core.persistence --init
	@echo "$(GREEN)✓ Databases initialized$(NC)"

check: lint test ## Run all checks (lint + test)
	@echo "$(GREEN)✓ All checks passed$(NC)"

ci: install lint test ## Run CI pipeline
	@echo "$(GREEN)✓ CI pipeline complete$(NC)"

dev-setup: install init-db docker-up ## Complete development setup
	@echo "$(GREEN)✓ Development environment ready!$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  1. Run tests: $(GREEN)make test$(NC)"
	@echo "  2. Start game: $(GREEN)make run$(NC)"
	@echo "  3. View docs: $(GREEN)make dbt-docs$(NC)"

info: ## Show project information
	@echo "$(BLUE)Temporal Echoes - Project Info$(NC)"
	@echo ""
	@echo "Python version: $$(poetry run python --version)"
	@echo "Poetry version: $$(poetry --version)"
	@echo "Project path: $$(pwd)"
	@echo ""
	@echo "Docker status:"
	@docker compose ps 2>/dev/null || echo "  Not running"

