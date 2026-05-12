"""Anthropic (Claude) provider — production-grade LLM for the AI DM.

Requires the `anthropic` package and `ANTHROPIC_API_KEY` in the environment.
Uses the Messages API for text and `tool_use` for structured output (more
reliable than JSON prompting for complex schemas).
"""

import os
from typing import Any

from pydantic import BaseModel

from src.ai.providers.base import LLMError, LLMValidationError

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_SYSTEM = "You are the AI Dungeon Master of a 16-bit RPG."


class AnthropicProvider:
    """Anthropic Claude provider using the Messages API.

    Args:
        api_key: Anthropic API key. Falls back to `ANTHROPIC_API_KEY` env var.
        model: Claude model ID. Falls back to `ANTHROPIC_MODEL` env var,
            then to `DEFAULT_MODEL`.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 30,
    ) -> None:
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise LLMError("ANTHROPIC_API_KEY not set. Export it or pass api_key explicitly.")
        self.api_key = resolved_key
        self.model = model or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
        self.timeout = timeout

    def _client(self) -> Any:
        """Lazy-import the Anthropic SDK so it is only required when used."""
        try:
            import anthropic

            return anthropic.AsyncAnthropic(api_key=self.api_key, timeout=self.timeout)
        except ImportError as exc:
            raise LLMError("anthropic package not installed. Run: poetry add anthropic") from exc

    @staticmethod
    def _split_system(
        messages: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]]]:
        """Extract the system message (if any) and return the rest unchanged."""
        system_parts: list[str] = []
        rest: list[dict[str, str]] = []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])
            else:
                rest.append(m)
        system = "\n\n".join(system_parts) if system_parts else DEFAULT_SYSTEM
        return system, rest

    async def complete(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Generate a text completion via the Claude Messages API.

        Args:
            messages: List of `{role, content}` dicts. Any `system` messages
                are extracted and concatenated into the API's `system` field.
            **kwargs: Overrides — `model`, `max_tokens`, `temperature`.

        Returns:
            Generated text content.

        Raises:
            LLMError: API call failed.
        """
        client = self._client()
        system, rest = self._split_system(messages)

        try:
            response = await client.messages.create(
                model=kwargs.pop("model", self.model),
                max_tokens=kwargs.pop("max_tokens", 1024),
                system=system,
                messages=rest,
                **kwargs,
            )
            return str(response.content[0].text)
        except Exception as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        """Generate structured output via Claude `tool_use`.

        The Pydantic schema is registered as a forced tool, which is more
        reliable than JSON prompting for complex schemas.

        Args:
            messages: List of `{role, content}` dicts.
            schema: Pydantic model class to parse the response into.
            **kwargs: Overrides — `model`, `max_tokens`.

        Returns:
            Validated `schema` instance.

        Raises:
            LLMValidationError: Response did not contain a tool_use block
                for the requested schema.
            LLMError: API call failed for any other reason.
        """
        client = self._client()
        system, rest = self._split_system(messages)

        tool = {
            "name": schema.__name__,
            "description": schema.__doc__ or f"Output conforming to {schema.__name__}",
            "input_schema": schema.model_json_schema(),
        }

        try:
            response = await client.messages.create(
                model=kwargs.pop("model", self.model),
                max_tokens=kwargs.pop("max_tokens", 1024),
                system=system,
                messages=rest,
                tools=[tool],
                tool_choice={"type": "tool", "name": schema.__name__},
                **kwargs,
            )
            tool_block = next(b for b in response.content if b.type == "tool_use")
            return schema.model_validate(tool_block.input)
        except StopIteration as exc:
            raise LLMValidationError("No tool_use block in Claude response") from exc
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"Anthropic structured completion error: {exc}") from exc
