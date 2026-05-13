"""Tests for the Narrator facade against MockProvider."""

import pytest

from src.ai.narrator import CombatNarration, Narrator, NPCLine
from src.ai.providers.mock import MockProvider


class TestNarrateCombat:
    @pytest.mark.asyncio
    async def test_returns_combat_narration(self) -> None:
        narrator = Narrator(MockProvider())
        result = await narrator.narrate_combat(
            actor="Aria", action="slashes", target="goblin", damage=12
        )
        assert isinstance(result, CombatNarration)
        assert 0 <= result.intensity <= 10
        assert len(result.prose) > 0

    @pytest.mark.asyncio
    async def test_prompt_includes_event_details(self) -> None:
        provider = MockProvider()
        narrator = Narrator(provider)
        await narrator.narrate_combat(actor="Aria", action="slashes", target="goblin", damage=42)
        prompt = provider.calls[0]["prompt"]
        assert "Aria" in prompt
        assert "goblin" in prompt
        assert "42" in prompt


class TestNPCDialogue:
    @pytest.mark.asyncio
    async def test_returns_npc_line(self) -> None:
        narrator = Narrator(MockProvider())
        result = await narrator.npc_dialogue(
            npc_name="Eldra", situation="player approaches the shrine"
        )
        assert isinstance(result, NPCLine)
        assert result.mood
        assert result.line


class TestDescribeLocation:
    @pytest.mark.asyncio
    async def test_returns_text(self) -> None:
        narrator = Narrator(MockProvider())
        result = await narrator.describe_location(
            location_name="Hollow Bell Temple", beats="ruined, foggy, dawn"
        )
        assert isinstance(result, str)
        assert len(result) > 0
