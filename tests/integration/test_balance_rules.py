"""Rules added for balance: one Break bonus, a working defend, paid rewinds, own-turn rewinds."""

import json

import pytest

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatPhase
from src.core.events import EventTypes
from src.core.exceptions import InsufficientChargeError, RewindBoundaryError
from src.core.persistence import EventStore
from src.core.temporal import NeverCounterPolicy, RewindResult
from src.entities import DamageType, Enemy, Player
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player


def _combat(
    enemy: Enemy | None = None, player: Player | None = None, seed: int = 42
) -> tuple[CombatContext, Enemy]:
    enemy = enemy or create_test_enemy(hp=100_000, max_hp=100_000)
    combat = CombatContext(
        combat_id="combat_001",
        seed=seed,
        player=player or create_test_player(hp=100_000, max_hp=100_000, speed=99),
        enemies=[enemy],
        event_store=EventStore(":memory:"),
        session_id="sess_001",
        timeline_id="timeline_main",
        counter_policy=NeverCounterPolicy(),
    )
    return combat, enemy


def _attack(enemy: Enemy) -> CombatAction:
    return CombatAction(action_type="attack", target_id=enemy.id)


_DEFEND = CombatAction(action_type="defend", target_id="")


def _round(combat: CombatContext, enemy: Enemy, action: CombatAction) -> None:
    """Play one full round: the player's action, then the enemy's turn."""
    if combat.phase is not CombatPhase.AWAITING_PLAYER_INPUT:
        combat.start_round()
    combat.submit_player_action(action)
    combat.advance_turn()
    while combat.phase is CombatPhase.EXECUTING_TURN:
        combat.execute_enemy_turn(enemy)
        combat.advance_turn()


def _damage_events(combat: CombatContext, actor_id: str) -> list[int]:
    return [
        json.loads(e.event_data)["damage_dealt"]
        for e in combat._event_store.get_events_by_timeline("timeline_main")
        if e.event_type == EventTypes.ACTION_EXECUTED
        and json.loads(e.event_data).get("actor_id") == actor_id
        and json.loads(e.event_data).get("action_type") == "attack"
    ]


class TestBreakBonusAppliedOnce:
    def test_hit_on_a_broken_enemy_is_one_and_a_half_times_not_more(self) -> None:
        def hit(broken: bool) -> int:
            enemy = create_test_enemy(hp=100_000, max_hp=100_000, defense=25)
            combat, _ = _combat(enemy)
            combat.start_round()
            if broken:
                enemy.trigger_break()
            before = enemy.hp
            combat.submit_player_action(_attack(enemy))
            return before - enemy.hp

        plain, broken = hit(broken=False), hit(broken=True)

        # Same seed, same roll: the only difference is the Break bonus.
        assert broken == pytest.approx(plain * 1.5, abs=1)
        assert broken < plain * 2

    def test_hp_lost_equals_the_damage_the_log_reports(self) -> None:
        enemy = create_test_enemy(hp=100_000, max_hp=100_000)
        combat, _ = _combat(enemy)
        combat.start_round()
        enemy.trigger_break()
        before = enemy.hp

        combat.submit_player_action(_attack(enemy))

        assert before - enemy.hp == _damage_events(combat, combat.player.id)[-1]


