# Temporal Echoes Setup Guide

Complete guide for setting up your development environment for Temporal Echoes.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation Steps](#installation-steps)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## Prerequisites

### Required Software

1. **Python 3.13+**
   ```bash
   # Check version
   python --version  # Should show Python 3.13.x
   ```
   
   Install from: https://www.python.org/downloads/

2. **Poetry** (Python package manager)
   ```bash
   # Install Poetry
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Verify installation
   poetry --version
   ```

3. **Docker & Docker Compose**
   ```bash
   # Verify Docker
   docker --version
   docker-compose --version
   ```
   
   Install from: https://www.docker.com/get-started

4. **Git**
   ```bash
   git --version
   ```

### Optional (for development)

- **Cursor IDE** (AI-powered editor) - https://cursor.sh
- **Visual Studio Code** (alternative)
- **Make** (usually pre-installed on macOS/Linux)

---

## Installation Steps

### 1. Clone Repository

```bash
git clone https://github.com/kellypj24/temporal-echoes.git
cd temporal-echoes
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.template .env

# Edit .env with your preferences (optional)
nano .env  # or use your preferred editor
```

Key settings to review:
- `OLLAMA_HOST`: Default is `localhost:11434`
- `LLM_MODEL`: Default is `llama3.2`
- `DEBUG`: Set to `1` for debug mode

### 3. Install Python Dependencies

```bash
# Install all dependencies
make install

# Or manually with Poetry
poetry install
```

This installs:
- Pygame 2.6+
- DuckDB + dbt-duckdb
- aiohttp (for async Ollama calls)
- Pydantic (for validation)
- Development tools (pytest, ruff, mypy)

### 4. Start Ollama Service

```bash
# Start Ollama container
make docker-up

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

Expected output: `{"models":[]}`

### 5. Pull LLM Model

```bash
# Pull Llama 3.2 (primary model, ~2GB)
docker exec temporal-echoes-ollama ollama pull llama3.2

# Verify model is available
docker exec temporal-echoes-ollama ollama list
```

**Note**: This download may take several minutes depending on your internet speed.

Alternative models:
```bash
# Smaller, faster model (for testing)
docker exec temporal-echoes-ollama ollama pull llama3.2:1b

# Larger, more capable model
docker exec temporal-echoes-ollama ollama pull llama3.2:70b
```

### 6. Initialize Databases

```bash
# Create SQLite and DuckDB databases
make init-db

# Verify databases created
ls -lh data/
```

You should see:
- `events.db` (SQLite event store)
- `analytics.duckdb` (DuckDB analytics)

### 7. Run Tests

```bash
# Run full test suite
make test

# Expected output: All tests passing with coverage report
```

### 8. Start the Game

```bash
# Launch game
make run
```

---

## Verification

### Check All Systems

Run these commands to verify your setup:

```bash
# 1. Python dependencies
poetry check

# 2. Linting passes
make lint

# 3. Tests pass
make test

# 4. Ollama is accessible
curl http://localhost:11434/api/tags

# 5. Docker containers running
docker-compose ps
```

### Expected Output

```
✓ Python 3.13.x installed
✓ Poetry 1.8.0 installed
✓ All dependencies installed
✓ Ollama service running
✓ Llama 3.2 model available
✓ Databases initialized
✓ All tests passing
✓ Linting clean
```

---

## Troubleshooting

### Issue: Poetry not found

```bash
# Add Poetry to PATH
export PATH="$HOME/.local/bin:$PATH"

# Add to shell profile for persistence
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc  # or ~/.zshrc
```

### Issue: Docker permission denied

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# On macOS, ensure Docker Desktop is running
```

### Issue: Ollama container fails to start

```bash
# Check Docker logs
docker-compose logs ollama

# Restart container
make docker-down
make docker-up

# Check port availability
lsof -i :11434
```

### Issue: Pygame display not working in Docker

**On Linux:**
```bash
# Allow X server connections
xhost +local:docker

# Set DISPLAY environment variable
export DISPLAY=:0
```

**On macOS/Windows:**
- Run game directly with `make run` (not in Docker)
- Docker display support is complex on non-Linux systems

### Issue: Import errors when running game

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/path/to/temporal-echoes

# Or use Poetry shell
poetry shell
python -m src.main
```

### Issue: Database not found

```bash
# Recreate databases
rm -f data/events.db data/analytics.duckdb
make init-db
```

### Issue: LLM responses timing out

1. Check Ollama is running: `docker-compose ps`
2. Verify model loaded: `docker exec temporal-echoes-ollama ollama list`
3. Test Ollama directly:
   ```bash
   curl http://localhost:11434/api/generate -d '{
     "model": "llama3.2",
     "prompt": "Hello",
     "stream": false
   }'
   ```
4. Increase timeout in `.env`: `LLM_TIMEOUT=10.0`

---

## Development Workflow

### Daily Setup

```bash
# 1. Start development environment
make docker-up

# 2. Run tests to ensure everything works
make test

# 3. Start coding!
```

### Before Committing

```bash
# 1. Format code
make format

# 2. Run linting
make lint

# 3. Run tests
make test

# 4. If all pass, commit
git add .
git commit -m "feat: your feature description"
```

### Using Cursor AI

1. Open project in Cursor
2. MDC rules will auto-apply based on files you edit
3. For architecture questions, type: `@architecture-worker`
4. Supervisors will guide implementation

---

## Next Steps

### 1. Explore the Codebase

```bash
# View project structure
tree -L 2 -I '__pycache__|*.pyc'

# Read MDC rules
cat .cursor/rules/architect-supervisor.mdc
```

### 2. Run First Development Phase

```bash
# Copy phase template
cp assignments/templates/PHASE_TEMPLATE.md assignments/active/phase-1-core-game-loop/PLAN.md

# Edit plan
nano assignments/active/phase-1-core-game-loop/PLAN.md
```

### 3. Start Development

Follow the phase plan with Cursor AI assistance:
- `@architect-supervisor` will coordinate
- Workers will auto-attach to relevant files
- Use templates in `assignments/templates/`

### 4. Learn the Stack

- **Event Sourcing**: Read `src/core/persistence.py`
- **State Machine**: Read `src/states/`
- **AI Integration**: Read `src/ai/`
- **dbt Models**: Read `dbt/models/`

### 5. Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

## Useful Commands

| Command | Purpose |
|---------|---------|
| `make help` | Show all available commands |
| `make dev-setup` | Complete setup from scratch |
| `make test` | Run test suite |
| `make lint` | Check code quality |
| `make run` | Start game |
| `make dbt-run` | Update analytics |
| `make docker-up` | Start services |
| `make docker-down` | Stop services |
| `make clean` | Clean generated files |
| `make info` | Show environment info |

---

## Getting Help

- **Documentation**: [README.md](README.md)
- **Architecture**: `.cursor/rules/*.mdc`
- **Issues**: [GitHub Issues](https://github.com/kellypj24/temporal-echoes/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kellypj24/temporal-echoes/discussions)

---

## Success! 🎉

If you've completed all steps:
- ✅ Dependencies installed
- ✅ Ollama running with Llama 3.2
- ✅ Databases initialized
- ✅ Tests passing
- ✅ Game launches

You're ready to start developing Temporal Echoes!

**First task**: Review `assignments/templates/PHASE_TEMPLATE.md` and create your first phase plan.

