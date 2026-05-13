"""Tests for scripts/eval_runner.py — both subprocess JSON mode and fixture mode."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts" / "eval_runner.py"


def _run(
    args: list[str], extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    import os

    env = os.environ.copy()
    env["TEMPORAL_LLM_PROVIDER"] = "mock"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(RUNNER), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )


class TestJSONMode:
    def test_combat_fixture_returns_ok(self) -> None:
        payload = json.dumps(
            {
                "category": "combat",
                "params": {
                    "actor": "Aria",
                    "action": "slashes",
                    "target": "goblin",
                    "damage": 12,
                },
            }
        )
        result = _run(["--input-json", payload])
        assert result.returncode == 0, result.stderr
        out = json.loads(result.stdout)
        assert out["ok"] is True
        assert "prose" in out["result"]
        assert "intensity" in out["result"]

    def test_npc_fixture_returns_ok(self) -> None:
        payload = json.dumps(
            {
                "category": "npc",
                "params": {
                    "npc_name": "Eldra",
                    "situation": "player approaches the shrine",
                },
            }
        )
        result = _run(["--input-json", payload])
        out = json.loads(result.stdout)
        assert out["ok"] is True
        assert "line" in out["result"]
        assert "mood" in out["result"]

    def test_location_fixture_returns_text(self) -> None:
        payload = json.dumps(
            {
                "category": "location",
                "params": {
                    "location_name": "Hollow Bell Temple",
                    "beats": "ruined, foggy, dawn",
                },
            }
        )
        result = _run(["--input-json", payload])
        out = json.loads(result.stdout)
        assert out["ok"] is True
        assert isinstance(out["result"], str)
        assert len(out["result"]) > 0

    def test_unknown_category_returns_error_envelope(self) -> None:
        payload = json.dumps({"category": "bogus", "params": {}})
        result = _run(["--input-json", payload])
        # Non-zero exit, but stdout is still a JSON error envelope
        assert result.returncode == 1
        out = json.loads(result.stdout)
        assert out["ok"] is False
        assert "Unknown category" in out["error"]


class TestFixtureMode:
    def test_loads_and_runs_combat_fixture(self, tmp_path: Path) -> None:
        fixture_file = tmp_path / "combat.yaml"
        fixture_file.write_text(
            """
fixtures:
  - id: basic_strike
    category: combat
    input:
      actor: Aria
      action: slashes
      target: goblin
      damage: 12
    expect:
      intensity_min: 1
""".strip()
        )
        result = _run(["--fixture", str(fixture_file), "--id", "basic_strike"])
        assert result.returncode == 0, result.stderr
        assert "basic_strike" in result.stdout
        assert "Result:" in result.stdout

    def test_missing_id_exits_nonzero(self, tmp_path: Path) -> None:
        fixture_file = tmp_path / "combat.yaml"
        fixture_file.write_text("fixtures: []")
        result = _run(["--fixture", str(fixture_file), "--id", "missing"])
        assert result.returncode != 0

    def test_fixture_without_id_arg_is_error(self, tmp_path: Path) -> None:
        fixture_file = tmp_path / "combat.yaml"
        fixture_file.write_text("fixtures: []")
        result = _run(["--fixture", str(fixture_file)])
        assert result.returncode != 0


class TestCLI:
    def test_requires_input_json_or_fixture(self) -> None:
        result = _run([])
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "error" in result.stderr.lower()


@pytest.fixture(scope="module", autouse=True)
def _ensure_runner_exists() -> None:
    assert RUNNER.exists(), f"Runner script missing at {RUNNER}"
