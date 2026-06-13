# Provider head-to-head: direct Ollama vs LangChain

**Question:** does routing the AI-DM through LangChain (`langchain-ollama`'s
`ChatOllama`) improve output quality or add overhead versus the hand-rolled
`OllamaProvider`?

**Setup:** identical model (`qwen2.5:3b`), identical `Narrator`, identical eval
fixtures, identical deterministic checks. The only variable is the
`LLMProvider` implementation, selected via `TEMPORAL_LLM_PROVIDER`. Model warmed
before timing. Structured calls run at temperature 0.0; `describe_location`
(free text) at 0.7.

Reproduce:

```bash
LLM_MODEL=qwen2.5:3b TEMPORAL_LLM_PROVIDER=ollama   just eval-real
LLM_MODEL=qwen2.5:3b TEMPORAL_LLM_PROVIDER=langchain just eval-real
```

## Results (5 fixtures)

| Metric            | Direct `OllamaProvider` | `LangChainProvider` |
|-------------------|-------------------------|---------------------|
| Checks passed     | 14 / 16                 | 14 / 16             |
| Errors            | 0                       | 0                   |
| Latency p50       | 1.21s                   | 1.41s               |
| Latency p95       | 1.91s                   | 1.84s               |
| Total (5 fixtures)| 7.17s                   | 7.58s               |

## Conclusion

**No meaningful difference.** Same pass rate; latency within ~5% (noise). Both
providers ultimately drive Ollama's `format`-based constrained decoding for
structured output — `ChatOllama.with_structured_output(method="json_schema")`
wraps the *same* lever the direct provider calls — so LangChain cannot beat it
and does not measurably tax it.

The per-fixture pass/fail differences between the two columns are run-to-run
**non-determinism** (N=5, free-text `describe_location` at temp 0.7, and a
previously free-string `mood`), not a quality gap.

### What actually moved the numbers (not the framework)

- **`mood` was a free `str`.** Models emitted off-list moods that failed the
  `mood_one_of` checks. Fixed by constraining `NPCLine.mood` to the `Mood`
  enum (`src/ai/narrator.py`), so constrained decoding *cannot* produce an
  invalid mood. This helps **both** providers equally.
- **N=5 is too small to optimize against.** Grow fixtures for stable signal.

### Takeaway

For this workload the leverage is in **schemas + prompts + eval volume**, not
the orchestration framework. `LangChainProvider` is retained as a reference
implementation (it satisfies the same `LLMProvider` Protocol and swaps in via
`TEMPORAL_LLM_PROVIDER=langchain`) for familiarity and future comparison, not
because it improves the local-model path today.

> Scope note: this evaluates LangChain as a *provider wrapper*. It says nothing
> about LangGraph for *agentic DM orchestration*, which is a separate question
> (stateful multi-step control flow) that this single-call narration workload
> does not exercise.
