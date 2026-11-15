"""
Terminal renderer for combat.

Pure presentation: this module reads entity state to draw it and never
decides anything about the fight. All output goes through an injected
`write` sink so tests can capture frames without touching stdout, and all
colour goes through `_paint`, which is a no-op when colour is disabled.
"""

from collections.abc import Callable, Iterable, Sequence
from typing import Final

from src.entities import Enemy, Player

_RESET: Final = "\033[0m"
_COLORS: Final[dict[str, str]] = {
    "dim": "\033[2m",
    "bold": "\033[1m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}

# Bar glyphs. Filled/empty pairs are the same width so bars never jitter.
_BAR_FILLED: Final = "█"
_BAR_EMPTY: Final = "░"
_PIP_FULL: Final = "●"
_PIP_EMPTY: Final = "○"
_CHARGE_FULL: Final = "◆"
_CHARGE_EMPTY: Final = "◇"
_SHIELD: Final = "▮"


class ConsoleRenderer:
    """
    Draws combat state as text.

    Attributes:
        _write: Output sink; receives one already-formatted line at a time.
        _color: Whether to emit ANSI colour codes.
        _width: Target width for rules and separators.
    """

    def __init__(
        self,
        write: Callable[[str], None] = print,
        color: bool = False,
        width: int = 68,
    ) -> None:
        """
        Initialise the renderer.

        Args:
            write: Line sink. Defaults to `print`; tests inject a collector.
            color: Emit ANSI colour codes. Callers should pass False when
                stdout is not a TTY or NO_COLOR is set.
            width: Character width used for horizontal rules.
        """
        self._write = write
        self._color = color
        self._width = width

    # --- Primitives -------------------------------------------------------

    def _paint(self, text: str, color: str) -> str:
        """
        Wrap `text` in an ANSI colour, or return it unchanged.

        Args:
            text: Text to colourise.
            color: Key into the palette (e.g. "red", "dim").

        Returns:
            The text, wrapped in colour codes only if colour is enabled and
            the key is known.
        """
        if not self._color or color not in _COLORS:
            return text
        return f"{_COLORS[color]}{text}{_RESET}"

    def blank(self) -> None:
        """Write one empty line."""
        self._write("")

    def rule(self, char: str = "─") -> None:
        """
        Write a horizontal rule.

        Args:
            char: Character to repeat across the rule.
        """
        self._write(self._paint(char * self._width, "dim"))

    def line(self, text: str = "") -> None:
        """
        Write one raw line.

        Args:
            text: Text to write.
        """
        self._write(text)

    # --- Composite frames -------------------------------------------------

    def title(self, title: str, intro: str = "") -> None:
        """
        Write the encounter header.

        Args:
            title: Encounter title.
            intro: Optional scene-setting paragraph, wrapped to width.
        """
        self.rule("═")
        self._write(self._paint(f"  {title}", "bold"))
        self.rule("═")
        if intro:
            for chunk in _wrap(intro, self._width - 2):
                self._write(self._paint(f"  {chunk}", "dim"))
        self.blank()

    def log(self, messages: Iterable[str]) -> None:
        """
        Write combat log messages, highlighting round headers.

        Args:
            messages: Log lines returned by the combat engine.
        """
        for message in messages:
            if message.startswith("---"):
                self.blank()
                self._write(self._paint(message, "bold"))
            else:
                self._write(f"  {message}")

    def status(self, player: Player, enemies: Sequence[Enemy]) -> None:
        """
        Write the HUD: player vitals plus one line per living enemy.

        Args:
            player: The player combatant.
            enemies: Enemies to list; defeated enemies are shown greyed out.
        """
        self.blank()
        self.rule()
        self._write(self._player_line(player))
        for index, enemy in enumerate(enemies, start=1):
            self._write(self._enemy_line(index, enemy))
        self.rule()

    def menu(self, entries: Sequence[tuple[str, str]]) -> None:
        """
        Write an action menu.

        Args:
            entries: `(key, label)` pairs, rendered as `[key] label`.
        """
        rendered = [f"{self._paint('[' + key + ']', 'cyan')} {label}" for key, label in entries]
        self._write("  " + "   ".join(rendered))

    def notice(self, message: str) -> None:
        """
        Write an informational line.

        Args:
            message: Text to show.
        """
        self._write(self._paint(f"  {message}", "blue"))

    def error(self, message: str) -> None:
        """
        Write a recoverable-error line (bad input, unusable ability).

        Args:
            message: Text to show.
        """
        self._write(self._paint(f"  ✗ {message}", "yellow"))

    def outcome(self, heading: str, detail: str = "", color: str = "green") -> None:
        """
        Write the end-of-combat banner.

        Args:
            heading: Banner heading (e.g. "VICTORY").
            detail: Optional supporting line.
            color: Palette key for the heading.
        """
        self.blank()
        self.rule("═")
        self._write(self._paint(f"  {heading}", color))
        if detail:
            self._write(self._paint(f"  {detail}", "dim"))
        self.rule("═")

    # --- HUD pieces -------------------------------------------------------

    def _player_line(self, player: Player) -> str:
        """
        Format the player's HUD line.

        Args:
            player: The player combatant.

        Returns:
            One formatted line with HP bar, Boost Points, and charge.
        """
        bar = self._bar(player.hp, player.max_hp, 20)
        hp = f"{player.hp:>4}/{player.max_hp:<4}"
        bp = _pips(player.boost_points, player.max_boost_points, _PIP_FULL, _PIP_EMPTY)
        charge = _pips(
            player.temporal_charge,
            player.max_temporal_charge,
            _CHARGE_FULL,
            _CHARGE_EMPTY,
        )
        return (
            f"  {self._paint(player.name.ljust(18), 'bold')} {bar} {hp}  "
            f"BP {self._paint(bp, 'yellow')}  TC {self._paint(charge, 'magenta')}"
        )

    def _enemy_line(self, index: int, enemy: Enemy) -> str:
        """
        Format one enemy's HUD line.

        Args:
            index: 1-based selection number shown to the player.
            enemy: The enemy to describe.

        Returns:
            One formatted line with HP bar, shield pips, and break state.
        """
        label = f"{index}) {enemy.name}".ljust(18)
        if not enemy.is_alive:
            return self._paint(f"  {label} defeated", "dim")

        bar = self._bar(enemy.hp, enemy.max_hp, 20)
        hp = f"{enemy.hp:>4}/{enemy.max_hp:<4}"
        shield = _SHIELD * enemy.shield_points
        suffix = (
            self._paint(f"BROKEN ({enemy.break_turns_remaining})", "red")
            if enemy.is_broken
            else self._paint(f"SH {shield or '—'}", "blue")
        )
        return f"  {label} {bar} {hp}  {suffix}"

    def _bar(self, current: int, maximum: int, width: int) -> str:
        """
        Draw a proportional bar, colour-coded by remaining fraction.

        A non-empty value never renders as a fully empty bar, so "almost
        dead" stays visually distinct from "dead".

        Args:
            current: Current value.
            maximum: Maximum value; non-positive renders an empty bar.
            width: Bar width in characters.

        Returns:
            The bracketed, optionally coloured bar.
        """
        if maximum <= 0:
            return f"[{_BAR_EMPTY * width}]"

        ratio = max(0.0, min(1.0, current / maximum))
        filled = int(ratio * width)
        if current > 0 and filled == 0:
            filled = 1

        color = "green" if ratio > 0.5 else "yellow" if ratio > 0.25 else "red"
        bar = self._paint(_BAR_FILLED * filled, color) + _BAR_EMPTY * (width - filled)
        return f"[{bar}]"


def _pips(current: int, maximum: int, full: str, empty: str) -> str:
    """
    Render a small resource meter as filled/empty pips.

    Args:
        current: Filled pip count.
        maximum: Total pip count.
        full: Glyph for a filled pip.
        empty: Glyph for an empty pip.

    Returns:
        The pip string (empty when `maximum` is non-positive).
    """
    if maximum <= 0:
        return ""
    filled = max(0, min(current, maximum))
    return full * filled + empty * (maximum - filled)


def _wrap(text: str, width: int) -> list[str]:
    """
    Wrap text to `width` on word boundaries.

    Args:
        text: Text to wrap.
        width: Maximum line width; non-positive returns the text unwrapped.

    Returns:
        Wrapped lines (empty list for empty input).
    """
    if width <= 0:
        return [text] if text else []

    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
