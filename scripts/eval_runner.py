"""Single-fixture eval runner — the subprocess target invoked by the Go harness.

Two modes:

1. ``--input-json '{"category": "...", "params": {...}}'`` — used by the Go
   runner. Reads the input on the command line, dispatches to the right
   ``Narrator`` call (or, for the ``chronomancer`` category, to the game's
   own rules with no provider), and emits the result to stdout as JSON.

2. ``--fixture eval/fixtures/<file>.yaml --id <fixture-id>`` — convenience for
   ``just ask-fixture <id>``. Loads the named fixture from YAML, runs it, and
   pretty-prints the result with the fixture's expectations alongside.

Provider selection follows the standard ``TEMPORAL_LLM_PROVIDER`` env var
(``ollama`` / ``anthropic`` / ``mock``).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import traceback
from pathlib import Path
from typing import Any

import yaml

from src.ai.narrator import Narrator
from src.ai.providers import get_provider
from src.core.ai import ChronomancerAI, CombatState
from src.core.temporal import TemporalAnnouncement
from src.entities import Enemy, Player

# Categories decided by game rules alone: no Narrator, no provider.
RULE_CATEGORIES = frozenset({"chronomancer"})
CHRONOMANCER_TRIALS = 200

CATEGORY_DISPATCH: dict[str, str] = {
    "combat": "narrate_combat",
    "npc": "npc_dialogue",
    "location": "describe_location",
}


def run_chronomancer(params: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the Chronomancer's rules for one described situation.

    Args:
        params: ``seed``, ``own_hp_pct``, ``own_charge``, ``player_charge``,
            ``living_enemies`` (including the Chronomancer), ``history_len``,
            ``prior_rewinds``, ``total_turns``, ``echo_active`` and an
            optional ``announced_ability`` ("rewind" or "echo_cast"). All
            have defaults describing a healthy Chronomancer mid-fight.

    Returns:
        ``decision`` ("rewind", "echo_cast" or "random_mix"), ``echo_turns``
        (when echoing), ``wants_counter`` (when a cast is announced) and
        ``distribution``, the share of each mundane action over
        ``CHRONOMANCER_TRIALS`` seeded draws.
    """
    seed = int(params.get("seed", 0))
    hp_pct = int(params.get("own_hp_pct", 100))
    mage = Enemy(
        id="chronomancer",
        name="Chronomancer",
        level=10,
        hp=hp_pct * 10,
        max_hp=1000,
        attack=30,
        defense=40,
        speed=30,
        shield_points=3,
        max_shield_points=3,
        archetype="chronomancer",
        temporal_charge=int(params.get("own_charge", 0)),
    )
    allies = [
        Enemy(
            id=f"ally_{i}",
            name="Acolyte",
            level=5,
            hp=100,
            max_hp=100,
            attack=20,
            defense=20,
            speed=10,
            shield_points=1,
            max_shield_points=1,
        )
        for i in range(int(params.get("living_enemies", 1)) - 1)
    ]
    player = Player(
        id="player_1",
        name="Hero",
        level=10,
        hp=500,
        max_hp=500,
        attack=50,
        defense=30,
        speed=40,
        temporal_charge=int(params.get("player_charge", 0)),
    )
    state = CombatState(
        player=player,
        enemies=[mage, *allies],
        round_number=int(params.get("round_number", 3)),
        total_turns=int(params.get("total_turns", 6)),
        rewind_counts={mage.id: int(params.get("prior_rewinds", 0))},
        history_lengths={mage.id: int(params.get("history_len", 1))},
        enemy_echo_active=bool(params.get("echo_active", False)),
    )

    action = ChronomancerAI(mage, random.Random(seed)).select_action(state)
    temporal = action.action_type in {"rewind", "echo_cast"}
    result: dict[str, Any] = {"decision": action.action_type if temporal else "random_mix"}
    if action.action_type == "echo_cast":
        result["echo_turns"] = action.echo_turns

    announced = params.get("announced_ability")
    if announced is not None:
        announcement = TemporalAnnouncement(
            ability=str(announced),
            caster_id=player.id,
            magnitude=1,
            turn_number=state.total_turns,
        )
        result["wants_counter"] = ChronomancerAI(mage, random.Random(seed)).wants_counter_stop(
            announcement, state
        )

    if not temporal:
        sampler = ChronomancerAI(mage, random.Random(seed))
        counts: dict[str, int] = {}
        for _ in range(CHRONOMANCER_TRIALS):
            kind = sampler.select_action(state).action_type
            counts[kind] = counts.get(kind, 0) + 1
        result["distribution"] = {
            kind: count / CHRONOMANCER_TRIALS for kind, count in sorted(counts.items())
        }
    return result


