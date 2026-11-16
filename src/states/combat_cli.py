"""
Interactive text-mode controller for a single combat encounter.

This is the controller half of MVC: it owns no rules and formats no text.
It reads input, translates it into `CombatAction`s (or direct
`TemporalSystem` calls for rewind, which does not consume a turn), and
hands the engine's transcript to the renderer.

Input and output are both injected, so a full fight can be driven in a
test — or scripted for a hands-off demo — without a terminal.
"""

import logging
from collections.abc import Callable, Sequence
from enum import Enum, auto

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatOutcome, CombatPhase
from src.core.exceptions import TemporalError
from src.core.temporal import (
    COUNTER_STOP_COST,
    ECHO_CAST_COST,
    MAX_ECHO_TURNS,
    CounterStopResult,
    RewindResult,
    TemporalAnnouncement,
)
from src.entities import Enemy, Player
from src.ui.console import ConsoleRenderer

logger = logging.getLogger(__name__)

# Phases where no combatant is mid-turn, so the next thing to do is start a round.
_ROUND_BOUNDARY_PHASES = frozenset(
    {CombatPhase.INITIALIZING, CombatPhase.ROUND_START, CombatPhase.ROUND_END}
)

# Prompt strings are module constants because they are a contract, not just
# UI text: `Autopilot` recognises which question it is answering by matching
# the fixed prefix of each one.
PROMPT_COMMAND = "  > "
PROMPT_BP = "  BP to spend (1-{maximum}, blank to cancel): "
PROMPT_ECHO = "  Echo window — replay your last N actions (1-{maximum}, blank = 1): "
PROMPT_REWIND = "  Rewind how many of your turns (1-{maximum}, blank = 1)? "
PROMPT_COUNTER = "  Counter-Stop it for {cost} charge? [y/N] "
PROMPT_TARGET = "  Target (number, blank to cancel): "

_MENU: tuple[tuple[str, str], ...] = (
    ("1-9", "attack"),
    ("b", "boost"),
    ("d", "defend"),
    ("e", "echo"),
    ("r", "rewind"),
    ("f", "flee"),
    ("?", "help"),
    ("q", "quit"),
)

_HELP: tuple[str, ...] = (
    "1-9  Attack an enemy by its HUD number (a = first living enemy).",
    "b    Boosted attack: spend 1-3 BP for 1.5x / 2.0x / 2.5x damage.",
    "d    Defend: halve incoming damage until your next turn.",
    f"e    Echo Cast ({ECHO_CAST_COST} charge): a past-self replays your last "
    f"1-{MAX_ECHO_TURNS} actions at full damage.",
    "r    Rewind (1 charge per turn of yours): return to the start of an earlier",
    "     turn of yours and choose again. It does not cost your turn.",
    "f    Flee the encounter.",
    "s    Redraw the status board.",
    "q    Quit to the shell.",
    "",
    "Basic attacks are PHYSICAL. Hitting a weakness chips a shield; empty the",
    "shield to Break the enemy — it is stunned and takes extra damage.",
)


class TurnSignal(Enum):
    """
    What the controller should do after handling one player input.

    Values:
        ACTED: A turn was consumed; advance combat.
        REPROMPT: No turn was consumed (help, bad input, rewind); ask again.
        QUIT: The player asked to leave; abandon the encounter.
    """

    ACTED = auto()
    REPROMPT = auto()
    QUIT = auto()


