"""Tests for the MockProvider — pattern routing, structured validation, call log."""

import json

import pytest
from pydantic import BaseModel

from src.ai.providers.base import LLMValidationError, get_provider
from src.ai.providers.mock import MockProvider


class _Schema(BaseModel):
    prose: str
    intensity: int


class _NPCSchema(BaseModel):
    line: str
    mood: str


class TestRouting:
    @pytest.mark.asyncio
    async def test_combat_route_returns_canned_prose(self) -> None:
        provider = MockProvider()
        result = await provider.complete(
            [{"role": "user", "content": "Combat event: Aria slashes goblin for 12 damage."}]
        )
        assert "Steel rings" in result

    @pytest.mark.asyncio
    async def test_npc_route_serializes_dict_as_json_in_complete(self) -> None:
        provider = MockProvider()
        result = await provider.complete(
            [{"role": "user", "content": "NPC: Eldra\nSituation: player approaches"}]
        )
        parsed = json.loads(result)
        assert parsed["mood"] == "wary"

    @pytest.mark.asyncio
    async def test_location_route_returns_text(self) -> None:
        provider = MockProvider()
        result = await provider.complete(
            [{"role": "user", "content": "Location: Temple\nAtmospheric cues: foggy"}]
        )
        assert "stone arches" in result

    @pytest.mark.asyncio
    async def test_routes_do_not_cross_match(self) -> None:
        """A location prompt whose system message says 'No dialogue' must not fire the NPC route."""
        provider = MockProvider()
        result = await provider.complete(
            [
                {"role": "system", "content": "You describe locations. No dialogue."},
                {"role": "user", "content": "Location: ruins"},
            ]
        )
        assert "stone arches" in result

    @pytest.mark.asyncio
    async def test_unmatched_prompt_returns_default(self) -> None:
        provider = MockProvider(routes=[], default_text="custom default")
        result = await provider.complete([{"role": "user", "content": "anything"}])
        assert result == "custom default"


class TestStructured:
    @pytest.mark.asyncio
    async def test_combat_route_validates_into_schema(self) -> None:
        provider = MockProvider()
        result = await provider.complete_structured(
            [{"role": "user", "content": "Combat event: hero strikes orc"}],
            schema=_Schema,
        )
        assert isinstance(result, _Schema)
        assert result.intensity == 7

    @pytest.mark.asyncio
    async def test_npc_route_into_npc_schema(self) -> None:
        provider = MockProvider()
        result = await provider.complete_structured(
            [{"role": "user", "content": "NPC: Eldra\nSituation: greeting"}],
            schema=_NPCSchema,
        )
        assert result.mood == "wary"

    @pytest.mark.asyncio
    async def test_unmatched_default_structured_raises_validation_error(self) -> None:
        # default_structured is empty by default — validation against _Schema fails
        provider = MockProvider(routes=[])
        with pytest.raises(LLMValidationError):
            await provider.complete_structured([{"role": "user", "content": "x"}], schema=_Schema)

    @pytest.mark.asyncio
    async def test_default_structured_can_be_overridden(self) -> None:
        provider = MockProvider(
            routes=[],
            default_structured={"prose": "fallback", "intensity": 1},
        )
        result = await provider.complete_structured(
            [{"role": "user", "content": "x"}], schema=_Schema
        )
        assert result.prose == "fallback"


class TestRegistration:
    @pytest.mark.asyncio
    async def test_register_route_takes_priority(self) -> None:
        provider = MockProvider()
        provider.register_route(
            lambda p, _s: "override-trigger" in p,
            "custom response",
        )
        result = await provider.complete(
            [{"role": "user", "content": "override-trigger plus combat noise"}]
        )
        # The new route fires first even though "combat" would also match
        assert result == "custom response"


class TestCallLog:
    @pytest.mark.asyncio
    async def test_records_complete_calls(self) -> None:
        provider = MockProvider()
        await provider.complete([{"role": "user", "content": "describe the temple"}])
        assert len(provider.calls) == 1
        assert provider.calls[0]["kind"] == "complete"
        assert "temple" in provider.calls[0]["prompt"]

    @pytest.mark.asyncio
    async def test_records_structured_calls_with_schema(self) -> None:
        provider = MockProvider()
        await provider.complete_structured(
            [{"role": "user", "content": "Combat event: x"}], schema=_Schema
        )
        assert provider.calls[0]["kind"] == "complete_structured"
        assert provider.calls[0]["schema"] == "_Schema"


class TestFactory:
    def test_get_provider_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEMPORAL_LLM_PROVIDER", raising=False)
        provider = get_provider("mock")
        assert type(provider).__name__ == "MockProvider"

    def test_get_provider_mock_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEMPORAL_LLM_PROVIDER", "mock")
        provider = get_provider()
        assert type(provider).__name__ == "MockProvider"
