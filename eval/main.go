// eval runs Temporal Echoes AI-DM eval fixtures concurrently and scores each
// against its expected properties. Exits with code 1 if any fixture fails
// (CI-friendly). Fixtures live in eval/fixtures/*.yaml; each fixture is
// dispatched to scripts/eval_runner.py as a subprocess.
//
// Usage:
//
//	go run ./eval [flags]
//	go run ./eval -filter combat
//	go run ./eval -concurrency 6 -timeout 60s
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

func main() {
	filter := flag.String("filter", "", "Only run fixtures whose ID contains this substring")
	category := flag.String("category", "", "Only run fixtures in this category (combat, npc, location)")
	concurrency := flag.Int("concurrency", runtime.NumCPU(), "Max fixtures to run in parallel")
	timeout := flag.Duration("timeout", 90*time.Second, "Per-fixture timeout")
	failFast := flag.Bool("fail-fast", false, "Stop after first failing fixture")
	root := flag.String("root", "", "Project root directory (default: current working directory)")
	fixturesDir := flag.String("fixtures", "eval/fixtures", "Path to fixtures directory (relative to root)")
	flag.Parse()

	projectRoot := *root
	if projectRoot == "" {
		wd, err := os.Getwd()
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: %v\n", err)
			os.Exit(1)
		}
		projectRoot = wd
	}

	dir := filepath.Join(projectRoot, *fixturesDir)
	fixtures, err := loadFixturesDir(dir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error loading fixtures from %s: %v\n", dir, err)
		os.Exit(1)
	}
	if len(fixtures) == 0 {
		fmt.Fprintf(os.Stderr, "no fixtures found in %s\n", dir)
		os.Exit(1)
	}

	fixtures = applyFilters(fixtures, *filter, *category)
	if len(fixtures) == 0 {
		fmt.Fprintln(os.Stderr, "no fixtures match the given filters")
		os.Exit(1)
	}

	fmt.Printf("Running %d fixture(s) with concurrency=%d timeout=%s\n\n",
		len(fixtures), *concurrency, *timeout)

	results := dispatch(projectRoot, fixtures, *concurrency, *timeout, *failFast)

	fmt.Println()
	printSummary(results)

	for _, r := range results {
		if !r.Passed {
			os.Exit(1)
		}
	}
}

func applyFilters(in []Fixture, idSubstr, cat string) []Fixture {
	var out []Fixture
	for _, fx := range in {
		if idSubstr != "" && !strings.Contains(fx.ID, idSubstr) {
			continue
		}
		if cat != "" && fx.Category != cat {
			continue
		}
		out = append(out, fx)
	}
	return out
}

// dispatch runs fixtures in parallel under a semaphore. The results slice is
// pre-allocated so each goroutine writes to its own index — no mutex needed
// for the slice itself. The fail-fast flag is the only shared state and is
// guarded by mu.
func dispatch(
	projectRoot string,
	fixtures []Fixture,
	concurrency int,
	timeout time.Duration,
	failFast bool,
) []FixtureResult {
	sem := make(chan struct{}, concurrency)
	results := make([]FixtureResult, len(fixtures))
	var (
		mu      sync.Mutex
		stopped bool
		wg      sync.WaitGroup
	)

	for i, fx := range fixtures {
		wg.Add(1)
		go func(idx int, fixture Fixture) {
			defer wg.Done()

			mu.Lock()
			if stopped {
				mu.Unlock()
				results[idx] = FixtureResult{
					ID:       fixture.ID,
					Category: fixture.Category,
					Error:    "skipped (fail-fast)",
				}
				return
			}
			mu.Unlock()

			sem <- struct{}{}
			defer func() { <-sem }()

			ctx, cancel := context.WithTimeout(context.Background(), timeout)
			defer cancel()

			fmt.Printf("  → %s\n", dim(fixture.ID))
			t0 := time.Now()
			run, runErr := runFixture(ctx, projectRoot, fixture)
			elapsed := time.Since(t0)

			fr := FixtureResult{
				ID:       fixture.ID,
				Category: fixture.Category,
				Elapsed:  elapsed,
				Run:      run,
			}
			if runErr != nil {
				fr.Error = runErr.Error()
				fr.Passed = false
			} else {
				fr.Checks = score(run, fixture.Expect)
				fr.Passed = true
				for _, c := range fr.Checks {
					if !c.Passed {
						fr.Passed = false
						break
					}
				}
			}

			icon := green("✓")
			if !fr.Passed {
				icon = red("✗")
			}
			fmt.Printf("  %s %s (%.2fs)\n", icon, dim(fixture.ID), elapsed.Seconds())

			results[idx] = fr

			if failFast && !fr.Passed {
				mu.Lock()
				stopped = true
				mu.Unlock()
				fmt.Println(yellow("  --fail-fast: stopping after first failure"))
			}
		}(i, fx)
	}

	wg.Wait()

	var final []FixtureResult
	for _, r := range results {
		if r.ID != "" {
			final = append(final, r)
		}
	}
	return final
}
