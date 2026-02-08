"""Unit tests for GameConfig.

These tests verify that the configuration system works correctly:
- Loading from environment variables
- Type validation with Pydantic
- Default values
- Computed properties
- Directory creation

Constitution Principles Tested:
- #3: Type safety (Pydantic validation)
- #7: Configuration as code (DEC-0007)
"""

from pathlib import Path

import pytest

from src.core.config import GameConfig

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Clean environment variables and prevent .env file loading."""
    # Remove any config-related env vars
    config_vars = [
        "GAME_TITLE",
        "FPS_TARGET",
        "WINDOW_WIDTH",
        "WINDOW_HEIGHT",
        "FULLSCREEN",
        "DATABASE_PATH",
        "DUCKDB_PATH",
        "OLLAMA_HOST",
        "LLM_MODEL",
        "LLM_TIMEOUT",
        "LLM_TEMPERATURE",
        "DEBUG_MODE",
        "LOG_LEVEL",
    ]

    for var in config_vars:
        monkeypatch.delenv(var, raising=False)

    # Change to temp dir so pydantic-settings won't find the project .env file
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create temporary directory for config testing."""
    config_dir = tmp_path / "test_config"
    config_dir.mkdir()
    return config_dir


# ============================================================================
# Default Values Tests
# ============================================================================


def test_config_default_values(clean_env: None) -> None:
    """Test that config loads with default values."""
    config = GameConfig()

    # Game settings
    assert config.game_title == "Temporal Echoes"
    assert config.fps_target == 60
    assert config.window_width == 800
    assert config.window_height == 600
    assert config.fullscreen is False

    # Database settings
    assert config.database_path == "data/events.db"
    assert config.duckdb_path == "data/analytics.duckdb"

    # AI settings
    assert config.ollama_host == "localhost:11434"
    assert config.llm_model == "llama3.2"
    assert config.llm_timeout == 5.0
    assert config.llm_temperature == 0.7

    # Development settings
    assert config.debug_mode is False
    assert config.log_level == "INFO"


def test_config_custom_values(clean_env: None) -> None:
    """Test that config accepts custom values."""
    config = GameConfig(
        game_title="Custom Game",
        fps_target=120,
        window_width=1920,
        window_height=1080,
        fullscreen=True,
        database_path="/tmp/test.db",
        debug_mode=True,
        log_level="DEBUG",
    )

    assert config.game_title == "Custom Game"
    assert config.fps_target == 120
    assert config.window_width == 1920
    assert config.window_height == 1080
    assert config.fullscreen is True
    assert config.database_path == "/tmp/test.db"
    assert config.debug_mode is True
    assert config.log_level == "DEBUG"


# ============================================================================
# Environment Variable Tests
# ============================================================================


def test_config_loads_from_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that config loads from environment variables."""
    # Set environment variables
    monkeypatch.setenv("GAME_TITLE", "Env Game")
    monkeypatch.setenv("FPS_TARGET", "90")
    monkeypatch.setenv("WINDOW_WIDTH", "1024")
    monkeypatch.setenv("WINDOW_HEIGHT", "768")
    monkeypatch.setenv("FULLSCREEN", "true")
    monkeypatch.setenv("DATABASE_PATH", "/custom/db.db")
    monkeypatch.setenv("DEBUG_MODE", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    config = GameConfig()

    assert config.game_title == "Env Game"
    assert config.fps_target == 90
    assert config.window_width == 1024
    assert config.window_height == 768
    assert config.fullscreen is True
    assert config.database_path == "/custom/db.db"
    assert config.debug_mode is True
    assert config.log_level == "DEBUG"


def test_config_env_vars_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that environment variables override default values."""
    monkeypatch.setenv("FPS_TARGET", "144")

    config = GameConfig()

    # Overridden value
    assert config.fps_target == 144

    # Default values still work
    assert config.game_title == "Temporal Echoes"
    assert config.window_width == 800


