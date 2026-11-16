"""Balance report: win rates of the scripted players over seeds.

Usage: ``just balance [seeds]``. For each scripted player it plays the full
sequence (wounds carried) and each encounter alone at full HP, and prints
how often it won, the HP it had left, and how many rounds a fight took.
"""

from __future__ import annotations

import sys
from statistics import mean

from src.content import list_encounters
from tests.fixtures.autopilot import (
    FightReport,
    Policy,
    fighter,
    masher,
    play_campaign,
    play_fight,
    tactician,
)


def _cell(reports: list[FightReport], of: int) -> str:
    wins = [r for r in reports if r.won]
    hp = f"{100 * mean(r.hp_left / r.max_hp for r in wins):3.0f}%" if wins else "  — "
    rounds = f"{mean(r.rounds for r in reports):4.1f}" if reports else "  — "
    return f"{len(wins):3d}/{of:<3d} hp {hp} rounds {rounds}"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    seeds = int(args[0]) if args else 100
    encounters = list_encounters()
    policies: list[Policy] = [masher, fighter, tactician]

    print(f"{seeds} seeds. Cell: wins/fights started, mean HP left in wins, mean rounds.\n")
    for title, runner in (("Sequence, wounds carried", True), ("Each fight alone, full HP", False)):
        print(title)
        for policy in policies:
            by_encounter: dict[str, list[FightReport]] = {e.id: [] for e in encounters}
            for seed in range(seeds):
                if runner:
                    for report in play_campaign(encounters, policy, seed):
                        by_encounter[report.encounter_id].append(report)
                else:
                    for encounter in encounters:
                        by_encounter[encounter.id].append(play_fight(encounter, policy, seed))
            cells = " | ".join(
                f"{e.id}: {_cell(by_encounter[e.id], seeds if not runner else len(by_encounter[e.id]))}"
                for e in encounters
            )
            print(f"  {policy.__name__:10} {cells}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