class CombatCLI:
    """
    Drives one `CombatContext` to completion against a human (or a script).

    Attributes:
        _combat: The encounter being played.
        _renderer: Presentation layer.
        _read_input: Prompt -> response function (injected for testing).
        _pause: Called between engine beats so fights are readable.
        _cursor: How much of the engine transcript has been rendered.
    """

    def __init__(
        self,
        combat: CombatContext,
        renderer: ConsoleRenderer,
        read_input: Callable[[str], str] = input,
        pause: Callable[[], None] = lambda: None,
    ) -> None:
        """
        Initialise the controller.

        Args:
            combat: The combat encounter to play.
            renderer: Console renderer for all output.
            read_input: Called with a prompt, returns the player's raw line.
                Defaults to `input`; tests and demo mode inject a script.
            pause: Called after enemy turns to pace the fight.
        """
        self._combat = combat
        self._renderer = renderer
        self._read_input = read_input
        self._pause = pause
        self._cursor = 0

    # --- Main loop --------------------------------------------------------

    def run(self, title: str = "", intro: str = "") -> CombatOutcome | None:
        """
        Play the encounter to its conclusion.

        Args:
            title: Encounter title for the header.
            intro: Optional scene-setting text.

        Returns:
            The final `CombatOutcome`, or None if the player quit early.
        """
        if title:
            self._renderer.title(title, intro)
        self._flush()

        while not self._combat.is_over:
            if self._combat.phase in _ROUND_BOUNDARY_PHASES:
                self._combat.start_round()
                self._flush()
                continue

            current = self._combat.current_combatant
            if isinstance(current, Player):
                signal = self._take_player_turn()
                if signal is TurnSignal.QUIT:
                    self._renderer.outcome("Abandoned.", "The timeline holds — for now.", "dim")
                    return None
                if signal is TurnSignal.REPROMPT:
                    continue
            elif isinstance(current, Enemy):
                self._combat.execute_enemy_turn(current)
                self._flush()
                self._pause()
                if self._combat.phase is CombatPhase.AWAITING_PLAYER_INPUT:
                    # The enemy rewound time: its turn no longer exists
                    # and the player acts next, so there is nothing to advance.
                    continue

            self._combat.advance_turn()
            self._flush()

        self._render_outcome()
        return self._combat.outcome

    def _flush(self) -> None:
        """Render every transcript line the engine has produced since last call."""
        messages = self._combat.log_messages
        if len(messages) > self._cursor:
            self._renderer.log(messages[self._cursor :])
            self._cursor = len(messages)

    def _render_outcome(self) -> None:
        """Draw the end-of-combat banner for the final outcome."""
        outcome = self._combat.outcome
        if outcome is CombatOutcome.VICTORY:
            self._renderer.outcome(
                "VICTORY",
                f"{self._combat.player.name} stands. Rounds fought: {self._combat.round_number}.",
                "green",
            )
        elif outcome is CombatOutcome.DEFEAT:
            self._renderer.outcome(
                "DEFEAT",
                "The moment closes over you. Try rewinding sooner next time.",
                "red",
            )
        else:
            self._renderer.outcome("ESCAPED", "You live to fight in another now.", "yellow")

    # --- Player turn ------------------------------------------------------

    def _take_player_turn(self) -> TurnSignal:
        """
        Draw the board, read one command, and act on it.

        Returns:
            The signal describing what the controller should do next.
        """
        self._renderer.status(self._combat.player, self._combat.enemies)
        self._renderer.menu(_MENU)
        command = self._read_input(PROMPT_COMMAND).strip().lower()

        if not command:
            return TurnSignal.REPROMPT
        if command in {"q", "quit", "exit"}:
            return TurnSignal.QUIT
        if command in {"?", "h", "help"}:
            self._renderer.blank()
            for line in _HELP:
                self._renderer.line(f"  {line}")
            return TurnSignal.REPROMPT
        if command in {"s", "status"}:
            return TurnSignal.REPROMPT
        if command in {"d", "defend"}:
            return self._submit(CombatAction(action_type="defend", target_id=""))
        if command in {"f", "flee"}:
            return self._submit(CombatAction(action_type="flee", target_id=""))
        if command in {"e", "echo"}:
            return self._echo_cast()
        if command in {"r", "rewind"}:
            return self._rewind()
        if command in {"b", "boost"}:
            return self._boosted_attack()
        return self._attack(command)

    def _attack(self, command: str) -> TurnSignal:
        """
        Attack an enemy chosen by HUD number (or "a" for the first living one).

        Args:
            command: The raw command text.

        Returns:
            ACTED on a valid target, REPROMPT otherwise.
        """
        living = self._combat.living_enemies
        if command in {"a", "attack"}:
            target_id = living[0].id
        else:
            target = self._resolve_target(command, living)
            if target is None:
                return TurnSignal.REPROMPT
            target_id = target.id
        return self._submit(CombatAction(action_type="attack", target_id=target_id))

    def _boosted_attack(self) -> TurnSignal:
        """
        Prompt for Boost Points and a target, then attack.

        Returns:
            ACTED once the attack is submitted, REPROMPT if the player has
            no BP or cancels at either prompt.
        """
        player = self._combat.player
        if player.boost_points < 1:
            self._renderer.error("No Boost Points yet — you gain 1 at the start of each round.")
            return TurnSignal.REPROMPT

        spendable = min(3, player.boost_points)
        raw = self._read_input(PROMPT_BP.format(maximum=spendable)).strip()
        if not raw:
            return TurnSignal.REPROMPT
        if not raw.isdigit() or not 1 <= int(raw) <= spendable:
            self._renderer.error(f"Enter a number from 1 to {spendable}.")
            return TurnSignal.REPROMPT

        living = self._combat.living_enemies
        target = living[0] if len(living) == 1 else self._prompt_for_target(living)
        if target is None:
            return TurnSignal.REPROMPT

        return self._submit(
            CombatAction(action_type="attack", target_id=target.id, boost_points=int(raw))
        )

    def _echo_cast(self) -> TurnSignal:
        """
        Prompt for an echo window and cast, spending the turn.

        Returns:
            ACTED if the cast was submitted (even if Counter-Stopped — the
            turn is spent either way), REPROMPT if the player cancelled or
            the engine rejected the cast.
        """
        raw = self._read_input(PROMPT_ECHO.format(maximum=MAX_ECHO_TURNS)).strip()
        turns = 1
        if raw:
            if not raw.isdigit() or not 1 <= int(raw) <= MAX_ECHO_TURNS:
                self._renderer.error(f"Enter a number from 1 to {MAX_ECHO_TURNS}.")
                return TurnSignal.REPROMPT
            turns = int(raw)

        return self._submit(CombatAction(action_type="echo_cast", target_id="", echo_turns=turns))

    def _rewind(self) -> TurnSignal:
        """
        Rewind combat, then hand the turn back to the player.

        Rewind is not a `CombatAction`: it is measured in the player's own
        turns and leaves combat awaiting player input at the start of the
        earlier one, so the
        player still acts this turn. That stays true when it is countered —
        the charge is spent, the jump does not happen, and the turn is
        still theirs.

        Returns:
            REPROMPT in every case.
        """
        player = self._combat.player
        if player.temporal_charge < 1:
            self._renderer.error("No temporal charge — you gain 1 at the start of each round.")
            return TurnSignal.REPROMPT
        maximum = min(player.temporal_charge, self._combat.player_turns_taken)
        if maximum < 1:
            self._renderer.error("Nothing to rewind — you have not taken a turn yet.")
            return TurnSignal.REPROMPT

        raw = self._read_input(PROMPT_REWIND.format(maximum=maximum)).strip()
        count = 1
        if raw:
            if not raw.isdigit() or not 1 <= int(raw) <= maximum:
                self._renderer.error(f"Enter a number from 1 to {maximum}.")
                return TurnSignal.REPROMPT
            count = int(raw)

        try:
            result = self._combat.rewind_player_turns(count)
        except TemporalError as exc:
            self._renderer.error(str(exc))
            return TurnSignal.REPROMPT

        self._flush()
        if isinstance(result, RewindResult):
            self._renderer.notice(
                f"Time folds back to the start of your turn {count} ago, "
                f"onto branch {result.new_branch_id}. {result.charge_spent} charge spent."
            )
        else:
            self._render_counter(result)
        return TurnSignal.REPROMPT

    def ask_counter(self, announcement: TemporalAnnouncement) -> bool:
        """
        Ask the player whether to Counter-Stop an enemy's announced cast.

        Called by the counter policy in the middle of an enemy's turn,
        only when the player holds the charge to respond.

        Args:
            announcement: The enemy cast being announced.

        Returns:
            True if the player chooses to counter.
        """
        self._flush()
        what = "rewind time" if announcement.ability == "rewind" else "cast Echo"
        self._renderer.notice(f"{self._name_of(announcement.caster_id)} begins to {what}.")
        answer = self._read_input(PROMPT_COUNTER.format(cost=COUNTER_STOP_COST)).strip().lower()
        return answer in {"y", "yes"}

    # --- Helpers ----------------------------------------------------------

    def _submit(self, action: CombatAction) -> TurnSignal:
        """
        Submit a player action to the engine and render what happened.

        Args:
            action: The action to execute.

        Returns:
            ACTED if the engine accepted the action, REPROMPT if it
            rejected it for a reason the player can act on.
        """
        try:
            self._combat.submit_player_action(action)
        except TemporalError as exc:
            self._renderer.error(str(exc))
            return TurnSignal.REPROMPT

        self._flush()
        return TurnSignal.ACTED

    def _render_counter(self, result: CounterStopResult) -> None:
        """
        Announce a Counter-Stop that the transcript does not spell out.

        Args:
            result: The counter payload from the engine.
        """
        self._renderer.notice(
            f"Counter-Stopped by {self._name_of(result.responder_id)} — "
            f"{result.caster_charge_lost} charge spent for nothing."
        )

    def _name_of(self, combatant_id: str) -> str:
        """
        Resolve a combatant id to a display name.

        Args:
            combatant_id: The id to look up.

        Returns:
            The combatant's name, or the raw id if it is unknown.
        """
        if combatant_id == self._combat.player.id:
            return self._combat.player.name
        for enemy in self._combat.enemies:
            if enemy.id == combatant_id:
                return enemy.name
        return combatant_id

    def _prompt_for_target(self, living: Sequence[Enemy]) -> Enemy | None:
        """
        Ask which enemy to hit.

        Args:
            living: Enemies still standing.

        Returns:
            The chosen enemy, or None if the player cancelled or mis-typed.
        """
        raw = self._read_input(PROMPT_TARGET).strip()
        if not raw:
            return None
        return self._resolve_target(raw, living)

    def _resolve_target(self, raw: str, living: Sequence[Enemy]) -> Enemy | None:
        """
        Translate a HUD number into a living enemy.

        HUD numbers index `combat.enemies` so they stay stable as enemies
        fall — the number next to a corpse never silently becomes a
        different enemy.

        Args:
            raw: The player's raw input.
            living: Enemies still standing.

        Returns:
            The selected enemy, or None (an error is rendered) if the input
            is not a number, out of range, or points at a defeated enemy.
        """
        if not raw.isdigit():
            self._renderer.error(f"Unknown command '{raw}' — press ? for help.")
            return None

        index = int(raw)
        roster = self._combat.enemies
        if not 1 <= index <= len(roster):
            self._renderer.error(f"No enemy {index}. Choose 1-{len(roster)}.")
            return None

        target = roster[index - 1]
        if target not in living:
            self._renderer.error(f"{target.name} is already defeated.")
            return None
        return target
