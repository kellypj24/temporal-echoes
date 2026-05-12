"""Tests for the AnthropicProvider — mocks the anthropic SDK."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from src.ai.providers.anthropic import AnthropicProvider
from src.ai.providers.base import LLMError, LLMValidationError


class _HeroSchema(BaseModel):
    """A test schema for structured completions."""

    name: str
    level: int


def _make_text_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(text=text, type="text")])


def _make_tool_response(payload: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=payload, name="Hero")])


def _make_provider_with_mock_client(
    monkeypatch: pytest.MonkeyPatch,
    messages_create: AsyncMock,
) -> AnthropicProvider:
    """Build a provider whose _client() returns a mock with messages.create."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    provider = AnthropicProvider()
    fake_client = MagicMock()
    fake_client.messages = MagicMock()
    fake_client.messages.create = messages_create
    monkeypatch.setattr(provider, "_client", lambda: fake_client)
    return provider


class TestInit:
    def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
            AnthropicProvider()

    def test_explicit_api_key_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        provider = AnthropicProvider(api_key="explicit-key")
        assert provider.api_key == "explicit-key"

    def test_model_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        provider = AnthropicProvider()
        assert provider.model == "claude-sonnet-4-6"

    def test_model_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-7")
        provider = AnthropicProvider()
        assert provider.model == "claude-opus-4-7"


class TestSplitSystem:
    def test_extracts_single_system_message(self) -> None:
        system, rest = AnthropicProvider._split_system(
            [{"role": "system", "content": "be a DM"}, {"role": "user", "content": "hi"}]
        )
        assert system == "be a DM"
        assert rest == [{"role": "user", "content": "hi"}]

    def test_concatenates_multiple_system_messages(self) -> None:
        system, rest = AnthropicProvider._split_system(
            [
                {"role": "system", "content": "rule 1"},
                {"role": "system", "content": "rule 2"},
                {"role": "user", "content": "x"},
            ]
        )
        assert "rule 1" in system
        assert "rule 2" in system
        assert rest == [{"role": "user", "content": "x"}]

    def test_default_system_when_absent(self) -> None:
        system, rest = AnthropicProvider._split_system([{"role": "user", "content": "hi"}])
        assert system  # non-empty default


class TestComplete:
    @pytest.mark.asyncio
    async def test_returns_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        messages_create = AsyncMock(return_value=_make_text_response("A dragon roars."))
        provider = _make_provider_with_mock_client(monkeypatch, messages_create)
        result = await provider.complete([{"role": "user", "content": "describe"}])
        assert result == "A dragon roars."

    @pytest.mark.asyncio
    async def test_system_passed_separately(self, monkeypatch: pytest.MonkeyPatch) -> None:
        messages_create = AsyncMock(return_value=_make_text_response("ok"))
        provider = _make_provider_with_mock_client(monkeypatch, messages_create)
        await provider.complete(
            [{"role": "system", "content": "be terse"}, {"role": "user", "content": "x"}]
        )
        call_kwargs = messages_create.await_args.kwargs
        assert call_kwargs["system"] == "be terse"
        assert call_kwargs["messages"] == [{"role": "user", "content": "x"}]

    @pytest.mark.asyncio
    async def test_api_error_wrapped_as_llm_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        messages_create = AsyncMock(side_effect=RuntimeError("rate limit"))
        provider = _make_provider_with_mock_client(monkeypatch, messages_create)
        with pytest.raises(LLMError, match="Anthropic API error"):
            await provider.complete([{"role": "user", "content": "x"}])


class TestCompleteStructured:
    @pytest.mark.asyncio
    async def test_validates_tool_use_input(self, monkeypatch: pytest.MonkeyPatch) -> None:
        messages_create = AsyncMock(return_value=_make_tool_response({"name": "Aria", "level": 7}))
        provider = _make_provider_with_mock_client(monkeypatch, messages_create)
        result = await provider.complete_structured(
            [{"role": "user", "content": "roll a hero"}],
            schema=_HeroSchema,
        )
        assert isinstance(result, _HeroSchema)
        assert result.name == "Aria"
        assert result.level == 7

    @pytest.mark.asyncio
    async def test_forces_schema_as_tool(self, monkeypatch: pytest.MonkeyPatch) -> None:
        messages_create = AsyncMock(return_value=_make_tool_response({"name": "A", "level": 1}))
        provider = _make_provider_with_mock_client(monkeypatch, messages_create)
        await provider.complete_structured([{"role": "user", "content": "x"}], schema=_HeroSchema)
        kwargs = messages_create.await_args.kwargs
        assert kwargs["tools"][0]["name"] == "_HeroSchema"
        assert kwargs["tool_choice"] == {"type": "tool", "name": "_HeroSchema"}

    @pytest.mark.asyncio
    async def test_missing_tool_use_raises_validation_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        text_only = SimpleNamespace(content=[SimpleNamespace(type="text", text="just text")])
        messages_create = AsyncMock(return_value=text_only)
        provider = _make_provider_with_mock_client(monkeypatch, messages_create)
        with pytest.raises(LLMValidationError):
            await provider.complete_structured(
                [{"role": "user", "content": "x"}], schema=_HeroSchema
            )


class TestLazyImport:
    def test_missing_package_raises_llm_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        provider = AnthropicProvider()

        def fail_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "anthropic":
                raise ImportError("no module")
            return __import__(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=fail_import),
            pytest.raises(LLMError, match="anthropic package not installed"),
        ):
            provider._client()
