package main

import (
	"testing"
)

func intPtr(i int) *int { return &i }

func TestScore_ErrorEnvelope(t *testing.T) {
	run := &RunResult{OK: false, Error: "boom"}
	checks := score(run, Expect{})
	if len(checks) != 1 || checks[0].Passed {
		t.Fatalf("expected single failing 'ran' check, got %#v", checks)
	}
	if checks[0].Detail != "boom" {
		t.Errorf("expected detail 'boom', got %q", checks[0].Detail)
	}
}

func TestScore_StringResult_ContainsAny(t *testing.T) {
	run := &RunResult{OK: true, Result: "Moss-laden stone arches loom overhead."}
	expect := Expect{ContainsAny: []string{"stone", "river"}}
	checks := score(run, expect)
	if !allPassed(checks) {
		t.Errorf("expected all passes, got %#v", checks)
	}
}

func TestScore_StringResult_ContainsAny_Fails(t *testing.T) {
	run := &RunResult{OK: true, Result: "Generic description."}
	expect := Expect{ContainsAny: []string{"stone", "river"}}
	checks := score(run, expect)
	if allPassed(checks) {
		t.Errorf("expected contains_any to fail, got %#v", checks)
	}
}

func TestScore_StringResult_MinLength(t *testing.T) {
	run := &RunResult{OK: true, Result: "short"}
	checks := score(run, Expect{MinLength: 10})
	if allPassed(checks) {
		t.Errorf("expected min_length to fail")
	}
}

func TestScore_StringResult_MaxLength(t *testing.T) {
	run := &RunResult{OK: true, Result: "this is a long description that exceeds the limit"}
	checks := score(run, Expect{MaxLength: 10})
	if allPassed(checks) {
		t.Errorf("expected max_length to fail")
	}
}

func TestScore_StructuredResult_CombatProse(t *testing.T) {
	run := &RunResult{
		OK: true,
		Result: map[string]interface{}{
			"prose":     "Steel rings against steel.",
			"intensity": float64(7),
		},
	}
	expect := Expect{
		ContainsAny:  []string{"steel"},
		IntensityMin: intPtr(1),
		IntensityMax: intPtr(10),
	}
	checks := score(run, expect)
	if !allPassed(checks) {
		t.Errorf("expected all passes, got %#v", checks)
	}
}

func TestScore_IntensityOutOfRange(t *testing.T) {
	run := &RunResult{
		OK: true,
		Result: map[string]interface{}{
			"prose":     "x",
			"intensity": float64(11),
		},
	}
	expect := Expect{IntensityMax: intPtr(10)}
	checks := score(run, expect)
	if allPassed(checks) {
		t.Errorf("expected intensity check to fail")
	}
}

func TestScore_IntensityMissing(t *testing.T) {
	run := &RunResult{
		OK:     true,
		Result: map[string]interface{}{"prose": "x"},
	}
	expect := Expect{IntensityMin: intPtr(1)}
	checks := score(run, expect)
	if allPassed(checks) {
		t.Errorf("expected intensity check to fail (field missing)")
	}
}

func TestScore_StructuredResult_NPCMood(t *testing.T) {
	run := &RunResult{
		OK: true,
		Result: map[string]interface{}{
			"line": "The path is dark.",
			"mood": "wary",
		},
	}
	expect := Expect{
		MoodOneOf:   []string{"wary", "calm", "fearful"},
		MinLength:   5,
		ContainsAny: []string{"path"},
	}
	checks := score(run, expect)
	if !allPassed(checks) {
		t.Errorf("expected all passes, got %#v", checks)
	}
}

func TestScore_NPCMoodNotInList(t *testing.T) {
	run := &RunResult{
		OK: true,
		Result: map[string]interface{}{
			"line": "x",
			"mood": "ecstatic",
		},
	}
	expect := Expect{MoodOneOf: []string{"wary", "calm"}}
	checks := score(run, expect)
	if allPassed(checks) {
		t.Errorf("expected mood_one_of check to fail")
	}
}

