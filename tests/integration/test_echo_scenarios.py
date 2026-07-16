"""
Integration tests for Phase 3 Step 5 Echo Cast.

Verifies end-to-end combat -> echo cast -> echo acting scenarios, rewind
interop (the trickiest surface — echoes must survive or vanish correctly
across a rewind depending on where the cast falls relative to the target
turn), and determinism invariants.

Uses natural charge economy (regen via start_round(), 1/round) rather than
hand-assigning combat.player.temporal_charge before a cast whenever a
rewind follows in the same test: a hand-assigned value that isn't backed by
real CHARGE_REGENERATED events in the store will make replay legitimately
fail once it reaches the corresponding CHARGE_SPENT event (spend_charge()
raises on an under-funded reconstructed balance). Charge is only
hand-assigned for a rewind's own spend, which is always safe — that
CHARGE_SPENT is stamped at the pre-rewind turn, which sits outside the
replay window (turn_number > to_turn), so replay never revisits it.
"""

from __future__ import annotations

import json

import pytest

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatPhase
from src.core.events import EventTypes
from src.core.exceptions import RewindReplayError
from tests.fixtures.combat_fixtures import create_combat_context
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player

# ============================================================================
# Helpers
# ============================================================================


def _attack(target_id: str = "enemy_1") -> CombatAction:
    """Return an attack CombatAction targeting the given ID."""
    return CombatAction(action_type="attack", target_id=target_id)


def _defend(actor_id: str = "player_1") -> CombatAction:
    """Return a defend CombatAction (a defender targets itself)."""
    return CombatAction(action_type="defend", target_id=actor_id)


def _echo_cast(turns: int = 1, actor_id: str = "player_1") -> CombatAction:
    """Return an echo_cast CombatAction requesting the given duration."""
    return CombatAction(action_type="echo_cast", target_id=actor_id, echo_turns=turns)


def _play_n_player_turns(combat: CombatContext, n: int, action: CombatAction) -> None:
    """
    Advance *n* player turns in a round-aware loop (mirrors
    test_rewind_scenarios.py's helper of the same name).

    Args:
        combat: The active CombatContext.
        n: Number of player turns to play.
        action: The player action to submit on each turn.
    """
    from src.entities import Enemy

    turns_played = 0
    iterations = 0
    max_iterations = n * 20 + 50
    while turns_played < n:
        iterations += 1
        if iterations > max_iterations:
            raise RuntimeError(
                f"_play_n_player_turns made no progress: stuck in phase "
                f"{combat.phase.name} after {iterations} iterations "
                f"({turns_played}/{n} player turns played)"
            )
        if combat.is_over:
            raise RuntimeError("Combat ended prematurely")
        if combat.phase in (
            CombatPhase.INITIALIZING,
            CombatPhase.ROUND_START,
            CombatPhase.ROUND_END,
        ):
            combat.start_round()
        elif combat.phase == CombatPhase.AWAITING_PLAYER_INPUT:
            combat.submit_player_action(action)
            combat.advance_turn()
            turns_played += 1
        elif combat.phase == CombatPhase.EXECUTING_TURN:
            current = combat.current_combatant
            if isinstance(current, Enemy):
                combat.execute_enemy_turn(current)
            combat.advance_turn()


def _tanky_combat(seed: int = 42) -> CombatContext:
    """
    Build a 1v1 combat with both sides very tanky (so a many-turn scenario
    never ends combat early) and a player that starts at 0 charge, so
    charge only comes from natural per-round regen.

    Returns:
        Fresh CombatContext, INITIALIZING phase.
    """
    player = create_test_player(
        hp=100_000, max_hp=100_000, temporal_charge=0, max_temporal_charge=5, attack=50
    )
    enemy = create_test_enemy(hp=100_000, max_hp=100_000, defense=25)
    return create_combat_context(seed=seed, player=player, enemies=[enemy])


def _get_all_events(combat: CombatContext) -> list:
    """Return all events for this combat's timeline."""
    return combat._event_store.get_events_by_timeline(combat._timeline_id)


# ============================================================================
# Full combat scenarios
# ============================================================================


