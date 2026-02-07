# AI Module Rules

Ollama LLM integration for AI Dungeon Master capabilities.

## Rules
- ALL calls to Ollama MUST be async (`async/await`). Never use synchronous `requests`.
- Always set timeouts (5s default). Never wait indefinitely.
- Every AI feature MUST have a rule-based fallback function.
- Validate token count before sending (4096 hard limit).
- Cache responses where context is identical.
- Use Pydantic models to validate JSON responses from LLM.
- Use specific exception types: `OllamaConnectionError`, `OllamaTimeoutError`, `OllamaModelNotFoundError`.
- Retry with exponential backoff (3x max) for connection/timeout errors. Don't retry model-not-found.
- Use connection pooling via `aiohttp.TCPConnector`.
- Clean up sessions properly (context managers).

## Graceful Degradation
1. Full AI generation with context
2. Timeout/error -> retry once with truncated context
3. Second failure -> rule-based fallback
4. Never block the game loop

## Reference
Full patterns: `.cursor/rules/ai-worker.mdc`, `.cursor/rules/ai-integration-supervisor.mdc`
