"""Tests for the interactive combat controller, driven by scripted input."""

from collections.abc import Iterable

from src.content import Encounter, get_encounter
from src.core.combat import CombatContext, CombatOutcome
from src.core.persistence import EventStore
from src.core.temporal import COUNTER_STOP_COST, ArchetypeCounterPolicy
from src.play import build_combat
from src.states.combat_cli import PROMPT_COMMAND, PROMPT_COUNTER, CombatCLI
from src.ui.console import ConsoleRenderer
from tests.fixtures.script_fixtures import Screen, Script


def _run(
    encounter_id: str, lines: Iterable[str], then: str = "q"
) -> tuple[CombatOutcome | None, Screen, Script, CombatContext]:
    """Play one encounter from a script and return everything observable."""
    encounter: Encounter = get_encounter(encounter_id)
    combat = build_combat(encounter, encounter.seed, EventStore(":memory:"))
    screen, script = Screen(), Script(lines, then=then)
    cli = CombatCLI(combat, ConsoleRenderer(write=screen), read_input=script)
    return cli.run(title=encounter.title, intro=encounter.intro), screen, script, combat


def test_attacking_every_turn_wins_the_first_fight() -> None:
    outcome, screen, _, combat = _run("sundial", [], then="a")

    assert outcome is CombatOutcome.VICTORY
    assert "VICTORY" in screen.text
    assert "The Sundial Courtyard" in screen.lines[1]
    assert combat.is_over


def test_quit_abandons_the_fight() -> None:
    outcome, screen, _, combat = _run("sundial", ["q"])

    assert outcome is None
    assert "Abandoned." in screen.text
    assert not combat.is_over


def test_malformed_input_reprompts_without_spending_the_turn() -> None:
    _, screen, script, combat = _run("sundial", ["", "zzz", "7", "?", "s", "q"])

    assert "Unknown command 'zzz'" in screen.text
    assert "No enemy 7. Choose 1-1." in screen.text
    assert "Echo Cast" in screen.text
    assert script.prompts.count(PROMPT_COMMAND) == 6
    assert combat.round_number == 1
    assert combat.enemies[0].hp == combat.enemies[0].max_hp


def test_defeated_target_is_refused_and_numbering_is_stable() -> None:
    encounter = get_encounter("crossroads")
    combat = build_combat(encounter, encounter.seed, EventStore(":memory:"))
    screen = Screen()
    answers: list[str] = []

    def read(prompt: str) -> str:
        first_dead = not combat.enemies[0].is_alive
        if first_dead and "1" in answers[-1:] and "already defeated" in screen.text:
            answers.append("q")
        else:
            answers.append("1")
        return answers[-1]

    CombatCLI(combat, ConsoleRenderer(write=screen), read_input=read).run()

    assert "Timeworn Raider is already defeated." in screen.text
    assert "1) Timeworn Raider defeated" in screen.text
    assert "2) Hollow Raider" in screen.text
    assert combat.enemies[1].is_alive


def test_boost_needs_points_and_a_valid_amount() -> None:
    _, screen, _, _ = _run("sundial", ["b", "9", "b", "", "b", "1", "q"])

    assert "Enter a number from 1 to 1." in screen.text
    assert "Kael attacks Clockwork Sentry" in screen.text


def test_boost_with_no_points_is_refused() -> None:
    encounter = get_encounter("sundial")
    combat = build_combat(encounter, encounter.seed, EventStore(":memory:"))
    screen = Screen()
    asked: list[str] = []

    def read(prompt: str) -> str:
        asked.append(prompt)
        if len(asked) == 1:
            combat.player.boost_points = 0
            return "b"
        return "q"

    CombatCLI(combat, ConsoleRenderer(write=screen), read_input=read).run()

    assert "No Boost Points yet" in screen.text


def test_boost_asks_for_a_target_when_there_are_several() -> None:
    _, screen, script, combat = _run("crossroads", ["b", "1", "2", "q"])

    assert any(p.strip().startswith("Target") for p in script.prompts)
    assert combat.enemies[1].hp < combat.enemies[1].max_hp
    assert combat.enemies[0].hp == combat.enemies[0].max_hp


def test_rewind_returns_to_the_start_of_the_players_last_turn_and_keeps_the_turn() -> None:
    _, screen, script, combat = _run("gate", ["d", "r", "1", "q"])

    assert "Time folds back to the start of your turn 1 ago" in screen.text
    rewind_prompt = next(i for i, p in enumerate(script.prompts) if "Rewind" in p)
    assert script.prompts[rewind_prompt + 1] == PROMPT_COMMAND
    # Back at the start of round 1, before the defend and everything after it.
    assert combat.round_number == 1
    assert combat._total_turns == 0
    assert combat.player.hp == combat.player.max_hp
    assert combat.player.boost_points == 1
    assert not combat.player.is_defending
    # Round 1's single charge, less the 1 the rewind cost.
    assert combat.player.temporal_charge == 0


