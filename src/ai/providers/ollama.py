"""Ollama provider — local LLM for offline play.

Uses aiohttp for async requests with connection pooling. Retries with
exponential backoff on connection or timeout errors.

Defaults are read from `GameConfig` so the provider stays in sync with
the rest of the game's configuration.
"""

import asyncio
import json
from typing import Any

import aiohttp
from pydantic import BaseModel

from src.ai.providers.base import (
    LLMConnectionError,
    LLMError,
    LLMTimeoutError,
    LLMValidationError,
)
from src.core.config import GameConfig

MAX_RETRIES = 3


class OllamaProvider:
    """Ollama LLM provider for local inference.

    Args:
        host: Ollama server URL (e.g. `http://localhost:11434`). Defaults
            to `GameConfig.ollama_host` (prefixed with `http://` if missing).
        model: Default model name. Defaults to `GameConfig.llm_model`.
        timeout: Request timeout in seconds. Defaults to `GameConfig.llm_timeout`.
        temperature: Sampling temperature. Defaults to `GameConfig.llm_temperature`.
    """

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        temperature: float | None = None,
    ) -> None:
        config = GameConfig()
        raw_host = host or config.ollama_host
        self.host = raw_host if raw_host.startswith("http") else f"http://{raw_host}"
        self.model = model or config.llm_model
        self.timeout = timeout if timeout is not None else config.llm_timeout
        self.temperature = temperature if temperature is not None else config.llm_temperature
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return a shared aiohttp session, creating it if needed."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=10)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def close(self) -> None:
        """Clean up the aiohttp session. Call on game shutdown."""
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def complete(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Generate a text completion via Ollama `/api/chat`.

        Args:
            messages: List of `{role, content}` dicts.
            **kwargs: Overrides — `model`, `temperature`, `num_predict`.

        Returns:
            Generated text content.
        """
        payload: dict[str, Any] = {
            "model": kwargs.pop("model", self.model),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.pop("temperature", self.temperature),
                "num_predict": kwargs.pop("num_predict", 1024),
                **kwargs,
            },
        }
        response = await self._post("/api/chat", payload)
        return str(response["message"]["content"])

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        """Generate a structured completion using Ollama's JSON mode.

        Injects the schema as a JSON instruction into the system prompt and
        passes the schema to Ollama's grammar-constrained generation. The
        response is then validated against the Pydantic model.

        Args:
            messages: List of `{role, content}` dicts.
            schema: Pydantic model class to parse the response into.
            **kwargs: Overrides — `model`, `temperature`, `num_predict`.

        Returns:
            Validated `schema` instance.

        Raises:
            LLMValidationError: Response JSON could not be parsed into `schema`.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        instruction = f"\n\nRespond with ONLY valid JSON matching this schema:\n{schema_json}"

        augmented = list(messages)
        if augmented and augmented[0]["role"] == "system":
            augmented[0] = {
                "role": "system",
                "content": augmented[0]["content"] + instruction,
            }
        else:
            augmented.insert(0, {"role": "system", "content": instruction})

        payload: dict[str, Any] = {
            "model": kwargs.pop("model", self.model),
            "messages": augmented,
            "stream": False,
            "format": schema.model_json_schema(),
            "options": {
                "temperature": kwargs.pop("temperature", 0.0),
                "num_predict": kwargs.pop("num_predict", 1024),
                **kwargs,
            },
        }
        response = await self._post("/api/chat", payload)
        raw = response["message"]["content"]

        try:
            return schema.model_validate_json(raw)
        except Exception as exc:
            raise LLMValidationError(
                f"Response could not be parsed into {schema.__name__}: {exc}\nRaw: {raw}"
            ) from exc

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to Ollama with retry, backoff, and typed error mapping.

        Args:
            path: API path (e.g. `/api/chat`).
            payload: JSON payload.

        Returns:
            Parsed JSON response.

        Raises:
            LLMConnectionError: Cannot reach Ollama after retries.
            LLMTimeoutError: Ollama did not respond within timeout.
            LLMError: Any other HTTP / unexpected failure.
        """
        session = await self._get_session()
        url = f"{self.host}{path}"
        last_exc: LLMError = LLMError("Unknown Ollama error")

        for attempt in range(MAX_RETRIES):
            try:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        raise LLMError(f"Ollama returned {resp.status}: {body}")
                    data: dict[str, Any] = await resp.json()
                    return data
            except aiohttp.ClientConnectorError as exc:
                last_exc = LLMConnectionError(f"Cannot reach Ollama at {self.host}: {exc}")
            except TimeoutError as exc:
                last_exc = LLMTimeoutError(f"Ollama timed out after {self.timeout}s: {exc}")
            except LLMError:
                raise
            except Exception as exc:
                last_exc = LLMError(f"Unexpected Ollama error: {exc}")

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2**attempt)

        raise last_exc
