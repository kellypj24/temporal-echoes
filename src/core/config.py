"""Configuration management for Temporal Echoes.

This module provides type-safe configuration using Pydantic Settings.
Configuration can be loaded from environment variables or .env files,
with automatic validation at startup.

Architecture Decision Records:
- DEC-0007: Pydantic Settings for type-safe configuration
- Research Topic 5: Configuration Management

Constitution Principles:
- #3: Type safety (full type hints with validation)
- #7: Configuration as code (type-safe, validated)
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GameConfig(BaseSettings):
    """
    Game configuration with type-safe validation.

    This class uses Pydantic Settings to provide type-safe configuration
    management with automatic loading from environment variables and .env files.

    Configuration Priority (highest to lowest):
    1. Explicitly passed values
    2. Environment variables
    3. .env file values
    4. Default values

    Example:
        >>> # Load from .env file
        >>> config = GameConfig()
        >>> print(config.fps_target)
        60

        >>> # Override with environment variable
        >>> import os
        >>> os.environ["FPS_TARGET"] = "120"
        >>> config = GameConfig()
        >>> print(config.fps_target)
        120

        >>> # Override programmatically
        >>> config = GameConfig(fps_target=144)
        >>> print(config.fps_target)
        144

    Attributes:
        game_title: Game title for display
        fps_target: Target frames/ticks per second (1-144)
        window_width: Window width in pixels (640+)
        window_height: Window height in pixels (480+)
        fullscreen: Whether to run in fullscreen mode

        database_path: Path to SQLite event store database
        duckdb_path: Path to DuckDB analytics database

        llm_provider: Active LLM backend (ollama, anthropic)
        ollama_host: Ollama API host:port
        llm_model: LLM model name, tag included (e.g., llama3.2:3b, gemma3:4b)
        llm_timeout: LLM request timeout in seconds (1.0-30.0)
        llm_temperature: LLM temperature for creativity (0.0-2.0)
        anthropic_api_key: API key for the Anthropic provider (optional)
        anthropic_model: Claude model ID when llm_provider=anthropic

        debug_mode: Enable debug mode (verbose logging)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    # ========================================================================
    # Game Settings
    # ========================================================================

    game_title: str = Field(
        default="Temporal Echoes",
        description="Game title displayed in window/logs",
    )

    fps_target: int = Field(
        default=60,
        ge=1,
        le=144,
        description="Target frames/ticks per second",
    )

    window_width: int = Field(
        default=800,
        ge=640,
        description="Window width in pixels",
    )

    window_height: int = Field(
        default=600,
        ge=480,
        description="Window height in pixels",
    )

    fullscreen: bool = Field(
        default=False,
        description="Run in fullscreen mode",
    )

    # ========================================================================
    # Database Settings
    # ========================================================================

    database_path: str = Field(
        default="data/events.db",
        description="Path to SQLite event store database",
    )

    duckdb_path: str = Field(
        default="data/analytics.duckdb",
        description="Path to DuckDB analytics database",
    )

    # ========================================================================
    # AI Settings (Phase 4+)
    # ========================================================================

    llm_provider: str = Field(
        default="ollama",
        pattern="^(ollama|anthropic)$",
        description="Active LLM backend (ollama, anthropic)",
    )

    ollama_host: str = Field(
        default="localhost:11434",
        description="Ollama API host:port",
    )

    llm_model: str = Field(
        default="llama3.2:3b",
        description="LLM model name, tag included (e.g., llama3.2:3b, gemma3:4b)",
    )

    llm_timeout: float = Field(
        default=5.0,
        ge=1.0,
        le=30.0,
        description="LLM request timeout in seconds",
    )

    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for creativity",
    )

    anthropic_api_key: str | None = Field(
        default=None,
        description="API key for the Anthropic provider (read from env)",
    )

    anthropic_model: str = Field(
        default="claude-sonnet-4-6",
        description="Claude model ID used when llm_provider=anthropic",
    )

    # ========================================================================
    # Development Settings
    # ========================================================================

    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode (verbose logging)",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    # ========================================================================
    # Computed Properties
    # ========================================================================

    @property
    def fixed_timestep(self) -> float:
        """
        Calculate fixed timestep from FPS target.

        Returns:
            Fixed timestep in seconds (e.g., 0.01666... for 60 FPS)
        """
        return 1.0 / self.fps_target

    @property
    def database_dir(self) -> Path:
        """
        Get database directory path.

        Returns:
            Path object for database directory
        """
        return Path(self.database_path).parent

    @property
    def is_development(self) -> bool:
        """
        Check if running in development mode.

        Returns:
            True if debug mode enabled or log level is DEBUG
        """
        return self.debug_mode or self.log_level == "DEBUG"

    # ========================================================================
    # Validation Methods
    # ========================================================================

    def ensure_directories_exist(self) -> None:
        """
        Ensure database directories exist.

        Creates parent directories for database_path and duckdb_path
        if they don't already exist.

        Example:
            >>> config = GameConfig()
            >>> config.ensure_directories_exist()
            # Creates data/ directory if it doesn't exist
        """
        # Create database directory
        db_dir = Path(self.database_path).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)

        # Create duckdb directory
        duckdb_dir = Path(self.duckdb_path).parent
        if not duckdb_dir.exists():
            duckdb_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, object]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary of configuration values (excludes computed properties)

        Example:
            >>> config = GameConfig()
            >>> config_dict = config.to_dict()
            >>> print(config_dict["fps_target"])
            60
        """
        return self.model_dump()

    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (
            f"GameConfig(fps={self.fps_target}, db={self.database_path}, debug={self.debug_mode})"
        )

    def __str__(self) -> str:
        """User-friendly string representation."""
        return (
            f"Game Configuration: {self.game_title} "
            f"({self.fps_target} FPS, "
            f"{'Debug' if self.debug_mode else 'Release'} mode)"
        )