def test_config_case_insensitive_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that environment variables are case insensitive."""
    # Try lowercase
    monkeypatch.setenv("fps_target", "75")

    config = GameConfig()

    assert config.fps_target == 75


# ============================================================================
# Validation Tests
# ============================================================================


def test_config_fps_target_validation(clean_env: None) -> None:
    """Test that fps_target validation works."""
    # Valid values
    config = GameConfig(fps_target=1)
    assert config.fps_target == 1

    config = GameConfig(fps_target=144)
    assert config.fps_target == 144

    # Invalid values
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        GameConfig(fps_target=0)

    with pytest.raises(ValueError, match="less than or equal to 144"):
        GameConfig(fps_target=200)


def test_config_window_dimensions_validation(clean_env: None) -> None:
    """Test that window dimension validation works."""
    # Valid values
    config = GameConfig(window_width=640, window_height=480)
    assert config.window_width == 640
    assert config.window_height == 480

    # Invalid values
    with pytest.raises(ValueError, match="greater than or equal to 640"):
        GameConfig(window_width=400)

    with pytest.raises(ValueError, match="greater than or equal to 480"):
        GameConfig(window_height=300)


def test_config_llm_timeout_validation(clean_env: None) -> None:
    """Test that llm_timeout validation works."""
    # Valid values
    config = GameConfig(llm_timeout=1.0)
    assert config.llm_timeout == 1.0

    config = GameConfig(llm_timeout=30.0)
    assert config.llm_timeout == 30.0

    # Invalid values
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        GameConfig(llm_timeout=0.5)

    with pytest.raises(ValueError, match="less than or equal to 30"):
        GameConfig(llm_timeout=60.0)


def test_config_llm_temperature_validation(clean_env: None) -> None:
    """Test that llm_temperature validation works."""
    # Valid values
    config = GameConfig(llm_temperature=0.0)
    assert config.llm_temperature == 0.0

    config = GameConfig(llm_temperature=2.0)
    assert config.llm_temperature == 2.0

    # Invalid values
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        GameConfig(llm_temperature=-0.1)

    with pytest.raises(ValueError, match="less than or equal to 2"):
        GameConfig(llm_temperature=3.0)


# ============================================================================
# Computed Properties Tests
# ============================================================================


def test_config_fixed_timestep_property(clean_env: None) -> None:
    """Test that fixed_timestep is computed correctly."""
    config = GameConfig(fps_target=60)
    assert config.fixed_timestep == pytest.approx(1.0 / 60.0)

    config = GameConfig(fps_target=120)
    assert config.fixed_timestep == pytest.approx(1.0 / 120.0)

    config = GameConfig(fps_target=30)
    assert config.fixed_timestep == pytest.approx(1.0 / 30.0)


def test_config_database_dir_property(clean_env: None) -> None:
    """Test that database_dir is computed correctly."""
    config = GameConfig(database_path="data/events.db")
    assert config.database_dir == Path("data")

    config = GameConfig(database_path="/custom/path/db.db")
    assert config.database_dir == Path("/custom/path")


def test_config_is_development_property(clean_env: None) -> None:
    """Test that is_development is computed correctly."""
    # Debug mode enabled
    config = GameConfig(debug_mode=True)
    assert config.is_development is True

    # Log level is DEBUG
    config = GameConfig(log_level="DEBUG")
    assert config.is_development is True

    # Neither (production)
    config = GameConfig(debug_mode=False, log_level="INFO")
    assert config.is_development is False


# ============================================================================
# Directory Creation Tests
# ============================================================================


def test_config_ensure_directories_exist(temp_config_dir: Path) -> None:
    """Test that ensure_directories_exist creates directories."""
    db_path = temp_config_dir / "events" / "test.db"
    duckdb_path = temp_config_dir / "analytics" / "test.duckdb"

    config = GameConfig(
        database_path=str(db_path),
        duckdb_path=str(duckdb_path),
    )

    # Directories should not exist yet
    assert not db_path.parent.exists()
    assert not duckdb_path.parent.exists()

    # Create directories
    config.ensure_directories_exist()

    # Directories should now exist
    assert db_path.parent.exists()
    assert duckdb_path.parent.exists()


def test_config_ensure_directories_exist_idempotent(temp_config_dir: Path) -> None:
    """Test that ensure_directories_exist can be called multiple times."""
    db_path = temp_config_dir / "events" / "test.db"

    config = GameConfig(database_path=str(db_path))

    # Call multiple times (should not error)
    config.ensure_directories_exist()
    config.ensure_directories_exist()
    config.ensure_directories_exist()

    assert db_path.parent.exists()


# ============================================================================
# Serialization Tests
# ============================================================================


def test_config_to_dict(clean_env: None) -> None:
    """Test that to_dict returns config as dictionary."""
    config = GameConfig(
        game_title="Test Game",
        fps_target=120,
        debug_mode=True,
    )

    config_dict = config.to_dict()

    assert isinstance(config_dict, dict)
    assert config_dict["game_title"] == "Test Game"
    assert config_dict["fps_target"] == 120
    assert config_dict["debug_mode"] is True

    # Computed properties should not be in dict
    assert "fixed_timestep" not in config_dict
    assert "database_dir" not in config_dict
    assert "is_development" not in config_dict


# ============================================================================
# String Representation Tests
# ============================================================================


def test_config_repr(clean_env: None) -> None:
    """Test developer-friendly string representation."""
    config = GameConfig(fps_target=60, debug_mode=True)

    repr_str = repr(config)

    assert "GameConfig" in repr_str
    assert "fps=60" in repr_str
    assert "debug=True" in repr_str


def test_config_str(clean_env: None) -> None:
    """Test user-friendly string representation."""
    config = GameConfig(
        game_title="Test Game",
        fps_target=90,
        debug_mode=False,
    )

    str_repr = str(config)

    assert "Test Game" in str_repr
    assert "90 FPS" in str_repr
    assert "Release mode" in str_repr


def test_config_str_debug_mode(clean_env: None) -> None:
    """Test string representation in debug mode."""
    config = GameConfig(debug_mode=True)

    str_repr = str(config)

    assert "Debug mode" in str_repr


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_config_invalid_type_for_int_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that invalid types are caught by validation."""
    monkeypatch.setenv("FPS_TARGET", "not_a_number")

    with pytest.raises(ValueError):
        GameConfig()