func TestScore_ZeroExpect_ProducesOnlyRanCheck(t *testing.T) {
	run := &RunResult{OK: true, Result: "anything"}
	checks := score(run, Expect{})
	if len(checks) != 1 {
		t.Errorf("expected single 'ran' check, got %d", len(checks))
	}
	if !checks[0].Passed {
		t.Errorf("expected ran=true")
	}
}

func TestScore_NilRun(t *testing.T) {
	checks := score(nil, Expect{})
	if len(checks) != 1 || checks[0].Passed {
		t.Errorf("expected single failing check for nil run")
	}
}

func allPassed(checks []CheckResult) bool {
	for _, c := range checks {
		if !c.Passed {
			return false
		}
	}
	return true
}

func boolPtr(b bool) *bool { return &b }

func chronoResult(fields map[string]interface{}) *RunResult {
	return &RunResult{OK: true, Result: fields}
}

func TestScore_Decision(t *testing.T) {
	run := chronoResult(map[string]interface{}{"decision": "rewind"})
	if !allPassed(score(run, Expect{DecisionEquals: "rewind"})) {
		t.Errorf("expected decision_equals to pass")
	}
	if allPassed(score(run, Expect{DecisionEquals: "echo_cast"})) {
		t.Errorf("expected decision_equals to fail on a different decision")
	}
	if allPassed(score(chronoResult(map[string]interface{}{}), Expect{DecisionEquals: "rewind"})) {
		t.Errorf("expected decision_equals to fail when the field is missing")
	}
}

func TestScore_EchoTurns(t *testing.T) {
	run := chronoResult(map[string]interface{}{"decision": "echo_cast", "echo_turns": float64(3)})
	if !allPassed(score(run, Expect{EchoTurnsEquals: intPtr(3)})) {
		t.Errorf("expected echo_turns_equals to pass")
	}
	if allPassed(score(run, Expect{EchoTurnsEquals: intPtr(1)})) {
		t.Errorf("expected echo_turns_equals to fail on a different window")
	}
	missing := chronoResult(map[string]interface{}{"decision": "rewind"})
	if allPassed(score(missing, Expect{EchoTurnsEquals: intPtr(1)})) {
		t.Errorf("expected echo_turns_equals to fail when the field is missing")
	}
}

func TestScore_WantsCounter(t *testing.T) {
	run := chronoResult(map[string]interface{}{"wants_counter": true})
	if !allPassed(score(run, Expect{WantsCounter: boolPtr(true)})) {
		t.Errorf("expected wants_counter to pass")
	}
	if allPassed(score(run, Expect{WantsCounter: boolPtr(false)})) {
		t.Errorf("expected wants_counter false to fail against true")
	}
	if allPassed(score(chronoResult(map[string]interface{}{}), Expect{WantsCounter: boolPtr(false)})) {
		t.Errorf("expected wants_counter to fail when the field is missing")
	}
}

func TestScore_Shares(t *testing.T) {
	run := chronoResult(map[string]interface{}{
		"decision":     "random_mix",
		"distribution": map[string]interface{}{"attack": 0.46, "defend": 0.34, "ability": 0.20},
	})
	within := Expect{
		ShareMin: map[string]float64{"attack": 0.35},
		ShareMax: map[string]float64{"attack": 0.55, "rewind": 0.0},
	}
	if !allPassed(score(run, within)) {
		t.Errorf("expected shares within bounds to pass")
	}
	if allPassed(score(run, Expect{ShareMin: map[string]float64{"defend": 0.5}})) {
		t.Errorf("expected share_min to fail")
	}
	if allPassed(score(run, Expect{ShareMax: map[string]float64{"ability": 0.1}})) {
		t.Errorf("expected share_max to fail")
	}
	noDist := chronoResult(map[string]interface{}{"decision": "rewind"})
	if allPassed(score(noDist, Expect{ShareMin: map[string]float64{"attack": 0.1}})) {
		t.Errorf("expected shares to fail without a distribution")
	}
}
