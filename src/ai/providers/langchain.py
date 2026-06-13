"""LangChain-backed LLM provider (Ollama via `langchain-ollama`).

Implements the same `LLMProvider` Protocol as the direct `OllamaProvider`,
but routes through LangChain's `ChatOllama`. This exists to A/B LangChain
against the hand-rolled provider on the eval harness — same fixtures, same
model, swap via `TEMPORAL_LLM_PROVIDER=langchain`.

`complete_structured()` uses `ChatOllama.with_structured_output(schema)`, which
(method="json_schema") drives Ollama's native constrained decoding — the same
`format=<json schema>` lever the direct provider calls. So this is a fair test
of LangChain's ergonomics/overhead, not of a different inference capability.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, ValidationError

from src.ai.providers.base import (
    LLMConnectionError,
    LLMError,
    LLMTimeoutError,
    LLMValidationError,
)
from src.core.config import GameConfig

try:  # httpx ships with the ollama client; map its connection errors when present
    import httpx

    _CONN_ERRORS: tuple[type[Exception], ...] = (
        ConnectionError,
        OSError,
        httpx.ConnectError,
        httpx.ConnectTimeout,
    )
except ImportError:  # pragma: no cover - httpx is always present via langchain-ollama
    _CONN_ERRORS = (ConnectionError, OSError)


class LangChainProvider:
    """LangChain `ChatOllama` provider satisfying the `LLMProvider` Protocol.

    Args:
        host: Ollama server URL. Defaults to `GameConfig.ollama_host`
            (prefixed with `http://` if missing).
        model: Default model name. Defaults to `GameConfig.llm_model`.
        timeout: Request timeout in seconds. Defaults to `GameConfig.llm_timeout`.
        temperature: Sampling temperature for free-form `complete()`. Defaults
            to `GameConfig.llm_temperature`. Structured calls force 0.0 to match
            the direct provider.
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

    def _build_chat(self, temperature: float, **kwargs: Any) -> Any:
        """Construct a `ChatOllama` for one call (cheap; carries no session)."""
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=kwargs.get("model", self.model),
            base_url=self.host,
            temperature=temperature,
            num_predict=kwargs.get("num_predict", 1024),
        )

    @staticmethod
    def _to_lc_messages(messages: list[dict[str, str]]) -> list[Any]:
        """Convert OpenAI-style `{role, content}` dicts to LangChain messages."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        converted: list[Any] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                converted.append(SystemMessage(content=content))
            elif role == "assistant":
                converted.append(AIMessage(content=content))
            else:
                converted.append(HumanMessage(content=content))
        return converted

    @staticmethod
    def _coerce_text(content: Any) -> str:
        """Flatten LangChain message content (str or content-block list) to text."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            ]
            return "".join(parts)
        return str(content)

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate a free-form text completion via `ChatOllama.ainvoke`."""
        temperature = kwargs.pop("temperature", self.temperature)
        llm = self._build_chat(temperature, **kwargs)
        lc_messages = self._to_lc_messages(messages)
        try:
            response = await asyncio.wait_for(llm.ainvoke(lc_messages), timeout=self.timeout)
        except (asyncio.TimeoutError, TimeoutError) as exc:
            raise LLMTimeoutError(f"LangChain/Ollama timed out after {self.timeout}s") from exc
        except _CONN_ERRORS as exc:
            raise LLMConnectionError(f"LangChain/Ollama unreachable at {self.host}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - normalize to the provider error hierarchy
            raise LLMError(f"LangChain completion failed: {exc}") from exc
        return self._coerce_text(response.content)

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        """Generate a schema-validated completion via `with_structured_output`.

        Uses LangChain's `method="json_schema"` path, which drives Ollama's
        `format=<json schema>` constrained decoding — the same lever the direct
        `OllamaProvider` uses.
        """
        temperature = kwargs.pop("temperature", 0.0)
        llm = self._build_chat(temperature, **kwargs)
        structured = llm.with_structured_output(schema)
        lc_messages = self._to_lc_messages(messages)
        try:
            result = await asyncio.wait_for(
                structured.ainvoke(lc_messages), timeout=self.timeout
            )
        except (asyncio.TimeoutError, TimeoutError) as exc:
            raise LLMTimeoutError(f"LangChain/Ollama timed out after {self.timeout}s") from exc
        except ValidationError as exc:
            raise LLMValidationError(f"Response did not match {schema.__name__}: {exc}") from exc
        except _CONN_ERRORS as exc:
            raise LLMConnectionError(f"LangChain/Ollama unreachable at {self.host}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - normalize to the provider error hierarchy
            raise LLMError(f"LangChain structured completion failed: {exc}") from exc

        if isinstance(result, schema):
            return result
        # with_structured_output should already return a schema instance; coerce defensively.
        try:
            return schema.model_validate(result)
        except ValidationError as exc:
            raise LLMValidationError(
                f"LangChain returned an object that failed {schema.__name__} validation: {exc}"
            ) from exc
