"""
Combat logger for human-readable combat messages.

Pure text formatting with no game logic. Returns lists of message strings
per action for easy testing and future UI integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.damage import DamageResult
    from src.entities import Combatant, Enemy, Player


class CombatLogger:
    """
    Formats combat events into human-readable text messages.

    Accumulates messages over the course of combat. Each method returns
    the new messages it added, and they are also stored in the internal
    message log for later retrieval.

    Attributes:
        _messages: All accumulated combat messages.
    """

    def __init__(self) -> None:
        """Initialize an empty combat logger."""
        self._messages: list[str] = []

    @property
    def messages(self) -> list[str]:
        """Return all accumulated messages."""
        return list(self._messages)

    def log_combat_start(self, player: Player, enemies: list[Enemy]) -> list[str]:
        """
        Log the start of combat.

        Args:
            player: The player combatant.
            enemies: List of enemy combatants.

        Returns:
            List of formatted messages.
        """
        msgs: list[str] = []
        enemy_names = ", ".join(e.name for e in enemies)
        msgs.append(f"Combat begins! {player.name} vs {enemy_names}")
        for enemy in enemies:
            weakness_names = ", ".join(w.name for w in enemy.weaknesses)
            shield_info = f"Shield: {enemy.shield_points}/{enemy.max_shield_points}"
            if weakness_names:
                msgs.append(
                    f"  {enemy.name} - HP: {enemy.hp}/{enemy.max_hp} | {shield_info} | Weak: {weakness_names}"
                )
            else:
                msgs.append(f"  {enemy.name} - HP: {enemy.hp}/{enemy.max_hp} | {shield_info}")
        self._messages.extend(msgs)
        return msgs

    def log_round_start(self, round_number: int, turn_order: list[Combatant]) -> list[str]:
        """
        Log the start of a new round.

        Args:
            round_number: The current round number.
            turn_order: Combatants in speed order.

        Returns:
            List of formatted messages.
        """
        msgs: list[str] = []
        order_names = " -> ".join(c.name for c in turn_order)
        msgs.append(f"--- Round {round_number} ---")
        msgs.append(f"Turn order: {order_names}")
        self._messages.extend(msgs)
        return msgs

    def log_attack(
        self,
        actor: Combatant,
        target: Combatant,
        damage_result: DamageResult,
        boost_points: int = 0,
    ) -> list[str]:
        """
        Log an attack action with damage details.

        Args:
            actor: The attacking combatant.
            target: The target combatant.
            damage_result: Result from damage calculation.
            boost_points: BP spent on this attack.

        Returns:
            List of formatted messages.
        """
        msgs: list[str] = []
        bp_str = f" (Boost x{boost_points})" if boost_points > 0 else ""
        msgs.append(
            f"{actor.name} attacks {target.name}{bp_str} for {damage_result.damage} damage!"
        )
        if damage_result.is_critical:
            msgs.append("  Critical hit!")
        if damage_result.is_weakness:
            msgs.append(f"  Hit {target.name}'s weakness!")
        self._messages.extend(msgs)
        return msgs

    def log_defend(self, actor: Combatant) -> list[str]:
        """
        Log a defend action.

        Args:
            actor: The defending combatant.

        Returns:
            List of formatted messages.
        """
        msgs = [f"{actor.name} takes a defensive stance."]
        self._messages.extend(msgs)
        return msgs

    def log_flee(self, actor: Combatant, success: bool) -> list[str]:
        """
        Log a flee attempt.

        Args:
            actor: The fleeing combatant.
            success: Whether the flee succeeded.

        Returns:
            List of formatted messages.
        """
        if success:
            msgs = [f"{actor.name} successfully fled from battle!"]
        else:
            msgs = [f"{actor.name} tried to flee but failed!"]
        self._messages.extend(msgs)
        return msgs

    def log_shield_break(self, enemy: Enemy) -> list[str]:
        """
        Log a shield break event.

        Args:
            enemy: The enemy whose shield broke.

        Returns:
            List of formatted messages.
        """
        msgs = [f"{enemy.name}'s shield is broken! Stunned for 1 turn!"]
        self._messages.extend(msgs)
        return msgs

    def log_defeat(self, combatant: Combatant) -> list[str]:
        """
        Log a combatant's defeat.

        Args:
            combatant: The defeated combatant.

        Returns:
            List of formatted messages.
        """
        msgs = [f"{combatant.name} has been defeated!"]
        self._messages.extend(msgs)
        return msgs

    def log_bp_gain(self, player: Player, amount: int) -> list[str]:
        """
        Log boost point gain.

        Args:
            player: The player who gained BP.
            amount: Actual BP gained.

        Returns:
            List of formatted messages.
        """
        if amount > 0:
            msgs = [f"{player.name} gains {amount} BP! (Total: {player.boost_points} BP)"]
        else:
            msgs = [
                f"{player.name}'s BP is full! ({player.boost_points}/{player.max_boost_points})"
            ]
        self._messages.extend(msgs)
        return msgs

    def log_echo_spawned(self, owner: Combatant, duration: int) -> list[str]:
        """
        Log a successful Echo Cast.

        Args:
            owner: The combatant who cast the echo.
            duration: Number of turns the echo will act.

        Returns:
            List of formatted messages.
        """
        msgs = [f"{owner.name} casts Echo! A past-self will act for {duration} turn(s)."]
        self._messages.extend(msgs)
        return msgs

    def log_echo_acted(
        self,
        owner: Combatant,
        action_type: str,
        target: Combatant | None,
        damage: int | None,
    ) -> list[str]:
        """
        Log one act of an owner's echo.

        Args:
            owner: The echo's owner (the echo is described as "owner's echo").
            action_type: "attack", "defend", or "fizzle".
            target: The struck combatant (attack only), else None.
            damage: Damage dealt (attack only), else None.

        Returns:
            List of formatted messages.
        """
        if action_type == "attack" and target is not None and damage is not None:
            msgs = [f"{owner.name}'s echo attacks {target.name} for {damage} damage!"]
        elif action_type == "defend":
            msgs = [f"{owner.name}'s echo takes a defensive stance."]
        else:
            msgs = [f"{owner.name}'s echo fizzles, unable to act."]
        self._messages.extend(msgs)
        return msgs

    def log_combat_end(self, outcome: str) -> list[str]:
        """
        Log the end of combat.

        Args:
            outcome: Combat outcome ("victory", "defeat", "fled").

        Returns:
            List of formatted messages.
        """
        outcome_messages = {
            "victory": "Victory! All enemies have been defeated!",
            "defeat": "Defeat... The party has fallen.",
            "fled": "The party escaped from battle.",
        }
        msg = outcome_messages.get(outcome, f"Combat ended: {outcome}")
        msgs = [msg]
        self._messages.extend(msgs)
        return msgs

    def clear(self) -> None:
        """Clear all accumulated messages."""
        self._messages.clear()
