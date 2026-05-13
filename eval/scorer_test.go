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