async def run_one(category: str, params: dict[str, Any]) -> Any:
    """Dispatch a single fixture to the matching Narrator method.

    Args:
        category: One of CATEGORY_DISPATCH's keys.
        params: Keyword arguments forwarded to the narrator method.

    Returns:
        The narrator's return value (Pydantic model or str).

    Raises:
        ValueError: ``category`` is not a known dispatch target.
    """
    if category == "chronomancer":
        return run_chronomancer(params)

    method_name = CATEGORY_DISPATCH.get(category)
    if method_name is None:
        raise ValueError(
            f"Unknown category {category!r}. "
            f"Valid: {', '.join(sorted({*CATEGORY_DISPATCH, *RULE_CATEGORIES}))}"
        )

    narrator = Narrator(get_provider())
    method = getattr(narrator, method_name)
    return await method(**params)


def _serialize(result: Any) -> Any:
    """Convert a narrator result into JSON-safe primitives."""
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


def _load_fixture(fixture_path: Path, fixture_id: str) -> dict[str, Any]:
    """Load a single fixture by id from a YAML file.

    Args:
        fixture_path: Path to a fixture YAML file.
        fixture_id: ``id`` field of the fixture to load.

    Returns:
        The fixture dict (with ``id``, ``category``, ``input``, ``expect``).

    Raises:
        ValueError: No fixture with that id is present in the file.
    """
    data = yaml.safe_load(fixture_path.read_text())
    for fixture in data.get("fixtures", []):
        if fixture.get("id") == fixture_id:
            return fixture  # type: ignore[no-any-return]
    raise ValueError(f"Fixture {fixture_id!r} not found in {fixture_path}")


def _run_json_mode(input_json: str) -> int:
    """Mode 1: parse stdin/CLI JSON, run, emit one-line JSON to stdout."""
    try:
        payload = json.loads(input_json)
        category = payload["category"]
        params = payload.get("params", {})
        result = asyncio.run(run_one(category, params))
        sys.stdout.write(
            json.dumps(
                {"ok": True, "result": _serialize(result)},
                separators=(",", ":"),
            )
        )
        sys.stdout.write("\n")
        return 0
    except Exception as exc:
        sys.stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "trace": traceback.format_exc(),
                }
            )
        )
        sys.stdout.write("\n")
        return 1


def _run_fixture_mode(fixture_path: Path, fixture_id: str) -> int:
    """Mode 2: load fixture from YAML, run it, pretty-print."""
    fixture = _load_fixture(fixture_path, fixture_id)
    category = fixture["category"]
    params = fixture.get("input", {})

    print(f"Fixture: {fixture_id} ({category})")
    print(f"Input:   {json.dumps(params, indent=2)}")
    print()

    result = asyncio.run(run_one(category, params))
    print("Result:")
    print(json.dumps(_serialize(result), indent=2))

    expect = fixture.get("expect")
    if expect:
        print()
        print("Expectations:")
        print(json.dumps(expect, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--input-json",
        help='JSON: {"category": "combat", "params": {...}} — used by Go runner',
    )
    group.add_argument(
        "--fixture",
        type=Path,
        help="Path to a fixture YAML file (pair with --id)",
    )
    parser.add_argument(
        "--id",
        help="Fixture id within --fixture (required with --fixture)",
    )

    args = parser.parse_args(argv)

    if args.input_json is not None:
        return _run_json_mode(args.input_json)

    if args.id is None:
        parser.error("--fixture requires --id")
    return _run_fixture_mode(args.fixture, args.id)


if __name__ == "__main__":
    sys.exit(main())
