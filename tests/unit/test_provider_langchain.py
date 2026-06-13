"""Tests for the LangChainProvider — mocks ChatOllama so no Ollama is required.

These cover message mapping, text coercion, the happy paths, and error
normalization into the provider error hierarchy. The real end-to-end behaviour
against a live model is exercised by the eval harness (see eval/COMPARISON.md).
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ai.narrator import Mood, NPCLine
from src.ai.providers.base import LLMError, LLMTimeoutError
from src.ai.providers.langchain import LangChainProvider


def _provider(monkeypatch: pytest.MonkeyPatch, chat: object) -> LangChainProvider:
    """Build a provider whose `_build_chat` returns the given fake chat object."""
    provider = LangChainProvider(host="http://localhost:11434", model="test-model")
    monkeypatch.setattr(provider, "_build_chat", lambda temperature, **kw: chat)
    return provider


def test_to_lc_messages_maps_roles() -> None:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    msgs = LangChainProvider._to_lc_messages(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u"},
            {"role": "assistant", "content": "a"},
            {"role": "unknown", "content": "fallback-to-human"},
        ]
    )
    assert [type(m) for m in msgs] == [SystemMessage, HumanMessage, AIMessage, HumanMessage]
    assert msgs[0].content == "sys"


def test_coerce_text_handles_str_and_blocks() -> None:
    assert LangChainProvider._coerce_text("plain") == "plain"
    assert LangChainProvider._coerce_text([{"text": "a"}, {"text": "b"}]) == "ab"
    assert LangChainProvider._coerce_text([{"text": "x"}, "y"]) == "xy"


async def test_complete_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    chat = MagicMock()
    chat.ainvoke = AsyncMock(return_value=SimpleNamespace(content="a sword strike"))
    provider = _provider(monkeypatch, chat)

    result = await provider.complete([{"role": "user", "content": "describe a strike"}])
    assert result == "a sword strike"
    chat.ainvoke.assert_awaited_once()


async def test_complete_timeout_maps_to_llmtimeouterror(monkeypatch: pytest.MonkeyPatch) -> None:
    chat = MagicMock()
    chat.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError())
    provider = _provider(monkeypatch, chat)

    with pytest.raises(LLMTimeoutError):
        await provider.complete([{"role": "user", "content": "hi"}])


async def test_complete_unexpected_error_maps_to_llmerror(monkeypatch: pytest.MonkeyPatch) -> None:
    chat = MagicMock()
    chat.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
    provider = _provider(monkeypatch, chat)

    with pytest.raises(LLMError):
        await provider.complete([{"role": "user", "content": "hi"}])


async def test_complete_structured_returns_schema_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runnable = MagicMock()
    runnable.ainvoke = AsyncMock(return_value=NPCLine(line="Well met.", mood=Mood.WELCOMING))
    chat = MagicMock()
    chat.with_structured_output = MagicMock(return_value=runnable)
    provider = _provider(monkeypatch, chat)

    result = await provider.complete_structured(
        [{"role": "user", "content": "greet the player"}], NPCLine
    )
    assert isinstance(result, NPCLine)
    assert result.mood == "welcoming"  # StrEnum stays plain-string comparable
    chat.with_structured_output.assert_called_once_with(NPCLine)