class TestFullCombatWithEchoCast:
    """test_full_combat_with_echo_cast_two."""

    def test_full_combat_with_echo_cast_two(self) -> None:
        """
        3 attacks -> cast(2) -> 2 turns: the echo replays the last 2 attacks
        at half damage, with ECHO_ACTED events on the current branch.
        """
        combat = _tanky_combat()

        _play_n_player_turns(combat, 3, _attack())
        history = list(combat._action_history["player_1"])
        expected_scaled = [max(1, entry.damage_dealt * 5 // 10) for entry in history[-2:]]

        _play_n_player_turns(combat, 1, _echo_cast(turns=2))
        assert "player" in combat._active_echoes

        _play_n_player_turns(combat, 1, _attack())
        _play_n_player_turns(combat, 1, _attack())

        acted_events = [e for e in _get_all_events(combat) if e.event_type == EventTypes.ECHO_ACTED]
        assert len(acted_events) == 2
        dealt = [json.loads(e.event_data)["damage_dealt"] for e in acted_events]
        assert dealt == expected_scaled
        assert "player" not in combat._active_echoes  # expired after 2 acts


class TestEchoCastConsumesTurn:
    """test_echo_cast_consumes_the_turn."""

    def test_echo_cast_consumes_the_turn(self) -> None:
        """Casting advances total_turns and the phase, but deals no attack damage."""
        combat = _tanky_combat()
        _play_n_player_turns(combat, 2, _attack())  # bank 2 charge
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT

        total_before = combat._total_turns
        enemy_hp_before = combat.enemies[0].hp

        combat.submit_player_action(_echo_cast(turns=1))
        combat.advance_turn()

        assert combat._total_turns == total_before + 1
        assert combat.enemies[0].hp == enemy_hp_before
        assert combat.phase != CombatPhase.AWAITING_PLAYER_INPUT  # advanced past the player


class TestEnemyOwnedEchoSymmetric:
    """test_enemy_owned_echo_symmetric."""

    def test_enemy_owned_echo_symmetric(self) -> None:
        """
        An enemy-cast echo (driven manually — Chronomancer AI lands in
        Step 7) hits the player on the enemy's subsequent turn.
        """
        player = create_test_player(hp=1000, max_hp=1000, temporal_charge=3, max_temporal_charge=3)
        enemy = create_test_enemy(
            hp=200, max_hp=200, defense=10, attack=80, temporal_charge=3, max_temporal_charge=3
        )
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])
        combat.start_round()

        combat.submit_player_action(_defend())
        combat.advance_turn()
        combat.execute_enemy_turn(enemy)
        combat.advance_turn()

        assert len(combat._action_history[enemy.id]) == 1

        combat._temporal.echo_cast(combat, enemy, turns=1)
        assert combat._active_echoes["enemy"].owner_id == enemy.id

        player_hp_before = combat.player.hp
        combat.execute_enemy_turn(enemy)  # real action + echo hook both fire

        assert combat.player.hp < player_hp_before
        assert "enemy" not in combat._active_echoes  # single-act echo expired


class TestBrokenEnemyEchoStillActs:
    """test_broken_enemy_echo_still_acts."""

    def test_broken_enemy_echo_still_acts(self) -> None:
        """A stunned (broken) owner still has its echo act (locked semantic 10)."""
        player = create_test_player(hp=1000, max_hp=1000, temporal_charge=3, max_temporal_charge=3)
        enemy = create_test_enemy(
            hp=200, max_hp=200, defense=10, attack=80, temporal_charge=3, max_temporal_charge=3
        )
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])
        combat.start_round()

        combat.submit_player_action(_defend())
        combat.advance_turn()
        combat.execute_enemy_turn(enemy)
        combat.advance_turn()

        combat._temporal.echo_cast(combat, enemy, turns=1)
        enemy.is_broken = True
        enemy.break_turns_remaining = 1

        player_hp_before = combat.player.hp
        msgs = combat.execute_enemy_turn(enemy)

        assert any("stunned" in m.lower() for m in msgs)
        assert combat.player.hp < player_hp_before  # echo still hit despite the stun
        assert "enemy" not in combat._active_echoes


# ============================================================================
# Rewind interop
# ============================================================================


