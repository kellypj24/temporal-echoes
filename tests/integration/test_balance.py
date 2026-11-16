"""
Balance targets for the authored sequence, held by scripted players.

Seeds are fixed, so these are deterministic. `just balance` prints the same
measurements over more seeds.
"""

from statistics import mean

import pytest

from src.content import list_encounters
from tests.fixtures.autopilot import (
    FightReport,
    Policy,
    fighter,
    masher,
    play_campaign,
    tactician,
)

SEEDS = range(40)


@pytest.fixture(scope="module")
def campaigns() -> dict[str, list[list[FightReport]]]:
    encounters = list_encounters()
    policies: list[Policy] = [masher, fighter, tactician]
    return {
        policy.__name__: [play_campaign(encounters, policy, seed) for seed in SEEDS]
        for policy in policies
    }


def _cleared(runs: list[list[FightReport]]) -> float:
    return mean(1.0 if len(r) == 3 and r[-1].won else 0.0 for r in runs)


def test_attacking_every_turn_wins_the_first_two_fights(
    campaigns: dict[str, list[list[FightReport]]],
) -> None:
    runs = campaigns["masher"]
    assert all(len(r) == 3 for r in runs)


def test_attacking_every_turn_loses_the_gate(
    campaigns: dict[str, list[list[FightReport]]],
) -> None:
    assert _cleared(campaigns["masher"]) <= 0.10


def test_a_player_using_every_tool_usually_clears_the_sequence(
    campaigns: dict[str, list[list[FightReport]]],
) -> None:
    assert _cleared(campaigns["tactician"]) >= 0.70


def test_time_abilities_decide_the_gate(
    campaigns: dict[str, list[list[FightReport]]],
) -> None:
    without, with_time = _cleared(campaigns["fighter"]), _cleared(campaigns["tactician"])
    assert without <= 0.50
    assert with_time - without >= 0.25


def test_the_gate_lasts_eight_to_twelve_rounds_for_a_competent_player(
    campaigns: dict[str, list[list[FightReport]]],
) -> None:
    gate_rounds = [r[-1].rounds for r in campaigns["tactician"] if len(r) == 3]
    assert 8 <= mean(gate_rounds) <= 12


def test_scripted_fights_end(campaigns: dict[str, list[list[FightReport]]]) -> None:
    for runs in campaigns.values():
        assert all(report.outcome is not None for run in runs for report in run)
