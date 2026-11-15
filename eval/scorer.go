package main

import (
	"fmt"
	"sort"
	"strings"
)

// CheckResult is a single named assertion outcome.
type CheckResult struct {
	Name   string
	Passed bool
	Detail string
}

// score evaluates the fixture's Expect block against the narrator's result.
// The result envelope is the parsed Python {"ok", "result", "error"} payload.
func score(run *RunResult, expect Expect) []CheckResult {
	if run == nil {
		return []CheckResult{{Name: "ran", Passed: false, Detail: "no run result"}}
	}
	if !run.OK {
		return []CheckResult{{Name: "ran", Passed: false, Detail: run.Error}}
	}

	var checks []CheckResult
	checks = append(checks, CheckResult{Name: "ran", Passed: true})

	text, fields := extractTextAndFields(run.Result)

	// Text checks
	if len(expect.ContainsAny) > 0 {
		checks = append(checks, checkContainsAny(text, expect.ContainsAny))
	}
	if expect.MinLength > 0 {
		checks = append(checks, checkMinLength(text, expect.MinLength))
	}
	if expect.MaxLength > 0 {
		checks = append(checks, checkMaxLength(text, expect.MaxLength))
	}

	// Numeric checks (combat fixtures with `intensity` field)
	if expect.IntensityMin != nil || expect.IntensityMax != nil {
		checks = append(checks, checkIntensity(fields, expect.IntensityMin, expect.IntensityMax))
	}

	// Enum check (npc fixtures with `mood` field)
	if len(expect.MoodOneOf) > 0 {
		checks = append(checks, checkMoodOneOf(fields, expect.MoodOneOf))
	}

	// Rule decisions (chronomancer fixtures)
	if expect.DecisionEquals != "" {
		checks = append(checks, checkDecisionEquals(fields, expect.DecisionEquals))
	}
	if expect.EchoTurnsEquals != nil {
		checks = append(checks, checkEchoTurnsEquals(fields, *expect.EchoTurnsEquals))
	}
	if expect.WantsCounter != nil {
		checks = append(checks, checkWantsCounter(fields, *expect.WantsCounter))
	}
	if len(expect.ShareMin) > 0 || len(expect.ShareMax) > 0 {
		checks = append(checks, checkShares(fields, expect.ShareMin, expect.ShareMax))
	}

	return checks
}

// extractTextAndFields pulls the testable text out of the result regardless
// of whether the result is a bare string (location description) or a
// structured object (combat / npc).
func extractTextAndFields(result interface{}) (string, map[string]interface{}) {
	switch v := result.(type) {
	case string:
		return v, nil
	case map[string]interface{}:
		text := ""
		if prose, ok := v["prose"].(string); ok {
			text = prose
		} else if line, ok := v["line"].(string); ok {
			text = line
		}
		return text, v
	default:
		return "", nil
	}
}

func checkContainsAny(text string, needles []string) CheckResult {
	lower := strings.ToLower(text)
	for _, n := range needles {
		if strings.Contains(lower, strings.ToLower(n)) {
			return CheckResult{Name: "contains_any", Passed: true}
		}
	}
	return CheckResult{
		Name:   "contains_any",
		Passed: false,
		Detail: fmt.Sprintf("none of %v found in %q", needles, truncate(text, 60)),
	}
}

func checkMinLength(text string, n int) CheckResult {
	if len(text) >= n {
		return CheckResult{Name: "min_length", Passed: true}
	}
	return CheckResult{
		Name:   "min_length",
		Passed: false,
		Detail: fmt.Sprintf("got %d, want >= %d", len(text), n),
	}
}

func checkMaxLength(text string, n int) CheckResult {
	if len(text) <= n {
		return CheckResult{Name: "max_length", Passed: true}
	}
	return CheckResult{
		Name:   "max_length",
		Passed: false,
		Detail: fmt.Sprintf("got %d, want <= %d", len(text), n),
	}
}

