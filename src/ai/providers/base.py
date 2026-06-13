"""LLM provider abstraction.

The AI Dungeon Master harness imports only `LLMProvider` — never a concrete
provider. Swap providers via the `TEMPORAL_LLM_PROVIDER` environment variable
with zero changes to game/agent code.

Supported providers:
  ollama     — local Ollama (default, offline-capable)
  anthropic  — Claude API (higher quality, requires ANTHROPIC_API_KEY)
  mock       — deterministic in-process responses for harness iteration
"""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class LLMProvider(Protocol):
    """Contract that every LLM provider must satisfy.

    The agent harness depends only on this protocol — never on a concrete
    implementation. This keeps provider swaps transparent to all game code.
    """

    async def complete(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Generate a text completion.

        Args:
            messages: List of `{role, content}` dicts (OpenAI-style format).
            **kwargs: Provider-specific overrides (model, temperature, max_tokens, ...).

        Returns:
            Generated text string.

        Raises:
            LLMTimeoutError: Provider did not respond within timeout.
            LLMConnectionError: Provider unreachable.
            LLMError: Any other provider failure.
        """
        ...

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        """Generate a completion validated against a Pydantic schema.

        Each provider implements this differently:
          - Ollama: JSON mode + schema-instructed prompt
          - Anthropic: `tool_use` with the schema as a forced tool

        Args:
            messages: List of `{role, content}` dicts.
            schema: Pydantic model class to validate the response against.
            **kwargs: Provider-specific overrides.

        Returns:
            Validated instance of `schema`.

        Raises:
            LLMValidationError: Response could not be parsed into the schema.
            LLMTimeoutError: Provider did not respond within timeout.
            LLMConnectionError: Provider unreachable.
        """
        ...


class LLMError(Exception):
    """Base exception for all LLM provider errors."""


class LLMConnectionError(LLMError):
    """Provider unreachable."""


class LLMTimeoutError(LLMError):
    """Provider did not respond within timeout."""


class LLMValidationError(LLMError):
    """Response could not be parsed into the expected schema."""


def get_provider(name: str | None = None) -> LLMProvider:
    """Instantiate the configured LLM provider.

    Reads `TEMPORAL_LLM_PROVIDER` from environment when `name` is None
    (default: `"ollama"`). Imports are deferred so an unused provider
    does not require its dependency to be installed.

    Args:
        name: Override the env var. Useful in tests.

    Returns:
        Configured `LLMProvider` instance.

    Raises:
        ValueError: `name` does not match a supported provider.
    """
    import os

    provider = (name or os.getenv("TEMPORAL_LLM_PROVIDER") or "ollama").lower()

    if provider == "ollama":
        from src.ai.providers.ollama import OllamaProvider

        return OllamaProvider()
    if provider == "anthropic":
        from src.ai.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    if provider == "mock":
        from src.ai.providers.mock import MockProvider

        return MockProvider()
    if provider == "langchain":
        from src.ai.providers.langchain import LangChainProvider

        return LangChainProvider()
    raise ValueError(
        f"Unknown LLM provider: {provider!r}. "
        "Set TEMPORAL_LLM_PROVIDER to one of: ollama, anthropic, mock, langchain"
    )
