"""Scripted input and captured output for driving the terminal game in tests."""

from collections.abc import Iterable


class Script:
    """
    A `read_input` stand-in that answers prompts from a fixed list.

    Attributes:
        prompts: Every prompt asked, in order.
    """

    def __init__(self, lines: Iterable[str], then: str = "q") -> None:
        """
        Build the script.

        Args:
            lines: Answers to give, in order.
            then: Answer given to every prompt after `lines` runs out.
        """
        self._lines = list(lines)
        self._then = then
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        """Record the prompt and return the next scripted answer."""
        self.prompts.append(prompt)
        return self._lines.pop(0) if self._lines else self._then


class Screen:
    """A `write` sink that keeps every line."""

    def __init__(self) -> None:
        """Start with no output."""
        self.lines: list[str] = []

    def __call__(self, line: str = "") -> None:
        """Record one output line."""
        self.lines.append(line)

    @property
    def text(self) -> str:
        """Return all output as one string."""
        return "\n".join(self.lines)
