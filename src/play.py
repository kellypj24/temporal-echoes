"""
Command-line entry point for the terminal game.

Composition root only: it builds the event store, an encounter's entities
and the combat context, then hands control to `CombatCLI`. No rules and no
formatting live here beyond carrying wounds from one fight to the next.
"""

import argparse
import os
import sys
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from src.content import Encounter, get_encounter, list_encounters
from src.core.combat import CombatContext, CombatOutcome
from src.core.persistence import EventStore
from src.core.temporal import DesignatedCounterPolicy
from src.states.combat_cli import CombatCLI
from src.ui.console import ConsoleRenderer

EXIT_OK = 0
EXIT_USAGE = 2


@dataclass(frozen=True)
class PlayResult:
    """
    How one encounter ended.

    Attributes:
        encounter_id: The encounter that was played.
        outcome: The final outcome, or None if the player quit.
        player_hp: The player's HP when the fight ended.
        player_max_hp: The player's maximum HP in that fight.
    """

    encounter_id: str
    outcome: CombatOutcome | None
    player_hp: int
    player_max_hp: int

    @property
    def hp_missing(self) -> int:
        """Return how much HP the player was short of full at the end."""
        return self.player_max_hp - self.player_hp


def build_combat(
    encounter: Encounter,
    seed: int,
    event_store: EventStore,
    player_hp: int | None = None,
) -> CombatContext:
    """
    Instantiate an encounter as a live combat.

    Args:
        encounter: The authored encounter to play.
        seed: RNG seed; the same seed and inputs replay the same fight.
        event_store: Store that receives every combat event.
        player_hp: The player's starting HP; None means full.

    Returns:
        A `CombatContext` ready for its first round.
    """
    player, enemies = encounter.build(player_hp=player_hp)
    run_id = uuid.uuid4().hex[:8]
    return CombatContext(
        combat_id=f"{encounter.id}-{run_id}",
        seed=seed,
        player=player,
        enemies=enemies,
        event_store=event_store,
        session_id=f"play-{run_id}",
        timeline_id="main",
        counter_policy=DesignatedCounterPolicy(encounter.countering_enemy_ids),
    )


def play(
    encounter: Encounter,
    seed: int | None = None,
    event_store: EventStore | None = None,
    read_input: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
    color: bool = False,
    player_hp: int | None = None,
) -> PlayResult:
    """
    Play one encounter to its conclusion.

    Args:
        encounter: The authored encounter to play.
        seed: RNG seed for the fight; None uses the encounter's own.
        event_store: Store for the event log; None uses an in-memory one.
        read_input: Prompt -> response function; tests inject a script.
        write: Line sink for all output.
        color: Emit ANSI colour codes.
        player_hp: The player's starting HP; None means full.

    Returns:
        How the fight ended.
    """
    store = event_store if event_store is not None else EventStore(":memory:")
    combat = build_combat(
        encounter,
        encounter.seed if seed is None else seed,
        store,
        player_hp=player_hp,
    )
    cli = CombatCLI(combat, ConsoleRenderer(write=write, color=color), read_input=read_input)
    outcome = cli.run(title=encounter.title, intro=encounter.intro)
    return PlayResult(
        encounter_id=encounter.id,
        outcome=outcome,
        player_hp=combat.player.hp,
        player_max_hp=combat.player.max_hp,
    )


def play_sequence(
    encounters: Sequence[Encounter],
    seed: int | None = None,
    event_store: EventStore | None = None,
    read_input: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
    color: bool = False,
) -> list[PlayResult]:
    """
    Play encounters in order, carrying wounds, until one is not won.

    Each later fight starts with the player's HP reduced by the HP missing
    at the end of the previous one, to no less than 1.

    Args:
        encounters: Encounters in play order.
        seed: RNG seed applied to every fight; None uses each encounter's own.
        event_store: Store for the event log; None uses an in-memory one.
        read_input: Prompt -> response function; tests inject a script.
        write: Line sink for all output.
        color: Emit ANSI colour codes.

    Returns:
        One result per encounter started, in order.
    """
    store = event_store if event_store is not None else EventStore(":memory:")
    results: list[PlayResult] = []
    missing = 0
    for encounter in encounters:
        result = play(
            encounter,
            seed=seed,
            event_store=store,
            read_input=read_input,
            write=write,
            color=color,
            player_hp=encounter.player.max_hp - missing,
        )
        results.append(result)
        if result.outcome is not CombatOutcome.VICTORY:
            break
        missing = result.hp_missing
    return results


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        argv: Argument list, or None for `sys.argv[1:]`.

    Returns:
        The parsed namespace.
    """
    parser = argparse.ArgumentParser(
        prog="just play",
        description="Play Temporal Echoes in the terminal.",
    )
    parser.add_argument(
        "encounter",
        nargs="?",
        help="play only this encounter (default: all, in order, wounds carried)",
    )
    parser.add_argument("--list", action="store_true", help="list encounters and exit")
    parser.add_argument("--seed", type=int, help="override the RNG seed of every fight")
    parser.add_argument(
        "--db", default=":memory:", help="SQLite file for the event log (default: in-memory)"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the command-line game.

    Args:
        argv: Argument list, or None for `sys.argv[1:]`.

    Returns:
        Process exit code.
    """
    args = _parse_args(argv)

    if args.list:
        for enc in list_encounters():
            print(f"{enc.id:12} {enc.title}")
        return EXIT_OK

    if args.encounter is None:
        encounters = list_encounters()
    else:
        try:
            encounters = [get_encounter(args.encounter)]
        except KeyError as exc:
            print(exc.args[0], file=sys.stderr)
            return EXIT_USAGE

    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    try:
        play_sequence(
            encounters,
            seed=args.seed,
            event_store=EventStore(args.db),
            read_input=input,  # looked up at call time, so a caller can replace it
            color=color,
        )
    except (EOFError, KeyboardInterrupt):
        print()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
