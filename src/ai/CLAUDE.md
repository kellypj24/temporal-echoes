# AI Module Rules

LLM integration for the AI Dungeon Master. The harness imports through a
pluggable provider abstraction — game code never knows which backend is active.

## Provider abstraction is sacred

Game/agent code imports **only** `LLMProvider` and `get_provider` from
`src.ai.providers`. Never import `OllamaProvider` or `AnthropicProvider`
directly. The active provider is selected via `TEMPORAL_LLM_PROVIDER`
(`ollama` | `anthropic`).

```python
# correct
from src.ai.providers import LLMProvider, get_provider

# NEVER in agent code
from src.ai.providers.anthropic import AnthropicProvider
```

## Structured output always

For any LLM call whose result will be consumed by code, use
`complete_structured()` with a Pydantic schema. Reserve `complete()` for
free-form DM narration that will be shown directly to the player.

## Error hierarchy

Never raise raw exceptions from provider code. Use the hierarchy in
`providers/base.py`:
- `LLMConnectionError` — provider unreachable
- `LLMTimeoutError` — no response within timeout
- `LLMValidationError` — response did not match schema
- `LLMError` — base class for anything else

## Rules
- ALL provider calls MUST be async (`async/await`). Never block the game loop.
- Always set timeouts (5s default for Ollama). Never wait indefinitely.
- Every AI feature MUST have a rule-based fallback function.
- Validate token count before sending (4096 hard limit).
- Cache responses where context is identical.
- Use Pydantic models to validate any structured LLM response.
- Use connection pooling via `aiohttp.TCPConnector` (Ollama).
- Clean up sessions properly on shutdown (`OllamaProvider.close()`).

## Graceful Degradation
1. Full AI generation with full context.
2. Timeout/error → retry once with truncated context.
3. Second failure → rule-based fallback.
4. Never block the game loop.

## Adding a provider
1. Create `src/ai/providers/<name>.py` implementing the `LLMProvider` protocol.
2. Add a `deferred` import + branch in `get_provider()` in `base.py`.
3. Add the env var to `.env.example` and `GameConfig`.
4. Add unit tests under `tests/unit/test_<name>_provider.py`.

## Reference
Full patterns: `.cursor/rules/ai-worker.mdc`, `.cursor/rules/ai-integration-supervisor.mdc`