def test_rewind_without_charge_or_a_turn_to_undo_is_refused() -> None:
    encounter = get_encounter("sundial")
    combat = build_combat(encounter, encounter.seed, EventStore(":memory:"))
    screen = Screen()
    asked: list[str] = []

    def read(prompt: str) -> str:
        asked.append(prompt)
        step = len(asked)
        if step == 1:
            combat.player.temporal_charge = 0
            return "r"
        if step == 2:
            combat.player.temporal_charge = 1
            return "r"
        if step == 3:
            return "d"
        if step == 4:
            return "r"
        return "5" if step == 5 else "q"

    CombatCLI(combat, ConsoleRenderer(write=screen), read_input=read).run()

    assert "No temporal charge" in screen.text
    assert "Nothing to rewind" in screen.text
    assert "Enter a number from 1 to 1." in screen.text


def test_player_is_offered_a_counter_and_can_take_it() -> None:
    encounter = get_encounter("gate")
    screen = Screen()
    answers: list[str] = []
    asked: list[str] = []
    box: list[CombatCLI] = []
    combat = build_combat(
        encounter,
        encounter.seed,
        EventStore(":memory:"),
        counter_policy=ArchetypeCounterPolicy(ask_player=lambda a: box[0].ask_counter(a)),
    )
    mage = combat.enemies[0]

    def read(prompt: str) -> str:
        asked.append(prompt)
        if prompt == PROMPT_COUNTER.format(cost=COUNTER_STOP_COST):
            answers.append("y")
            return "y"
        if answers:
            return "q"
        # Hold 3 charge and leave her hurt with 1: she will try to rewind.
        combat.player.temporal_charge = 3
        mage.hp = mage.max_hp // 4
        mage.temporal_charge = 1
        return "d"

    box.append(CombatCLI(combat, ConsoleRenderer(write=screen), read_input=read))
    box[0].run()

    assert answers == ["y"]
    assert "The Chronomancer begins to rewind time." in screen.text
    assert "rewinds time!" not in screen.text
    assert combat._current_branch_id == 0
    assert combat.player.temporal_charge <= 1


def test_declining_the_counter_lets_the_cast_through() -> None:
    encounter = get_encounter("gate")
    screen = Screen()
    box: list[CombatCLI] = []
    combat = build_combat(
        encounter,
        encounter.seed,
        EventStore(":memory:"),
        counter_policy=ArchetypeCounterPolicy(ask_player=lambda a: box[0].ask_counter(a)),
    )
    mage = combat.enemies[0]
    seen = {"counter": False}

    def read(prompt: str) -> str:
        if "Counter-Stop" in prompt:
            seen["counter"] = True
            return ""
        if seen["counter"]:
            return "q"
        combat.player.temporal_charge = 3
        mage.hp = mage.max_hp // 4
        mage.temporal_charge = 1
        return "d"

    box.append(CombatCLI(combat, ConsoleRenderer(write=screen), read_input=read))
    box[0].run()

    assert seen["counter"]
    assert "The Chronomancer rewinds time!" in screen.text
    assert combat._current_branch_id == 1


def test_echo_cast_spends_the_turn_and_the_echo_acts_later() -> None:
    _, screen, _, combat = _run("sundial", ["d", "e", "1", "d", "q"])

    assert "casts Echo" in screen.text
    assert "Kael's echo" in screen.text
    assert combat.round_number == 4


def test_echo_with_bad_window_or_no_charge_is_refused() -> None:
    _, screen, _, combat = _run("sundial", ["e", "9", "e", "1", "q"])

    assert "Enter a number from 1 to 3." in screen.text
    assert combat.round_number == 1


def test_designated_enemy_counters_an_echo_at_the_gate() -> None:
    _, screen, _, combat = _run("gate", ["d", "d", "e", "1", "q"])
    chronomancer = combat.enemies[0]

    assert "Counter-Stop" in screen.text
    assert "Kael's echo" not in screen.text
    # Round 4 has started: each side has regenerated 1 since the counter.
    assert chronomancer.temporal_charge == 1
    assert combat.player.temporal_charge == 2


def test_designated_enemy_counters_a_rewind_and_the_turn_stays() -> None:
    _, screen, script, combat = _run("gate", ["d", "d", "r", "1", "q"])

    assert "Counter-Stopped by The Chronomancer — 1 charge spent for nothing." in screen.text
    assert combat.enemies[0].temporal_charge == 0
    assert script.prompts[-1] == PROMPT_COMMAND


def test_flee_ends_the_fight_or_spends_the_turn() -> None:
    outcome, screen, _, _ = _run("sundial", [], then="f")

    assert outcome in {CombatOutcome.FLED, CombatOutcome.DEFEAT}
    assert "ESCAPED" in screen.text or "DEFEAT" in screen.text
