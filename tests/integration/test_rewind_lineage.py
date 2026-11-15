"""Replay correctness: branch lineage, shield breaks and break recovery."""

import pytest

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatPhase
from src.core.exceptions import InsufficientChargeError
from src.core.persistence import EventStore
from src.core.temporal import RewindResult
from src.entities import DamageType, Enemy
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player


def _combat() -> tuple[CombatContext, Enemy]:
    enemy = create_test_enemy(hp=100_000, max_hp=100_000)
    combat = CombatContext(
        combat_id="combat_001",
        seed=42,
        player=create_test_player(hp=100_000, max_hp=100_000, speed=99),
        enemies=[enemy],
        event_store=EventStore(":memory:"),
        session_id="sess_001",
        timeline_id="timeline_main",
    )
    return combat, enemy


def _finish_round(combat: CombatContext, enemy: Enemy) -> None:
    combat.submit_player_action(CombatAction(action_type="attack", target_id=enemy.id))
    combat.advance_turn()
    while combat.phase is CombatPhase.EXECUTING_TURN:
        combat.execute_enemy_turn(enemy)
        combat.advance_turn()


def _state(combat: CombatContext, enemy: Enemy) -> tuple[int, int, int, int]:
    return (combat.player.hp, enemy.hp, combat._total_turns, combat.round_number)


def test_second_rewind_ignores_the_abandoned_tail_of_the_first_branch() -> None:
    combat, enemy = _combat()
    seen: dict[int, tuple[int, int, int, int]] = {}
    for _ in range(3):
        combat.start_round()
        _finish_round(combat, enemy)
    combat.start_round()

    first = combat.temporal_system.rewind(combat, combat.player, turns=2)
    assert isinstance(first, RewindResult)
    assert (first.from_turn, first.to_turn) == (6, 4)

    # Live on branch 1: turns 5 and 6 replace the abandoned ones, then a full round.
    _finish_round(combat, enemy)
    seen[combat._total_turns] = _state(combat, enemy)
    combat.start_round()
    _finish_round(combat, enemy)
    combat.start_round()
    combat.player.temporal_charge = 3
    assert combat._total_turns == 8

    second = combat.temporal_system.rewind(combat, combat.player, turns=2)

    assert isinstance(second, RewindResult)
    assert (second.from_turn, second.to_turn, second.new_branch_id) == (8, 6, 2)
    assert _state(combat, enemy)[:3] == seen[6][:3]


def test_rewinding_past_an_earlier_fork_lands_on_the_original_line() -> None:
    combat, enemy = _combat()
    combat.start_round()
    _finish_round(combat, enemy)
    after_round_one = _state(combat, enemy)
    for _ in range(2):
        combat.start_round()
        _finish_round(combat, enemy)
    combat.start_round()
    combat.temporal_system.rewind(combat, combat.player, turns=3)
    _finish_round(combat, enemy)
    combat.start_round()
    combat.player.temporal_charge = 3
    assert combat._total_turns == 5

    result = combat.temporal_system.rewind(combat, combat.player, turns=3)

    assert isinstance(result, RewindResult)
    assert result.to_turn == 2
    assert _state(combat, enemy)[:3] == after_round_one[:3]


def test_rejected_echo_cast_leaves_the_turn_with_the_player() -> None:
    combat, enemy = _combat()
    combat.start_round()
    turns_before = combat._total_turns

    with pytest.raises(InsufficientChargeError):
        combat.submit_player_action(CombatAction(action_type="echo_cast", target_id=""))

    assert combat.phase is CombatPhase.AWAITING_PLAYER_INPUT
    assert combat._total_turns == turns_before
    combat.submit_player_action(CombatAction(action_type="attack", target_id=enemy.id))
    assert enemy.hp < enemy.max_hp


def _breakable() -> tuple[CombatContext, Enemy]:
    enemy = create_test_enemy(
        hp=100_000,
        max_hp=100_000,
        shield_points=1,
        max_shield_points=1,
        weaknesses=[DamageType.PHYSICAL],
    )
    combat = CombatContext(
        combat_id="combat_001",
        seed=42,
        player=create_test_player(hp=100_000, max_hp=100_000, speed=99),
        enemies=[enemy],
        event_store=EventStore(":memory:"),
        session_id="sess_001",
        timeline_id="timeline_main",
    )
    return combat, enemy


def test_rewind_across_a_shield_break_rebuilds_the_break() -> None:
    combat, enemy = _breakable()
    combat.start_round()
    combat.submit_player_action(CombatAction(action_type="attack", target_id=enemy.id))
    assert enemy.is_broken
    broken_hp = enemy.hp
    combat.advance_turn()
    combat.execute_enemy_turn(enemy)
    combat.advance_turn()
    assert not enemy.is_broken
    combat.start_round()
    combat.player.temporal_charge = 1

    result = combat.temporal_system.rewind(combat, combat.player, turns=1)

    assert isinstance(result, RewindResult)
    assert result.to_turn == 1
    assert enemy.is_broken
    assert enemy.shield_points == 0
    assert enemy.hp == broken_hp


def test_rewind_after_break_recovery_rebuilds_the_recovery() -> None:
    combat, enemy = _breakable()
    for _ in range(3):
        combat.start_round()
        _finish_round(combat, enemy)
    live = (enemy.hp, enemy.is_broken, enemy.shield_points, enemy.break_turns_remaining)
    combat.start_round()
    _finish_round(combat, enemy)
    combat.start_round()
    combat.player.temporal_charge = 2

    result = combat.temporal_system.rewind(combat, combat.player, turns=2)

    assert isinstance(result, RewindResult)
    assert result.to_turn == 6
    assert (enemy.hp, enemy.is_broken, enemy.shield_points, enemy.break_turns_remaining) == live
