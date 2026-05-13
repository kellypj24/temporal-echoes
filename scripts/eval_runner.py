"""Single-fixture eval runner — the subprocess target invoked by the Go harness.

Two modes:

1. ``--input-json '{"category": "...", "params": {...}}'`` — used by the Go
   runner. Reads the input on the command line, dispatches to the right
   ``Narrator`` call, and emits the structured result to stdout as JSON.

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
import sys
import traceback
from pathlib import Path
from typing import Any

import yaml

from src.ai.narrator import Narrator
from src.ai.providers import get_provider

CATEGORY_DISPATCH: dict[str, str] = {
    "combat": "narrate_combat",
    "npc": "npc_dialogue",
    "location": "describe_location",
}


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
    method_name = CATEGORY_DISPATCH.get(category)
    if method_name is None:
        raise ValueError(
            f"Unknown category {category!r}. "
            f"Valid: {', '.join(sorted(CATEGORY_DISPATCH))}"
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
