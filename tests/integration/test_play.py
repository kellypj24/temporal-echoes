"""End-to-end tests for the terminal game entry point."""

import re

import pytest

from src.content import Encounter, EnemySpec, PlayerSpec, get_encounter, list_encounters
from src.core.combat import CombatOutcome
from src.core.events import EventTypes
from src.core.persistence import EventStore
from src.play import EXIT_OK, EXIT_USAGE, main, play, play_sequence
from tests.fixtures.script_fixtures import Screen, Script

_HOPELESS = Encounter(
    id="hopeless",
    title="Hopeless",
    intro="",
    seed=1,
    player=PlayerSpec(name="Kael", level=1, max_hp=10, attack=1, defense=1, speed=1),
    enemies=(
        EnemySpec(
            id="wall",
            name="Wall",
            level=50,
            max_hp=9999,
            attack=200,
            defense=200,
            speed=99,
            shield_points=9,
        ),
    ),
)


def test_scripted_attacks_win_one_encounter() -> None:
    screen = Screen()
    result = play(get_encounter("sundial"), read_input=Script([], then="a"), write=screen)

    assert result.outcome is CombatOutcome.VICTORY
    assert result.encounter_id == "sundial"
    assert 0 < result.player_hp <= result.player_max_hp
    assert "VICTORY" in screen.lines[-3]


def test_every_event_reaches_the_store() -> None:
    store = EventStore(":memory:")
    play(
        get_encounter("sundial"), event_store=store, read_input=Script([], then="a"), write=Screen()
    )

    types = [e.event_type for e in store.get_events_by_timeline("main")]
    assert types[0] == EventTypes.COMBAT_STARTED
    assert types[-1] == EventTypes.COMBAT_ENDED


def test_wounds_carry_into_the_next_fight() -> None:
    screen = Screen()
    first, second = list_encounters()[:2]
    results = play_sequence([first, second], read_input=Script([], then="a"), write=screen)

    assert [r.outcome for r in results] == [CombatOutcome.VICTORY, CombatOutcome.VICTORY]
    missing = results[0].hp_missing
    assert missing > 0
    start_hp = second.player.max_hp - missing
    assert any(f"{start_hp}/{second.player.max_hp}" in line for line in screen.lines)


def test_carried_wounds_never_start_a_fight_below_one_hp() -> None:
    screen = Screen()
    survivor = Encounter(
        id="pyrrhic",
        title="Pyrrhic",
        intro="",
        seed=3,
        player=PlayerSpec(name="Kael", level=1, max_hp=5000, attack=90, defense=5, speed=1),
        enemies=(
            EnemySpec(
                id="glass",
                name="Glass",
                level=1,
                max_hp=3000,
                attack=120,
                defense=1,
                speed=200,
                shield_points=9,
            ),
        ),
    )
    frail = Encounter(
        id="frail",
        title="Frail",
        intro="",
        seed=1,
        player=PlayerSpec(name="Kael", level=1, max_hp=10, attack=1, defense=1, speed=250),
        enemies=_HOPELESS.enemies,
    )
    results = play_sequence([survivor, frail], read_input=Script([], then="a"), write=screen)

    assert results[0].outcome is CombatOutcome.VICTORY
    assert results[0].hp_missing > frail.player.max_hp
    assert any(re.search(r"(?<!\d)1/10\b", line) for line in screen.lines)


def test_a_defeat_ends_the_sequence() -> None:
    screen = Screen()
    results = play_sequence(
        [_HOPELESS, get_encounter("sundial")], read_input=Script([], then="d"), write=screen
    )

    assert [r.outcome for r in results] == [CombatOutcome.DEFEAT]
    assert "The Sundial Courtyard" not in screen.text


def test_quitting_ends_the_sequence() -> None:
    results = play_sequence(list_encounters(), read_input=Script(["q"]), write=Screen())

    assert [r.outcome for r in results] == [None]


def test_same_seed_and_script_give_the_same_output() -> None:
    lines = ["d", "d", "d", "e", "1", "r", "1", "b", "2", "1"]
    runs = []
    for _ in range(2):
        screen = Screen()
        play(get_encounter("gate"), seed=42, read_input=Script(lines, then="a"), write=screen)
        runs.append(screen.lines)

    assert runs[0] == runs[1]
    assert any("Time folds back" in line for line in runs[0])
    assert any("casts Echo" in line or "Counter-Stop" in line for line in runs[0])


def test_a_different_seed_gives_a_different_fight() -> None:
    outputs = []
    for seed in (1, 2):
        screen = Screen()
        play(get_encounter("gate"), seed=seed, read_input=Script([], then="a"), write=screen)
        outputs.append(screen.lines)

    assert outputs[0] != outputs[1]


def test_list_prints_the_encounter_ids(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--list"]) == EXIT_OK
    out = capsys.readouterr().out
    assert [line.split()[0] for line in out.splitlines()] == ["sundial", "crossroads", "gate"]


def test_unknown_encounter_exits_with_usage_status(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["nowhere"]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert "sundial, crossroads, gate" in err


def test_main_plays_from_stdin_and_survives_end_of_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["a"])

    def read(prompt: str = "") -> str:
        try:
            return next(answers)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr("builtins.input", read)

    assert main(["sundial", "--seed", "5"]) == EXIT_OK
    assert "The Sundial Courtyard" in capsys.readouterr().out


def test_the_gate_boss_rewinds_and_the_fight_still_ends() -> None:
    screen = Screen()
    result = play(get_encounter("gate"), read_input=Script([], then="a"), write=screen)

    assert "The Chronomancer rewinds time!" in screen.text
    assert screen.text.count("The Chronomancer rewinds time!") <= 2
    assert result.outcome in {CombatOutcome.VICTORY, CombatOutcome.DEFEAT}
