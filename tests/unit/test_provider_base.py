"""Tests for the LLM provider factory and error hierarchy."""

import pytest

from src.ai.providers.base import (
    LLMConnectionError,
    LLMError,
    LLMTimeoutError,
    LLMValidationError,
    get_provider,
)


class TestErrorHierarchy:
    def test_connection_error_is_llm_error(self) -> None:
        assert issubclass(LLMConnectionError, LLMError)

    def test_timeout_error_is_llm_error(self) -> None:
        assert issubclass(LLMTimeoutError, LLMError)

    def test_validation_error_is_llm_error(self) -> None:
        assert issubclass(LLMValidationError, LLMError)

    def test_subclasses_are_distinct(self) -> None:
        assert LLMConnectionError is not LLMTimeoutError
        assert LLMTimeoutError is not LLMValidationError


class TestGetProvider:
    def test_explicit_ollama(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEMPORAL_LLM_PROVIDER", raising=False)
        provider = get_provider("ollama")
        assert type(provider).__name__ == "OllamaProvider"

    def test_default_is_ollama(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEMPORAL_LLM_PROVIDER", raising=False)
        provider = get_provider()
        assert type(provider).__name__ == "OllamaProvider"

    def test_env_var_anthropic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEMPORAL_LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        provider = get_provider()
        assert type(provider).__name__ == "AnthropicProvider"

    def test_explicit_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEMPORAL_LLM_PROVIDER", "anthropic")
        provider = get_provider("ollama")
        assert type(provider).__name__ == "OllamaProvider"

    def test_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        provider = get_provider("ANTHROPIC")
        assert type(provider).__name__ == "AnthropicProvider"

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_provider("openai")

    def test_unknown_provider_error_lists_valid_options(self) -> None:
        with pytest.raises(ValueError, match="ollama, anthropic"):
            get_provider("gpt-4")
