"""Unit tests for the Chronomancer archetype, its counter policy and the enemy rewind gate."""

import random

import pytest

from src.core.ai import (
    CHRONO_MAX_REWINDS,
    AIArchetype,
    ChronomancerAI,
    CombatState,
    create_enemy_ai,
)
from src.core.combat import CombatContext, CombatPhase
from src.core.exceptions import RewindUnavailableError
from src.core.persistence import EventStore
from src.core.temporal import (
    COUNTER_STOP_COST,
    ArchetypeCounterPolicy,
    CounterStopResult,
    NeverCounterPolicy,
    RewindResult,
    TemporalAnnouncement,
)
from src.entities import Enemy, Player
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player

_ANNOUNCEMENT = TemporalAnnouncement(
    ability="rewind", caster_id="player_1", magnitude=1, turn_number=3
)


def _mage(hp_pct: int = 100, charge: int = 0, enemy_id: str = "enemy_1") -> Enemy:
    return create_test_enemy(
        id=enemy_id,
        hp=hp_pct * 10,
        max_hp=1000,
        temporal_charge=charge,
        archetype="chronomancer",
    )


def _state(
    mage: Enemy,
    player_charge: int = 0,
    allies: int = 0,
    history: int = 1,
    prior_rewinds: int = 0,
    total_turns: int = 4,
    echo_active: bool = False,
) -> CombatState:
    others = [create_test_enemy(id=f"ally_{i}") for i in range(allies)]
    return CombatState(
        player=create_test_player(temporal_charge=player_charge),
        enemies=[mage, *others],
        round_number=2,
        total_turns=total_turns,
        rewind_counts={mage.id: prior_rewinds},
        history_lengths={mage.id: history},
        enemy_echo_active=echo_active,
    )


def _ai(mage: Enemy, seed: int = 7) -> ChronomancerAI:
    return ChronomancerAI(mage, random.Random(seed))


class TestRewindRule:
    def test_rewinds_below_hp_threshold(self) -> None:
        mage = _mage(hp_pct=39, charge=1)
        assert _ai(mage).select_action(_state(mage)).action_type == "rewind"

    def test_no_rewind_at_threshold(self) -> None:
        mage = _mage(hp_pct=40, charge=1)
        assert _ai(mage).select_action(_state(mage, allies=1)).action_type != "rewind"

    def test_no_rewind_without_charge(self) -> None:
        mage = _mage(hp_pct=10, charge=0)
        assert _ai(mage).select_action(_state(mage)).action_type != "rewind"

    def test_no_rewind_at_turn_zero(self) -> None:
        mage = _mage(hp_pct=10, charge=1)
        assert _ai(mage).select_action(_state(mage, total_turns=0)).action_type != "rewind"

    def test_rewind_cap(self) -> None:
        mage = _mage(hp_pct=10, charge=3)
        under = _state(mage, prior_rewinds=CHRONO_MAX_REWINDS - 1, allies=1)
        at_cap = _state(mage, prior_rewinds=CHRONO_MAX_REWINDS, allies=1)

        assert _ai(mage).select_action(under).action_type == "rewind"
        assert _ai(mage).select_action(at_cap).action_type != "rewind"

    def test_hoard_guard_does_not_suppress_rewind(self) -> None:
        mage = _mage(hp_pct=10, charge=3)
        assert _ai(mage).select_action(_state(mage, player_charge=3)).action_type == "rewind"

    def test_rewind_beats_echo(self) -> None:
        mage = _mage(hp_pct=10, charge=3)
        assert _ai(mage).select_action(_state(mage, history=3)).action_type == "rewind"


