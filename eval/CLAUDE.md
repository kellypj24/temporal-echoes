# eval/ — Claude Context

The only Go package in the project. Uses Go 1.26 + `gopkg.in/yaml.v3` —
standard library otherwise.

## Layout (one package, flat)

| File | Responsibility |
|------|---------------|
| `main.go` | CLI flags, semaphore, goroutine dispatch, WaitGroup |
| `runner.go` | Subprocess call to `scripts/eval_runner.py` + JSON decode |
| `scorer.go` | Score `RunResult` against fixture `Expect` block |
| `scorer_test.go` | Unit tests for scorer |
| `fixtures.go` | YAML loading (globs `eval/fixtures/*.yaml`) |
| `report.go` | `tabwriter` summary + ANSI color helpers |
| `fixtures/*.yaml` | Per-category fixture files (combat, npc, location, …) |

## Subprocess contract

The Go runner shells out to:

```
uv run python scripts/eval_runner.py --input-json '{"category":"…","params":{…}}'
```

The Python script must emit **one** JSON object to stdout matching the
`RunResult` struct (`{ok, result, error}`). `ok=false` is treated as a
fixture-level failure, not a Go-side error, so the script always exits
with valid JSON even on exceptions. Don't change this contract without
updating both sides.

## Routing in the mock provider

`src/ai/providers/mock.py` routes on the **user-payload markers** the
narrator emits (`Combat event:`, `NPC:`, `Location:`, `Quest:`). Adding a
new narrator method means adding a matching marker route in `mock.py`.
Don't route on system-prompt phrasing — it cross-matches (e.g. a location
prompt that says "No dialogue" will fire the NPC route).

## Concurrency

Buffered `chan struct{}` semaphore — acquire before spawning Python,
release in `defer`. Results slice is pre-allocated; each goroutine
writes to its own index. Fail-fast flag is the only shared mutable
state and is guarded by a single `sync.Mutex`. Do not introduce more
mutex-protected shared state without a strong reason.

## Adding fixtures

1. Pick the right `eval/fixtures/<category>.yaml` (or create a new one).
2. Each entry needs `id`, `category`, `input` (kwargs forwarded to the
   narrator method), and an `expect` block.
3. Run `just eval` (mock, fast) to confirm the fixture exercises the
   route you intended.
4. Once the AI DM has real implementations, run `just eval-real -filter <id>`
   against the configured provider to validate behavior.

## CI

The `eval-go` GitHub Actions job runs `go vet`, `go test`, and a smoke
run of the full harness against `TEMPORAL_LLM_PROVIDER=mock`. The smoke
run is what catches drift between fixture YAML, mock routes, and the
narrator surface. Adding a new fixture without updating mock routes
will surface there.
