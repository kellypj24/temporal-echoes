"""Mock LLM provider for fast harness iteration and deterministic tests.

The mock returns canned responses keyed off the message content so the eval
harness can run end-to-end in seconds against `TEMPORAL_LLM_PROVIDER=mock`
without touching Ollama or the Anthropic API.

Routing strategy
----------------
The provider inspects the concatenated message content and the requested
schema (for structured calls) and looks for the first matching trigger in
the registered route table. Each route is a `(predicate, response)` pair.

Default routes cover the seed fixture categories (combat narration, NPC
dialogue, location description). Tests and harness code can register
additional routes via `register_route()` for one-off scenarios.
"""

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from src.ai.providers.base import LLMValidationError

Predicate = Callable[[str, type[BaseModel] | None], bool]
Response = str | dict[str, Any]


def _contains(*needles: str) -> Predicate:
    """Predicate: prompt contains any of the given case-insensitive substrings."""
    lower_needles = [n.lower() for n in needles]

    def _check(prompt: str, _schema: type[BaseModel] | None) -> bool:
        return any(n in prompt.lower() for n in lower_needles)

    return _check


# Default routes anchor on the *user-payload markers* the Narrator emits
# (`Combat event:`, `NPC:`, `Location:`) so routing is unambiguous regardless
# of what system prompt phrasing happens to contain. Match is case-insensitive
# substring on the concatenated message content.
_DEFAULT_ROUTES: list[tuple[Predicate, Response]] = [
    # Combat narration — structured: {"prose": str, "intensity": int}
    (
        _contains("Combat event:"),
        {
            "prose": "Steel rings against steel as the blow lands with thunderous force.",
            "intensity": 7,
        },
    ),
    # NPC dialogue — structured: {"line": str, "mood": str}
    (
        _contains("NPC:"),
        {
            "line": "Traveler — the path ahead is darker than it seems. Tread carefully.",
            "mood": "wary",
        },
    ),
    # Location description — free text
    (
        _contains("Location:"),
        "Moss-laden stone arches loom overhead, their faces worn smooth by centuries of pilgrim hands.",
    ),
    # Quest hook — structured (kept for forward compatibility with Phase 4 fixtures)
    (
        _contains("Quest:", "Objective:"),
        {
            "title": "The Hollow Bell",
            "summary": "A village elder seeks the bell that once warded the eastern pass.",
        },
    ),
]


class MockProvider:
    """Deterministic LLM provider for harness iteration and tests.

    Args:
        routes: Optional override of the default routing table.
        default_text: Returned by `complete()` when no route matches.
        default_structured: Returned by `complete_structured()` when no route
            matches; the dict is validated against the requested schema.
    """

    def __init__(
        self,
        routes: list[tuple[Predicate, Response]] | None = None,
        default_text: str = "[mock] no route matched",
        default_structured: dict[str, Any] | None = None,
    ) -> None:
        self._routes: list[tuple[Predicate, Response]] = list(routes or _DEFAULT_ROUTES)
        self._default_text = default_text
        self._default_structured = default_structured or {}
        self.calls: list[dict[str, Any]] = []

    def register_route(self, predicate: Predicate, response: Response) -> None:
        """Prepend a route so it takes priority over the defaults."""
        self._routes.insert(0, (predicate, response))

    def _flatten(self, messages: list[dict[str, str]]) -> str:
        return "\n".join(m.get("content", "") for m in messages)

    def _match(self, prompt: str, schema: type[BaseModel] | None) -> Response | None:
        for predicate, response in self._routes:
            if predicate(prompt, schema):
                return response
        return None

    async def complete(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        prompt = self._flatten(messages)
        self.calls.append({"kind": "complete", "prompt": prompt, "kwargs": kwargs})

        match = self._match(prompt, None)
        if match is None:
            return self._default_text
        if isinstance(match, str):
            return match
        return json.dumps(match)

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        prompt = self._flatten(messages)
        self.calls.append(
            {
                "kind": "complete_structured",
                "prompt": prompt,
                "schema": schema.__name__,
                "kwargs": kwargs,
            }
        )

        match = self._match(prompt, schema)
        payload = match if isinstance(match, dict) else self._default_structured

        try:
            return schema.model_validate(payload)
        except Exception as exc:
            raise LLMValidationError(
                f"Mock payload could not be validated as {schema.__name__}: {exc}\n"
                f"Payload: {payload}"
            ) from exc