class TestEchoRule:
    def test_echoes_when_last_enemy_standing(self) -> None:
        mage = _mage(charge=2)
        action = _ai(mage).select_action(_state(mage))
        assert action.action_type == "echo_cast"
        assert action.target_id == mage.id

    def test_no_echo_with_living_allies(self) -> None:
        mage = _mage(charge=2)
        assert _ai(mage).select_action(_state(mage, allies=1)).action_type != "echo_cast"

    def test_dead_allies_do_not_count(self) -> None:
        mage = _mage(charge=2)
        state = _state(mage, allies=1)
        state.enemies[1].hp = 0
        assert _ai(mage).select_action(state).action_type == "echo_cast"

    @pytest.mark.parametrize(("history", "turns"), [(1, 1), (2, 2), (3, 3)])
    def test_echo_window_is_the_whole_history(self, history: int, turns: int) -> None:
        mage = _mage(charge=2)
        assert _ai(mage).select_action(_state(mage, history=history)).echo_turns == turns

    def test_no_echo_without_history(self) -> None:
        mage = _mage(charge=3)
        assert _ai(mage).select_action(_state(mage, history=0)).action_type != "echo_cast"

    def test_no_echo_below_cost(self) -> None:
        mage = _mage(charge=1)
        assert _ai(mage).select_action(_state(mage)).action_type != "echo_cast"

    def test_no_second_echo_while_one_is_live(self) -> None:
        mage = _mage(charge=3)
        assert _ai(mage).select_action(_state(mage, echo_active=True)).action_type != "echo_cast"

    @pytest.mark.parametrize(("player_charge", "echoes"), [(1, True), (2, False), (3, False)])
    def test_hoard_guard(self, player_charge: int, echoes: bool) -> None:
        mage = _mage(charge=3)
        action = _ai(mage).select_action(_state(mage, player_charge=player_charge))
        assert (action.action_type == "echo_cast") is echoes


class TestRandomness:
    def test_rules_draw_nothing(self) -> None:
        mage = _mage(hp_pct=10, charge=1)
        ai = _ai(mage)
        before = ai.rng.getstate()
        ai.select_action(_state(mage))
        ai.wants_counter_stop(_ANNOUNCEMENT, _state(mage))
        assert ai.rng.getstate() == before

    def test_fall_through_is_the_weighted_mix_and_draws_once(self) -> None:
        mage = _mage()
        ai, twin = _ai(mage, seed=11), random.Random(11)
        action = ai.select_action(_state(mage, allies=1))
        expected = twin.choices(["attack", "defend", "ability"], weights=[45, 35, 20], k=1)[0]

        assert action.action_type == expected
        assert ai.rng.getstate() == twin.getstate()

    def test_holds_no_state_of_its_own(self) -> None:
        mage = _mage()
        assert set(vars(_ai(mage))) == {"enemy", "rng", "base_weights"}

    def test_rejects_a_non_state(self) -> None:
        with pytest.raises(TypeError):
            _ai(_mage()).select_action("nope")  # type: ignore[arg-type]


class TestCounterDecision:
    def test_chronomancer_always_wants_to_counter(self) -> None:
        mage = _mage()
        assert _ai(mage).wants_counter_stop(_ANNOUNCEMENT, _state(mage)) is True

    @pytest.mark.parametrize(
        "archetype",
        [
            AIArchetype.AGGRESSIVE,
            AIArchetype.DEFENSIVE,
            AIArchetype.TACTICAL,
            AIArchetype.BERSERKER,
        ],
    )
    def test_other_archetypes_never_do(self, archetype: AIArchetype) -> None:
        enemy = create_test_enemy()
        ai = create_enemy_ai(enemy, archetype, random.Random(1))
        assert ai.wants_counter_stop(_ANNOUNCEMENT, _state(enemy)) is False

    def test_factory_builds_a_chronomancer(self) -> None:
        ai = create_enemy_ai(_mage(), AIArchetype.CHRONOMANCER, random.Random(1))
        assert isinstance(ai, ChronomancerAI)


def _combat(enemies: list[Enemy], player: Player | None = None, seed: int = 42) -> CombatContext:
    return CombatContext(
        combat_id="combat_001",
        seed=seed,
        player=player or create_test_player(hp=100_000, max_hp=100_000, speed=99),
        enemies=enemies,
        event_store=EventStore(":memory:"),
        session_id="sess_001",
        timeline_id="timeline_main",
    )


