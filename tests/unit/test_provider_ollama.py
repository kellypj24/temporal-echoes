"""Tests for the OllamaProvider — uses aioresponses-style mocking via aiohttp."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from pydantic import BaseModel

from src.ai.providers.base import (
    LLMConnectionError,
    LLMError,
    LLMTimeoutError,
    LLMValidationError,
)
from src.ai.providers.ollama import OllamaProvider


class _FakeResponse:
    def __init__(
        self, status: int, json_data: dict[str, Any] | None = None, text: str = ""
    ) -> None:
        self.status = status
        self._json = json_data or {}
        self._text = text

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def json(self) -> dict[str, Any]:
        return self._json

    async def text(self) -> str:
        return self._text


def _make_provider_with_mock_post(post_side_effect: Any) -> OllamaProvider:
    """Build a provider whose internal session.post returns the given response."""
    provider = OllamaProvider(host="http://localhost:11434")
    fake_session = MagicMock()
    fake_session.closed = False
    fake_session.post = MagicMock(side_effect=post_side_effect)
    provider._session = fake_session  # type: ignore[assignment]
    return provider


class TestInit:
    def test_host_gets_http_prefix(self) -> None:
        provider = OllamaProvider(host="localhost:11434")
        assert provider.host == "http://localhost:11434"

    def test_host_keeps_explicit_http(self) -> None:
        provider = OllamaProvider(host="http://example.com:11434")
        assert provider.host == "http://example.com:11434"

    def test_explicit_overrides(self) -> None:
        provider = OllamaProvider(host="http://h:1", model="m", timeout=9.0, temperature=0.1)
        assert provider.model == "m"
        assert provider.timeout == 9.0
        assert provider.temperature == 0.1


class TestComplete:
    @pytest.mark.asyncio
    async def test_returns_message_content(self) -> None:
        provider = _make_provider_with_mock_post(
            lambda *_, **__: _FakeResponse(200, {"message": {"content": "Hello, hero."}})
        )
        result = await provider.complete([{"role": "user", "content": "hi"}])
        assert result == "Hello, hero."

    @pytest.mark.asyncio
    async def test_passes_model_override(self) -> None:
        captured: dict[str, Any] = {}

        def capture(url: str, json: dict[str, Any], **_: Any) -> _FakeResponse:
            captured["json"] = json
            return _FakeResponse(200, {"message": {"content": "ok"}})

        provider = _make_provider_with_mock_post(capture)
        await provider.complete([{"role": "user", "content": "hi"}], model="llama3.2:8b")
        assert captured["json"]["model"] == "llama3.2:8b"

    @pytest.mark.asyncio
    async def test_non_200_raises_llm_error(self) -> None:
        provider = _make_provider_with_mock_post(lambda *_, **__: _FakeResponse(500, text="boom"))
        with pytest.raises(LLMError, match="500"):
            await provider.complete([{"role": "user", "content": "x"}])


class _OutSchema(BaseModel):
    """A test schema."""

    name: str
    level: int


class TestCompleteStructured:
    @pytest.mark.asyncio
    async def test_validates_response_into_schema(self) -> None:
        provider = _make_provider_with_mock_post(
            lambda *_, **__: _FakeResponse(
                200,
                {"message": {"content": '{"name": "Aria", "level": 7}'}},
            )
        )
        result = await provider.complete_structured(
            [{"role": "user", "content": "make a hero"}],
            schema=_OutSchema,
        )
        assert isinstance(result, _OutSchema)
        assert result.name == "Aria"
        assert result.level == 7

    @pytest.mark.asyncio
    async def test_invalid_json_raises_validation_error(self) -> None:
        provider = _make_provider_with_mock_post(
            lambda *_, **__: _FakeResponse(200, {"message": {"content": "not json"}})
        )
        with pytest.raises(LLMValidationError):
            await provider.complete_structured(
                [{"role": "user", "content": "x"}], schema=_OutSchema
            )

    @pytest.mark.asyncio
    async def test_schema_injected_into_system_message(self) -> None:
        captured: dict[str, Any] = {}

        def capture(url: str, json: dict[str, Any], **_: Any) -> _FakeResponse:
            captured["json"] = json
            return _FakeResponse(200, {"message": {"content": '{"name": "A", "level": 1}'}})

        provider = _make_provider_with_mock_post(capture)
        await provider.complete_structured(
            [{"role": "system", "content": "be helpful"}, {"role": "user", "content": "x"}],
            schema=_OutSchema,
        )
        sent_messages = captured["json"]["messages"]
        assert sent_messages[0]["role"] == "system"
        assert "be helpful" in sent_messages[0]["content"]
        assert "valid JSON matching this schema" in sent_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_system_message_prepended_when_absent(self) -> None:
        captured: dict[str, Any] = {}

        def capture(url: str, json: dict[str, Any], **_: Any) -> _FakeResponse:
            captured["json"] = json
            return _FakeResponse(200, {"message": {"content": '{"name": "A", "level": 1}'}})

        provider = _make_provider_with_mock_post(capture)
        await provider.complete_structured([{"role": "user", "content": "x"}], schema=_OutSchema)
        sent_messages = captured["json"]["messages"]
        assert sent_messages[0]["role"] == "system"


class TestRetries:
    @pytest.mark.asyncio
    async def test_connection_error_retries_then_raises(self) -> None:
        provider = OllamaProvider(host="http://localhost:11434")
        fake_session = MagicMock()
        fake_session.closed = False
        fake_session.post = MagicMock(
            side_effect=aiohttp.ClientConnectorError(MagicMock(), OSError("nope"))
        )
        provider._session = fake_session  # type: ignore[assignment]

        with (
            patch("asyncio.sleep", new=AsyncMock()),
            pytest.raises(LLMConnectionError),
        ):
            await provider.complete([{"role": "user", "content": "x"}])
        assert fake_session.post.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_error_maps_to_llm_timeout(self) -> None:
        provider = OllamaProvider(host="http://localhost:11434")
        fake_session = MagicMock()
        fake_session.closed = False
        fake_session.post = MagicMock(side_effect=TimeoutError("slow"))
        provider._session = fake_session  # type: ignore[assignment]

        with (
            patch("asyncio.sleep", new=AsyncMock()),
            pytest.raises(LLMTimeoutError),
        ):
            await provider.complete([{"role": "user", "content": "x"}])


class TestSessionLifecycle:
    @pytest.mark.asyncio
    async def test_close_is_safe_when_session_never_opened(self) -> None:
        provider = OllamaProvider(host="http://localhost:11434")
        await provider.close()  # should not raise

    @pytest.mark.asyncio
    async def test_close_closes_open_session(self) -> None:
        provider = OllamaProvider(host="http://localhost:11434")
        fake_session = MagicMock()
        fake_session.closed = False
        fake_session.close = AsyncMock()
        provider._session = fake_session  # type: ignore[assignment]
        await provider.close()
        fake_session.close.assert_awaited_once()
