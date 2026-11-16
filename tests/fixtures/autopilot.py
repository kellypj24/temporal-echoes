"""
Scripted players for measuring encounter balance.

A policy answers one prompt of the terminal game, given the live combat
and a scratch dict that lasts one fight. Policies read state the player
can see on the board; they do not read enemy AI state or RNG.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from src.content import Encounter
from src.core.combat import CombatContext, CombatOutcome
from src.core.persistence import EventStore
from src.core.temporal import COUNTER_STOP_COST, ArchetypeCounterPolicy, TemporalAnnouncement
from src.entities import Enemy
from src.play import build_combat
from src.states.combat_cli import CombatCLI
from src.ui.console import ConsoleRenderer

Policy = Callable[[CombatContext, str, dict[str, Any]], str]

MAX_PROMPTS = 4000
REWIND_HP_LOSS = 0.25  # rewind when one round cost this share of max HP
MAX_REWINDS = 8
ALL_TOOLS = frozenset({"rewind", "echo", "counter"})


def _number(combat: CombatContext, enemy: Enemy) -> str:
    return str(combat.enemies.index(enemy) + 1)


def masher(combat: CombatContext, prompt: str, memory: dict[str, Any]) -> str:  # noqa: ARG001
    """Attack the first living enemy every turn and decline everything else."""
    return "a" if prompt.strip() == ">" else ""


def tactician(combat: CombatContext, prompt: str, memory: dict[str, Any]) -> str:
    """
    Play with every tool: kill the weakest first, boost into breaks, defend
    when every enemy is defending, spend a 1-charge rewind to empty a
    watching Chronomancer's pool, echo a boosted turn once she cannot
    counter, rewind a round that cost a quarter of max HP, and counter
    enemy casts.
    """
    return _tactics(combat, prompt, memory, ALL_TOOLS)


def fighter(combat: CombatContext, prompt: str, memory: dict[str, Any]) -> str:
    """
    Play well without time: the tactician's targeting, boosts and defends,
    but never a rewind, an Echo Cast or a Counter-Stop.
    """
    return _tactics(combat, prompt, memory, frozenset())


def _tactics(
    combat: CombatContext, prompt: str, memory: dict[str, Any], tools: frozenset[str]
) -> str:
    """
    Shared decision procedure for `tactician` and `fighter`.

    Args:
        combat: The live combat.
        prompt: The prompt being answered.
        memory: Scratch state for this fight.
        tools: Which of "rewind", "echo" and "counter" may be used.

    Returns:
        The answer to type.
    """
    player = combat.player
    living = combat.living_enemies

    if "Counter-Stop" in prompt:
        return "y" if "counter" in tools else "n"
    if "BP to spend" in prompt:
        return str(min(3, player.boost_points))
    if "Target" in prompt:
        return str(memory["target"])
    if "Echo window" in prompt:
        return str(min(3, len(combat._action_history[player.id])))
    if "Rewind how many" in prompt:
        return "1"

    here = (combat._current_branch_id, combat._total_turns)
    lost = memory.get("hp_at_last_turn", player.hp) - player.hp
    memory["hp_at_last_turn"] = player.hp

    # A Chronomancer holding 3 charge counters any cast. The cheapest cast
    # is a 1-charge rewind: spend it to empty her pool, then cast freely.
    watched = any(
        e.archetype == "chronomancer" and e.temporal_charge >= COUNTER_STOP_COST for e in living
    )
    if (
        ("echo" in tools or "rewind" in tools)
        and watched
        and player.temporal_charge >= 1
        and combat.player_turns_taken >= 1
        and memory.get("baited_at") != here
    ):
        memory["baited_at"] = here
        return "r"

    if (
        "rewind" in tools
        and not watched
        and lost >= REWIND_HP_LOSS * player.max_hp
        and player.temporal_charge >= 1
        and combat.player_turns_taken >= 1
        and memory.get("rewound_at") != here
        and memory.get("rewinds", 0) < MAX_REWINDS
    ):
        memory["rewound_at"] = here
        memory["rewinds"] = memory.get("rewinds", 0) + 1
        memory.pop("hp_at_last_turn")
        return "r"

    open_targets = [e for e in living if not e.is_defending] or living
    target = min(open_targets, key=lambda e: (not e.is_broken, e.hp))
    memory["target"] = _number(combat, target)

    if (
        "echo" in tools
        and not watched
        and player.temporal_charge >= 2
        and memory.get("last_was_boost")
        and "player" not in combat._active_echoes
        and memory.get("echoed_at") != here
    ):
        memory["echoed_at"] = here
        memory["last_was_boost"] = False
        return "e"

    if all(e.is_defending for e in living) and player.boost_points < 5:
        memory["last_was_boost"] = False
        return "d"

    if player.boost_points >= 3 or (target.is_broken and player.boost_points >= 1):
        memory["last_was_boost"] = True
        return "b"

    memory["last_was_boost"] = False
    return memory["target"]


@dataclass(frozen=True)
class FightReport:
    """
    How one scripted fight went.

    Attributes:
        encounter_id: The encounter played.
        outcome: Final outcome, or None if the script ran out of prompts.
        hp_left: Player HP at the end.
        max_hp: Player max HP.
        rounds: Rounds fought.
    """

    encounter_id: str
    outcome: CombatOutcome | None
    hp_left: int
    max_hp: int
    rounds: int

    @property
    def won(self) -> bool:
        """Return whether the fight ended in victory."""
        return self.outcome is CombatOutcome.VICTORY


def play_fight(
    encounter: Encounter, policy: Policy, seed: int, player_hp: int | None = None
) -> FightReport:
    """
    Play one encounter with a scripted policy and no output.

    Args:
        encounter: The encounter to play.
        policy: The scripted player.
        seed: RNG seed for the fight.
        player_hp: Starting HP; None means full.

    Returns:
        How the fight went.
    """
    memory: dict[str, Any] = {}
    controller: list[CombatCLI] = []
    asked = {"n": 0}

    def ask_player(announcement: TemporalAnnouncement) -> bool:
        return controller[0].ask_counter(announcement)

    combat = build_combat(
        encounter,
        seed,
        EventStore(":memory:"),
        player_hp=player_hp,
        counter_policy=ArchetypeCounterPolicy(ask_player=ask_player),
    )

    def read(prompt: str) -> str:
        asked["n"] += 1
        return "q" if asked["n"] > MAX_PROMPTS else policy(combat, prompt, memory)

    controller.append(
        CombatCLI(combat, ConsoleRenderer(write=lambda _line="": None), read_input=read)
    )
    outcome = controller[0].run()
    return FightReport(
        encounter_id=encounter.id,
        outcome=outcome,
        hp_left=combat.player.hp,
        max_hp=combat.player.max_hp,
        rounds=combat.round_number,
    )


def play_campaign(encounters: Sequence[Encounter], policy: Policy, seed: int) -> list[FightReport]:
    """
    Play encounters in order with wounds carried, stopping at the first loss.

    Args:
        encounters: Encounters in play order.
        policy: The scripted player.
        seed: RNG seed applied to every fight.

    Returns:
        One report per fight started.
    """
    reports: list[FightReport] = []
    missing = 0
    for encounter in encounters:
        report = play_fight(encounter, policy, seed, player_hp=encounter.player.max_hp - missing)
        reports.append(report)
        if not report.won:
            break
        missing = report.max_hp - report.hp_left
    return reports