class TestArchetypeCounterPolicy:
    def test_is_the_default_policy(self) -> None:
        combat = _combat([_mage()])
        assert isinstance(combat.temporal_system._counter_policy, ArchetypeCounterPolicy)

    def test_picks_the_first_willing_eligible_enemy(self) -> None:
        grunt = create_test_enemy(id="grunt", temporal_charge=3)
        first = _mage(charge=3, enemy_id="mage_a")
        second = _mage(charge=3, enemy_id="mage_b")
        combat = _combat([grunt, first, second])

        chosen = ArchetypeCounterPolicy().decide(combat, _ANNOUNCEMENT, [grunt, first, second])

        assert chosen is first

    def test_without_a_chronomancer_nobody_counters(self) -> None:
        grunts = [create_test_enemy(id=f"g{i}", temporal_charge=3) for i in range(2)]
        combat = _combat(grunts)

        assert ArchetypeCounterPolicy().decide(combat, _ANNOUNCEMENT, grunts) is None
        assert NeverCounterPolicy().decide(combat, _ANNOUNCEMENT, grunts) is None

    def test_player_side_never_counters(self) -> None:
        combat = _combat([_mage()])
        combat.player.temporal_charge = 3
        enemy_cast = TemporalAnnouncement(
            ability="rewind", caster_id="enemy_1", magnitude=1, turn_number=3
        )

        assert ArchetypeCounterPolicy().decide(combat, enemy_cast, [combat.player]) is None

    def test_chronomancer_counters_a_player_rewind_through_the_window(self) -> None:
        mage = _mage()
        combat = _combat([mage])
        combat.start_round()
        combat.submit_player_action(_attack(mage.id))
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1
        mage.temporal_charge = COUNTER_STOP_COST

        result = combat.temporal_system.rewind(combat, combat.player, turns=1)

        assert isinstance(result, CounterStopResult)
        assert result.responder_id == mage.id
        assert mage.temporal_charge == 0
        assert combat._current_branch_id == 0


def _attack(target_id: str):  # type: ignore[no-untyped-def]
    from src.core.ai import CombatAction

    return CombatAction(action_type="attack", target_id=target_id)


class TestEnemyRewindGate:
    def _at_enemy_turn(self) -> tuple[CombatContext, Enemy]:
        mage = _mage(charge=0)
        other = create_test_enemy(id="other", speed=1)
        combat = _combat([mage, other])
        combat.start_round()
        combat.submit_player_action(_attack(mage.id))
        combat.advance_turn()
        assert combat.current_combatant is mage
        assert combat.phase is CombatPhase.EXECUTING_TURN
        return combat, mage

    def test_current_enemy_may_rewind_before_its_turn_resolves(self) -> None:
        combat, mage = self._at_enemy_turn()
        mage.temporal_charge = 1
        hp_after_hit = mage.hp

        result = combat.temporal_system.rewind(combat, mage, turns=1)

        assert isinstance(result, RewindResult)
        assert (result.from_turn, result.to_turn) == (1, 0)
        assert mage.hp > hp_after_hit
        assert combat.phase is CombatPhase.AWAITING_PLAYER_INPUT
        assert combat.current_combatant is combat.player

    def test_enemy_that_is_not_current_may_not(self) -> None:
        combat, _ = self._at_enemy_turn()
        other = combat.enemies[1]
        other.temporal_charge = 1

        with pytest.raises(RewindUnavailableError):
            combat.temporal_system.rewind(combat, other, turns=1)

    def test_player_still_may_not_rewind_during_an_enemy_turn(self) -> None:
        combat, _ = self._at_enemy_turn()
        combat.player.temporal_charge = 1

        with pytest.raises(RewindUnavailableError):
            combat.temporal_system.rewind(combat, combat.player, turns=1)


class TestRewindCountReadModel:
    def test_counts_completed_rewinds_per_caster_and_survives_them(self) -> None:
        mage = _mage()
        combat = _combat([mage])
        assert combat.temporal_rewind_count(mage.id) == 0

        for expected in (1, 2):
            if combat.phase is not CombatPhase.AWAITING_PLAYER_INPUT:
                combat.start_round()
            combat.submit_player_action(_attack(mage.id))
            combat.advance_turn()
            mage.temporal_charge = 1
            combat.temporal_system.rewind(combat, mage, turns=1)
            assert combat.temporal_rewind_count(mage.id) == expected

        assert combat.temporal_rewind_count(combat.player.id) == 0
        assert combat.ai_state().rewind_counts == {mage.id: 2}