def test_config_invalid_type_for_bool_field(clean_env: None) -> None:
    """Test that invalid bool values are handled."""
    # Pydantic is lenient with booleans, accepts various formats
    config = GameConfig(fullscreen="yes")
    assert config.fullscreen is True

    config = GameConfig(fullscreen="no")
    assert config.fullscreen is False


def test_config_extra_fields_ignored(clean_env: None) -> None:
    """Test that extra fields are ignored (not an error)."""
    # Should not raise an error
    config = GameConfig(unknown_field="value")  # type: ignore[call-arg]

    # Config should still work
    assert config.fps_target == 60


# ============================================================================
# Integration Tests
# ============================================================================


def test_config_full_workflow(temp_config_dir: Path) -> None:
    """Test complete configuration workflow."""
    # 1. Create config with custom values
    db_path = temp_config_dir / "game" / "events.db"
    config = GameConfig(
        game_title="Integration Test",
        fps_target=120,
        database_path=str(db_path),
        debug_mode=True,
    )

    # 2. Verify values
    assert config.game_title == "Integration Test"
    assert config.fps_target == 120
    assert config.debug_mode is True

    # 3. Check computed properties
    assert config.fixed_timestep == pytest.approx(1.0 / 120.0)
    assert config.is_development is True

    # 4. Create directories
    config.ensure_directories_exist()
    assert db_path.parent.exists()

    # 5. Serialize to dict
    config_dict = config.to_dict()
    assert config_dict["game_title"] == "Integration Test"

    # 6. String representations
    assert "Integration Test" in str(config)
    assert "GameConfig" in repr(config)
