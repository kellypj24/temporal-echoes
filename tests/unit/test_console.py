"""Tests for the terminal renderer."""

import ast
from pathlib import Path

from src.content import get_encounter
from src.ui import console
from src.ui.console import ConsoleRenderer
from tests.fixtures.script_fixtures import Screen


def test_status_shows_every_combatant_and_resource() -> None:
    screen = Screen()
    player, enemies = get_encounter("crossroads").build(player_hp=300)
    player.boost_points = 2
    player.temporal_charge = 1

    ConsoleRenderer(write=screen).status(player, enemies)

    assert "Kael" in screen.text
    assert "300/600" in screen.text
    assert "●●○○○" in screen.text
    assert "◆◇◇" in screen.text
    assert "1) Timeworn Raider" in screen.text
    assert "2) Hollow Raider" in screen.text


def test_defeated_enemy_keeps_its_number() -> None:
    screen = Screen()
    player, enemies = get_encounter("crossroads").build()
    enemies[0].hp = 0

    ConsoleRenderer(write=screen).status(player, enemies)

    assert "1) Timeworn Raider defeated" in screen.text
    assert "2) Hollow Raider" in screen.text


def test_colour_is_off_by_default_and_on_when_asked() -> None:
    plain, coloured = Screen(), Screen()
    ConsoleRenderer(write=plain).error("nope")
    ConsoleRenderer(write=coloured, color=True).error("nope")

    assert "\033[" not in plain.text
    assert "\033[" in coloured.text
    assert "nope" in coloured.text


def test_title_wraps_intro_to_width() -> None:
    screen = Screen()
    ConsoleRenderer(write=screen, width=40).title("T", "word " * 40)
    assert max(len(line) for line in screen.lines) <= 40


def test_outcome_and_notice_and_menu_render_their_text() -> None:
    screen = Screen()
    renderer = ConsoleRenderer(write=screen)
    renderer.outcome("VICTORY", "detail")
    renderer.notice("heads up")
    renderer.menu((("a", "attack"), ("q", "quit")))
    renderer.log(["one", "two"])
    renderer.blank()
    renderer.line("raw")

    for expected in (
        "VICTORY",
        "detail",
        "heads up",
        "[a] attack",
        "[q] quit",
        "one",
        "two",
        "raw",
    ):
        assert expected in screen.text


def test_renderer_imports_no_game_rules() -> None:
    tree = ast.parse(Path(console.__file__).read_text())
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not {m for m in modules if m.startswith(("src.core", "src.states"))}


def test_board_shows_enemy_charge_and_who_is_defending() -> None:
    screen = Screen()
    player, enemies = get_encounter("crossroads").build()
    enemies[0].temporal_charge = 2
    enemies[0].is_defending = True
    player.is_defending = True

    ConsoleRenderer(write=screen).status(player, enemies)

    first, second = (line for line in screen.lines if "Raider" in line)
    assert "TC ◆◆◇" in first and first.rstrip().endswith("DEF")
    assert "TC ◇◇◇" in second and "DEF" not in second
    assert next(line for line in screen.lines if "Kael" in line).rstrip().endswith("DEF")