class TestDefend:
    def test_defending_halves_the_next_hit(self) -> None:
        hits: dict[bool, int] = {}
        for defend in (False, True):
            # Find a seed where the enemy attacks on its first turn in both runs.
            for seed in range(50):
                combat, enemy = _combat(
                    create_test_enemy(hp=100_000, max_hp=100_000, attack=400), seed=seed
                )
                combat.start_round()
                combat.submit_player_action(_DEFEND if defend else _attack(enemy))
                combat.advance_turn()
                before = combat.player.hp
                combat.execute_enemy_turn(enemy)
                if combat.player.hp < before:
                    hits[defend] = before - combat.player.hp
                    assert combat.player.is_defending is defend
                    break
        assert hits[True] * 2 <= hits[False] + 1
        assert hits[True] >= 1

    def test_defend_ends_when_the_defenders_next_turn_begins(self) -> None:
        combat, enemy = _combat()
        _round(combat, enemy, _DEFEND)
        assert combat.player.is_defending

        combat.start_round()
        combat.submit_player_action(_attack(enemy))

        assert not combat.player.is_defending

    def test_a_defending_enemy_takes_half(self) -> None:
        combat, enemy = _combat(create_test_enemy(hp=100_000, max_hp=100_000, defense=25))
        combat.start_round()
        enemy.is_defending = True
        combat.submit_player_action(_attack(enemy))
        halved = _damage_events(combat, combat.player.id)[-1]

        other, other_enemy = _combat(create_test_enemy(hp=100_000, max_hp=100_000, defense=25))
        other.start_round()
        other.submit_player_action(_attack(other_enemy))
        full = _damage_events(other, other.player.id)[-1]

        assert halved == max(1, full // 2)

    def test_rewind_rebuilds_who_is_defending(self) -> None:
        combat, enemy = _combat()
        _round(combat, enemy, _DEFEND)
        hp_after_round_one = combat.player.hp
        _round(combat, enemy, _attack(enemy))
        combat.start_round()
        combat.player.temporal_charge = 1

        result = combat.rewind_player_turns(1)

        assert isinstance(result, RewindResult)
        assert combat.player.is_defending
        assert combat.player.hp == hp_after_round_one


class TestRewindIsPaidFor:
    def test_the_cost_stays_spent_on_the_new_branch(self) -> None:
        combat, enemy = _combat()
        for _ in range(3):
            _round(combat, enemy, _attack(enemy))
        combat.start_round()
        assert combat.player.temporal_charge == 3

        combat.temporal_system.rewind(combat, combat.player, turns=1)

        # One turn back is still inside round 3, where the player held 3.
        assert combat.player.temporal_charge == 2

    def test_a_later_rewind_through_that_point_still_charges_for_it(self) -> None:
        combat, enemy = _combat()
        for _ in range(3):
            _round(combat, enemy, _attack(enemy))
        combat.start_round()
        combat.temporal_system.rewind(combat, combat.player, turns=1)
        paid_once = combat.player.temporal_charge
        _round(combat, enemy, _attack(enemy))
        combat.start_round()
        assert combat.player.temporal_charge == 3

        combat.temporal_system.rewind(combat, combat.player, turns=1)

        # The earlier turn held 2 because the first rewind's cost is replayed
        # with it; this rewind then costs 1 more. Unreplayed, this would be 2.
        assert paid_once == 2
        assert combat.player.temporal_charge == 1

    def test_carried_spend_is_an_event_on_the_new_branch(self) -> None:
        combat, enemy = _combat()
        _round(combat, enemy, _attack(enemy))
        combat.start_round()

        combat.temporal_system.rewind(combat, combat.player, turns=1)

        spends = [
            (e.branch_id, json.loads(e.event_data))
            for e in combat._event_store.get_events_by_timeline("timeline_main")
            if e.event_type == EventTypes.CHARGE_SPENT
        ]
        assert [(b, d.get("carried", False)) for b, d in spends] == [(0, False), (1, True)]

    def test_cost_never_takes_charge_below_zero(self) -> None:
        combat, enemy = _combat()
        _round(combat, enemy, _attack(enemy))
        _round(combat, enemy, _attack(enemy))
        combat.start_round()
        assert combat.player.temporal_charge == 3

        combat.temporal_system.rewind(combat, combat.player, turns=4, cost=3)

        # Turn 0 held round 1's single charge; the cost takes it and no more.
        assert combat.player.temporal_charge == 0


class TestRewindOwnTurns:
    def test_one_turn_back_is_the_start_of_the_last_turn_taken(self) -> None:
        combat, enemy = _combat()
        _round(combat, enemy, _attack(enemy))
        combat.start_round()
        at_turn_start = (combat.player.hp, enemy.hp, combat.round_number, combat._total_turns)
        _round(combat, enemy, _attack(enemy))
        combat.start_round()

        result = combat.rewind_player_turns(1)

        assert isinstance(result, RewindResult)
        assert result.charge_spent == 1
        assert (combat.player.hp, enemy.hp, combat.round_number, combat._total_turns) == (
            at_turn_start
        )
        assert combat.phase is CombatPhase.AWAITING_PLAYER_INPUT
        assert combat.current_combatant is combat.player

    def test_two_enemies_between_turns_still_cost_one_charge(self) -> None:
        enemies = [create_test_enemy(id=f"e{i}", hp=100_000, max_hp=100_000) for i in range(3)]
        combat = CombatContext(
            combat_id="combat_001",
            seed=42,
            player=create_test_player(hp=100_000, max_hp=100_000, speed=99),
            enemies=enemies,
            event_store=EventStore(":memory:"),
            session_id="sess_001",
            timeline_id="timeline_main",
        )
        combat.start_round()
        combat.submit_player_action(_attack(enemies[0]))
        combat.advance_turn()
        while combat.phase is CombatPhase.EXECUTING_TURN:
            combat.execute_enemy_turn(combat.current_combatant)  # type: ignore[arg-type]
            combat.advance_turn()
        combat.start_round()
        assert combat._total_turns == 4

        result = combat.rewind_player_turns(1)

        assert isinstance(result, RewindResult)
        assert (result.from_turn, result.to_turn, result.charge_spent) == (4, 0, 1)

    def test_round_does_not_restart_after_rewinding_to_its_first_turn(self) -> None:
        combat, enemy = _combat()
        _round(combat, enemy, _attack(enemy))
        combat.start_round()
        round_before, bp_before = combat.round_number, combat.player.boost_points
        _round(combat, enemy, _attack(enemy))
        combat.start_round()

        combat.rewind_player_turns(1)
        assert (combat.round_number, combat.player.boost_points) == (round_before, bp_before)

        # Playing on must reach the next round once, not replay this one's start.
        _round(combat, enemy, _attack(enemy))
        combat.start_round()
        assert combat.round_number == round_before + 1
        assert combat.player.boost_points == bp_before + 1

    def test_echo_cast_turns_count_as_turns_taken(self) -> None:
        combat, enemy = _combat()
        _round(combat, enemy, _attack(enemy))
        _round(combat, enemy, _attack(enemy))
        _round(combat, enemy, CombatAction(action_type="echo_cast", target_id="", echo_turns=1))
        combat.start_round()
        assert combat.player_turns_taken == 3

        combat.rewind_player_turns(1)

        assert combat.player_turns_taken == 2
        assert combat._active_echoes == {}

    def test_more_turns_than_taken_or_than_charge_is_refused(self) -> None:
        combat, enemy = _combat()
        _round(combat, enemy, _attack(enemy))
        combat.start_round()

        with pytest.raises(RewindBoundaryError):
            combat.rewind_player_turns(2)
        with pytest.raises(ValueError, match="at least 1"):
            combat.rewind_player_turns(0)

        _round(combat, enemy, _attack(enemy))
        combat.start_round()
        combat.player.temporal_charge = 1
        with pytest.raises(InsufficientChargeError):
            combat.rewind_player_turns(2)


def test_echo_ignores_break_and_defend() -> None:
    enemy = create_test_enemy(hp=100_000, max_hp=100_000, defense=25, weaknesses=[DamageType.FIRE])
    combat, _ = _combat(enemy)
    _round(combat, enemy, _attack(enemy))
    recorded = _damage_events(combat, combat.player.id)[-1]
    _round(combat, enemy, _attack(enemy))
    _round(combat, enemy, CombatAction(action_type="echo_cast", target_id="", echo_turns=1))
    combat.start_round()
    enemy.is_defending = True
    enemy.trigger_break()
    last = _damage_events(combat, combat.player.id)[-1]

    combat.submit_player_action(_DEFEND)

    echo_hits = [
        json.loads(e.event_data)["damage_dealt"]
        for e in combat._event_store.get_events_by_timeline("timeline_main")
        if e.event_type == EventTypes.ECHO_ACTED
    ]
    # Neither the Break bonus nor the defend applies: the echo repeats what was recorded.
    assert echo_hits == [last]
    assert recorded > 0
