package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"gopkg.in/yaml.v3"
)

// Expect captures the assertions a fixture makes about the narrator's output.
// All fields are optional — a zero value means "do not check".
type Expect struct {
	// String/text checks (apply to both string results and structured prose/line fields).
	ContainsAny []string `yaml:"contains_any"`
	MinLength   int      `yaml:"min_length"`
	MaxLength   int      `yaml:"max_length"`

	// Numeric range (combat fixtures: intensity).
	IntensityMin *int `yaml:"intensity_min"`
	IntensityMax *int `yaml:"intensity_max"`

	// String enum (npc fixtures: mood).
	MoodOneOf []string `yaml:"mood_one_of"`
}

// Fixture is one evaluation case loaded from YAML.
type Fixture struct {
	ID       string                 `yaml:"id"`
	Category string                 `yaml:"category"`
	Input    map[string]interface{} `yaml:"input"`
	Expect   Expect                 `yaml:"expect"`
}

type fixtureFile struct {
	Fixtures []Fixture `yaml:"fixtures"`
}

// loadFixturesDir reads every *.yaml file under dir, concatenates the
// `fixtures:` lists, and returns them in stable ID order.
func loadFixturesDir(dir string) ([]Fixture, error) {
	matches, err := filepath.Glob(filepath.Join(dir, "*.yaml"))
	if err != nil {
		return nil, fmt.Errorf("glob fixtures dir: %w", err)
	}
	sort.Strings(matches)

	var out []Fixture
	for _, path := range matches {
		fxs, err := loadFixtureFile(path)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", filepath.Base(path), err)
		}
		out = append(out, fxs...)
	}

	sort.SliceStable(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

func loadFixtureFile(path string) ([]Fixture, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read: %w", err)
	}
	var f fixtureFile
	if err := yaml.Unmarshal(b, &f); err != nil {
		return nil, fmt.Errorf("parse: %w", err)
	}
	return f.Fixtures, nil
}
