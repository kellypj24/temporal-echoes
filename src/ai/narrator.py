"""Narrator facade — the surface the eval harness targets.

The Narrator wraps an `LLMProvider` with three game-specific calls used by
the seed eval fixtures:

- `narrate_combat`: turn a structured combat event into prose + intensity.
- `npc_dialogue`: produce a single NPC line + mood from situational context.
- `describe_location`: emit a 1–3 sentence atmospheric description.

This is intentionally minimal. Phase 4 will replace or expand it with the
real AI DM; the seed fixtures and harness wiring exist so that expansion has
something concrete to plug into.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.ai.providers import LLMProvider


class CombatNarration(BaseModel):
    """A single combat narration: prose plus a 0-10 intensity score."""

    prose: str = Field(min_length=1, max_length=400)
    intensity: int = Field(ge=0, le=10)


class NPCLine(BaseModel):
    """A single line of NPC dialogue plus the mood it should be delivered in."""

    line: str = Field(min_length=1, max_length=400)
    mood: str = Field(min_length=1, max_length=40)


_COMBAT_SYSTEM = (
    "You are the combat narrator of a 16-bit RPG. "
    "Given a combat event, produce one vivid sentence of prose and an "
    "intensity score from 0 (gentle) to 10 (devastating)."
)

_NPC_SYSTEM = (
    "You are an NPC voice in a 16-bit RPG. Reply with one line of dialogue "
    "and the mood it is delivered in. Keep lines under 200 characters."
)

_LOCATION_SYSTEM = (
    "You are the location describer of a 16-bit RPG. Produce a 1-3 sentence "
    "atmospheric description. No dialogue. No second-person commands."
)


class Narrator:
    """Game-specific narration calls on top of an `LLMProvider`."""

    def __init__(self, provider: "LLMProvider") -> None:
        self._provider = provider

    async def narrate_combat(
        self,
        actor: str,
        action: str,
        target: str,
        damage: int,
    ) -> CombatNarration:
        """Narrate a single combat exchange.

        Args:
            actor: Name of the entity performing the action.
            action: Short verb phrase (e.g. "slashes", "casts fireball at").
            target: Name of the entity receiving the action.
            damage: Damage dealt (used to inform intensity).
        """
        user = (
            f"Combat event: {actor} {action} {target} for {damage} damage. "
            "Produce a single sentence describing what happens."
        )
        return await self._provider.complete_structured(  # type: ignore[return-value]
            [
                {"role": "system", "content": _COMBAT_SYSTEM},
                {"role": "user", "content": user},
            ],
            schema=CombatNarration,
        )

    async def npc_dialogue(
        self,
        npc_name: str,
        situation: str,
    ) -> NPCLine:
        """Produce one NPC line for the given situation.

        Args:
            npc_name: The NPC's display name.
            situation: One-sentence description of the encounter context.
        """
        user = (
            f"NPC: {npc_name}\nSituation: {situation}\n"
            "Produce one line of dialogue plus the mood it is delivered in."
        )
        return await self._provider.complete_structured(  # type: ignore[return-value]
            [
                {"role": "system", "content": _NPC_SYSTEM},
                {"role": "user", "content": user},
            ],
            schema=NPCLine,
        )

    async def describe_location(self, location_name: str, beats: str) -> str:
        """Produce a 1-3 sentence atmospheric description.

        Args:
            location_name: The location's display name.
            beats: Comma-separated atmospheric cues (e.g. "ruined, foggy, dawn").
        """
        user = f"Location: {location_name}\nAtmospheric cues: {beats}"
        return await self._provider.complete(
            [
                {"role": "system", "content": _LOCATION_SYSTEM},
                {"role": "user", "content": user},
            ]
        )