func checkIntensity(fields map[string]interface{}, minV, maxV *int) CheckResult {
	raw, ok := fields["intensity"]
	if !ok {
		return CheckResult{Name: "intensity", Passed: false, Detail: "field missing"}
	}
	// JSON numbers come back as float64
	f, ok := raw.(float64)
	if !ok {
		return CheckResult{
			Name:   "intensity",
			Passed: false,
			Detail: fmt.Sprintf("not numeric: %v", raw),
		}
	}
	v := int(f)
	if minV != nil && v < *minV {
		return CheckResult{
			Name:   "intensity",
			Passed: false,
			Detail: fmt.Sprintf("got %d, want >= %d", v, *minV),
		}
	}
	if maxV != nil && v > *maxV {
		return CheckResult{
			Name:   "intensity",
			Passed: false,
			Detail: fmt.Sprintf("got %d, want <= %d", v, *maxV),
		}
	}
	return CheckResult{Name: "intensity", Passed: true}
}

func checkMoodOneOf(fields map[string]interface{}, allowed []string) CheckResult {
	raw, ok := fields["mood"]
	if !ok {
		return CheckResult{Name: "mood_one_of", Passed: false, Detail: "mood field missing"}
	}
	got, ok := raw.(string)
	if !ok {
		return CheckResult{
			Name:   "mood_one_of",
			Passed: false,
			Detail: fmt.Sprintf("mood not a string: %v", raw),
		}
	}
	lowerGot := strings.ToLower(got)
	for _, a := range allowed {
		if strings.ToLower(a) == lowerGot {
			return CheckResult{Name: "mood_one_of", Passed: true}
		}
	}
	return CheckResult{
		Name:   "mood_one_of",
		Passed: false,
		Detail: fmt.Sprintf("got %q, want one of %v", got, allowed),
	}
}

func checkDecisionEquals(fields map[string]interface{}, want string) CheckResult {
	got, ok := fields["decision"].(string)
	if !ok {
		return CheckResult{Name: "decision_equals", Passed: false, Detail: "decision field missing"}
	}
	if got != want {
		return CheckResult{
			Name:   "decision_equals",
			Passed: false,
			Detail: fmt.Sprintf("got %q, want %q", got, want),
		}
	}
	return CheckResult{Name: "decision_equals", Passed: true}
}

func checkEchoTurnsEquals(fields map[string]interface{}, want int) CheckResult {
	f, ok := fields["echo_turns"].(float64)
	if !ok {
		return CheckResult{Name: "echo_turns_equals", Passed: false, Detail: "echo_turns field missing"}
	}
	if int(f) != want {
		return CheckResult{
			Name:   "echo_turns_equals",
			Passed: false,
			Detail: fmt.Sprintf("got %d, want %d", int(f), want),
		}
	}
	return CheckResult{Name: "echo_turns_equals", Passed: true}
}

func checkWantsCounter(fields map[string]interface{}, want bool) CheckResult {
	got, ok := fields["wants_counter"].(bool)
	if !ok {
		return CheckResult{Name: "wants_counter", Passed: false, Detail: "wants_counter field missing"}
	}
	if got != want {
		return CheckResult{
			Name:   "wants_counter",
			Passed: false,
			Detail: fmt.Sprintf("got %t, want %t", got, want),
		}
	}
	return CheckResult{Name: "wants_counter", Passed: true}
}

// checkShares bounds the share of each named action in the result's
// `distribution`. An action absent from the distribution has share 0.
func checkShares(fields map[string]interface{}, minV, maxV map[string]float64) CheckResult {
	dist, ok := fields["distribution"].(map[string]interface{})
	if !ok {
		return CheckResult{Name: "shares", Passed: false, Detail: "distribution field missing"}
	}
	share := func(action string) float64 {
		f, _ := dist[action].(float64)
		return f
	}
	var problems []string
	for action, lo := range minV {
		if got := share(action); got < lo {
			problems = append(problems, fmt.Sprintf("%s got %.2f, want >= %.2f", action, got, lo))
		}
	}
	for action, hi := range maxV {
		if got := share(action); got > hi {
			problems = append(problems, fmt.Sprintf("%s got %.2f, want <= %.2f", action, got, hi))
		}
	}
	if len(problems) > 0 {
		sort.Strings(problems)
		return CheckResult{Name: "shares", Passed: false, Detail: strings.Join(problems, "; ")}
	}
	return CheckResult{Name: "shares", Passed: true}
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
