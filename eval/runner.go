package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

// RunResult is what the Python eval_runner.py prints to stdout.
type RunResult struct {
	OK     bool        `json:"ok"`
	Result interface{} `json:"result"`
	Error  string      `json:"error"`
}

// FixtureResult holds the scored outcome for a single fixture.
type FixtureResult struct {
	ID       string
	Category string
	Passed   bool
	Checks   []CheckResult
	Error    string
	Elapsed  time.Duration
	Run      *RunResult
}

// runFixture invokes the Python single-question runner as a subprocess and
// returns the parsed envelope. A non-zero exit is treated as a fixture
// failure rather than a Go-side error if the script still emitted a valid
// JSON envelope (the Python side wraps exceptions in {"ok": false, ...}).
func runFixture(ctx context.Context, projectRoot string, fixture Fixture) (*RunResult, error) {
	inputJSON, err := json.Marshal(map[string]interface{}{
		"category": fixture.Category,
		"params":   fixture.Input,
	})
	if err != nil {
		return nil, fmt.Errorf("marshal input: %w", err)
	}

	cmd := exec.CommandContext(ctx,
		"uv", "run", "python", "scripts/eval_runner.py",
		"--input-json", string(inputJSON),
	)
	cmd.Dir = projectRoot

	out, runErr := cmd.Output()
	if runErr != nil {
		// Script may still have emitted a JSON envelope on stdout even with
		// a non-zero exit (the Python error path does this). Try to parse it.
		if ee, ok := runErr.(*exec.ExitError); ok && len(out) > 0 {
			var result RunResult
			if jsonErr := json.Unmarshal(out, &result); jsonErr == nil {
				return &result, nil
			}
			stderr := strings.TrimSpace(string(ee.Stderr))
			if stderr != "" {
				return nil, fmt.Errorf("runner failed: %s", stderr)
			}
		}
		return nil, fmt.Errorf("runner failed: %w", runErr)
	}

	var result RunResult
	if err := json.Unmarshal(out, &result); err != nil {
		return nil, fmt.Errorf("parse runner output: %w", err)
	}
	return &result, nil
}
