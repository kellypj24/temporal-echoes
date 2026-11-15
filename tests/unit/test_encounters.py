"""Tests for authored encounter specs."""

import pytest

from src.content import DEFAULT_ENCOUNTER_ID, get_encounter, list_encounters


def test_encounters_are_listed_in_play_order() -> None:
    assert [e.id for e in list_encounters()] == ["sundial", "crossroads", "gate"]
    assert DEFAULT_ENCOUNTER_ID == "sundial"


def test_unknown_encounter_names_the_known_ones() -> None:
    with pytest.raises(KeyError, match="sundial, crossroads, gate"):
        get_encounter("nowhere")


@pytest.mark.parametrize("encounter", list_encounters(), ids=lambda e: e.id)
def test_build_gives_fresh_full_strength_entities(encounter) -> None:  # type: ignore[no-untyped-def]
    player, enemies = encounter.build()
    again, _ = encounter.build()

    assert player is not again
    assert player.hp == player.max_hp == encounter.player.max_hp
    assert player.boost_points == 0
    assert player.temporal_charge == 0
    assert [e.id for e in enemies] == [s.id for s in encounter.enemies]
    assert all(e.hp == e.max_hp for e in enemies)
    assert len({e.id for e in enemies}) == len(enemies)


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(None, 520), (400, 400), (0, 1), (-50, 1), (9999, 520)],
)
def test_player_starting_hp_is_clamped(requested: int | None, expected: int) -> None:
    player, _ = get_encounter("sundial").build(player_hp=requested)
    assert player.hp == expected
    assert player.max_hp == 520


def test_only_the_gate_has_a_chronomancer() -> None:
    archetypes = {
        enemy.id: enemy.archetype
        for encounter in list_encounters()
        for enemy in encounter.enemies
        if enemy.archetype == "chronomancer"
    }
    assert archetypes == {"chronomancer": "chronomancer"}