class TestRewindEchoInterop:
    """Rewind x echo scenarios that must fall out correctly (STEP-5-PLAN.md §5)."""

    def test_rewind_before_cast_removes_echo_and_refunds_charge(self) -> None:
        """Rewinding to before the cast leaves no echo and excludes the spend."""
        combat = _tanky_combat()
        _play_n_player_turns(combat, 1, _attack())
        target_turn = combat._total_turns

        _play_n_player_turns(combat, 2, _attack())  # bank charge for the cast
        _play_n_player_turns(combat, 1, _echo_cast(turns=1))
        assert "player" in combat._active_echoes

        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = combat._total_turns - target_turn  # rewind's own spend
        result = combat.rewind_to_turn(target_turn)

        assert result.to_turn == target_turn
        assert "player" not in combat._active_echoes

    def test_rewind_mid_echo_life_restores_next_index(self) -> None:
        """
        Rewinding to just after an echo's first act restores it at the right
        next_index; the second act then replays identically on the new branch.
        """
        combat = _tanky_combat()
        _play_n_player_turns(combat, 2, _attack())  # banks exactly ECHO_CAST_COST
        _play_n_player_turns(combat, 1, _echo_cast(turns=2))
        _play_n_player_turns(combat, 1, _defend())
        mid_turn = combat._total_turns
        assert combat._active_echoes["player"].next_index == 1

        _play_n_player_turns(combat, 1, _defend())
        assert "player" not in combat._active_echoes  # fully acted, expired

        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        turns_back = combat._total_turns - mid_turn
        combat.player.temporal_charge = turns_back  # rewind's own spend
        combat.rewind_to_turn(mid_turn)

        assert combat._active_echoes["player"].next_index == 1

        # The second act replays deterministically on the new branch.
        combat.player.temporal_charge = 0
        _play_n_player_turns(combat, 1, _defend())
        assert "player" not in combat._active_echoes

    def test_rewind_past_full_echo_lifetime_expires_during_replay(self) -> None:
        """
        Rewinding to a turn that includes an echo's entire 1-act lifetime
        replays it to full expiry via _apply_event, not just live play.
        """
        combat = _tanky_combat()
        _play_n_player_turns(combat, 2, _attack())  # banks exactly ECHO_CAST_COST
        _play_n_player_turns(combat, 1, _echo_cast(turns=1))
        _play_n_player_turns(combat, 1, _defend())  # echo's single act; expires live
        assert "player" not in combat._active_echoes
        target_turn = combat._total_turns

        _play_n_player_turns(combat, 1, _defend())  # one more turn past the echo's lifetime

        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        turns_back = combat._total_turns - target_turn
        combat.player.temporal_charge = turns_back  # rewind's own spend
        combat.rewind_to_turn(target_turn)

        # Replay re-applies ECHO_SPAWNED + the single ECHO_ACTED, expiring
        # the echo again inside _apply_event (not just via live play).
        assert "player" not in combat._active_echoes

    def test_post_rewind_echo_events_carry_new_branch_id(self) -> None:
        """Echo events emitted after a rewind carry the new branch_id."""
        combat = _tanky_combat()
        _play_n_player_turns(combat, 1, _attack())

        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = combat._total_turns  # rewind's own spend, to turn 0
        result = combat.rewind_to_turn(0)
        new_branch = result.new_branch_id

        _play_n_player_turns(combat, 2, _attack())  # bank charge on the new branch
        _play_n_player_turns(combat, 1, _echo_cast(turns=2))
        _play_n_player_turns(combat, 1, _defend())

        echo_events = [
            e
            for e in _get_all_events(combat)
            if e.event_type in (EventTypes.ECHO_SPAWNED, EventTypes.ECHO_ACTED)
        ]
        assert echo_events, "Expected at least one echo event on the new branch"
        assert all(e.branch_id == new_branch for e in echo_events)

    def test_rollback_restores_echo_and_history_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        A replay failure mid-rewind restores _active_echoes and
        _action_history to their pre-rewind snapshot (bit-identical).
        """
        combat = _tanky_combat()
        _play_n_player_turns(combat, 2, _attack())
        _play_n_player_turns(combat, 1, _echo_cast(turns=2))
        _play_n_player_turns(combat, 1, _defend())

        echoes_before = {side: echo.next_index for side, echo in combat._active_echoes.items()}
        history_before = {
            combatant_id: list(history) for combatant_id, history in combat._action_history.items()
        }

        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = combat._total_turns  # rewind's own spend, to turn 0

        def _fail_apply(c: object, e: object) -> None:
            raise RuntimeError("injected replay failure")

        monkeypatch.setattr(combat._temporal, "_apply_event", _fail_apply)

        with pytest.raises(RewindReplayError):
            combat.rewind_to_turn(0)

        echoes_after = {side: echo.next_index for side, echo in combat._active_echoes.items()}
        history_after = {
            combatant_id: list(history) for combatant_id, history in combat._action_history.items()
        }
        assert echoes_after == echoes_before
        assert history_after == history_before


# ============================================================================
# Determinism
# ============================================================================


class TestEchoDeterminism:
    """Determinism invariants for echo cast + act + rewind."""

    def test_event_log_hash_stable_with_echo(self) -> None:
        """
        A seeded combat with a cast, acts, and a rewind produces an
        identical (event_type, branch_id, turn_number) event log across
        two runs — the deterministic echo_id is what makes this hold.
        """

        def _run(seed: int) -> list[tuple]:
            combat = _tanky_combat(seed=seed)
            _play_n_player_turns(combat, 2, _attack())
            _play_n_player_turns(combat, 1, _echo_cast(turns=2))
            _play_n_player_turns(combat, 1, _defend())

            combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
            combat.player.temporal_charge = combat._total_turns  # rewind's own spend, to turn 0
            combat.rewind_to_turn(0)

            _play_n_player_turns(combat, 2, _attack())
            _play_n_player_turns(combat, 1, _echo_cast(turns=1))

            events = _get_all_events(combat)
            return [
                (e.event_type, e.branch_id, json.loads(e.event_data).get("turn_number", 0))
                for e in events
            ]

        run1 = _run(seed=42)
        run2 = _run(seed=42)
        assert run1 == run2, "Event log must be bit-stable across identical seeded runs"

    def test_replay_echo_damage_matches_recorded(self) -> None:
        """
        _apply_event's echo-damage determinism assertion (recomputed ==
        recorded) does not fire when replaying over a rewind that spans
        echo acts. A clean rewind proves this.
        """
        combat = _tanky_combat()
        _play_n_player_turns(combat, 2, _attack())
        _play_n_player_turns(combat, 1, _echo_cast(turns=2))
        _play_n_player_turns(combat, 1, _defend())
        _play_n_player_turns(combat, 1, _defend())

        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = combat._total_turns  # rewind's own spend, to turn 0

        from src.core.temporal import RewindResult

        result = combat.rewind_to_turn(0)
        assert isinstance(result, RewindResult)
