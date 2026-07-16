"""
Integration tests for Phase 3 Step 6 Counter-Stop.

Verifies end-to-end combat -> announce -> counter (or not) scenarios,
rewind interop (the §5 no-new-handlers property: a countered cast is just
2 rewindable CHARGE_SPENTs + 1 persistent COUNTER_STOP_TRIGGERED, so it
falls out correctly on either side of a later rewind with zero special
handling), and determinism.

Uses natural charge economy (regen via start_round(), 1/round for both
sides simultaneously) rather than hand-assigning temporal_charge whenever a
rewind follows in the same test — see test_echo_scenarios.py's module
docstring for the full rationale (a hand-assigned value not backed by real
CHARGE_REGENERATED events makes replay legitimately fail once it reaches
the corresponding CHARGE_SPENT). Charge is only hand-assigned for a
rewind's own spend, which is always safe (stamped at the pre-rewind turn,
outside the replay window).
"""

from __future__ import annotations

import json

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatPhase
from src.core.events import EventTypes
from src.core.persistence import EventStore
from src.core.temporal import (
    CounterStopPolicy,
    CounterStopResult,
    EchoCastResult,
    RewindResult,
    TemporalAnnouncement,
)
from src.entities import Combatant, Enemy, Player
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player

# ============================================================================
# Test policies
# ============================================================================


class ScriptedPolicy:
    """Test policy: pops a scripted response per call (see test_counter_stop.py)."""

    def __init__(self, responses: list[Combatant | None]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[TemporalAnnouncement, list[Combatant]]] = []

    def decide(
        self,
        combat: CombatContext,
        announcement: TemporalAnnouncement,
        eligible: list[Combatant],
    ) -> Combatant | None:
        self.calls.append((announcement, list(eligible)))
        return self.responses.pop(0)


class AlwaysFirstEligiblePolicy:
    """Test policy: always counters with the first eligible responder."""

    def decide(
        self,
        combat: CombatContext,
        announcement: TemporalAnnouncement,
        eligible: list[Combatant],
    ) -> Combatant | None:
        return eligible[0]


# ============================================================================
# Helpers
# ============================================================================


def _attack(target_id: str = "enemy_1") -> CombatAction:
    """Return an attack CombatAction targeting the given ID."""
    return CombatAction(action_type="attack", target_id=target_id)


def _echo_cast(turns: int = 1, actor_id: str = "player_1") -> CombatAction:
    """Return an echo_cast CombatAction requesting the given duration."""
    return CombatAction(action_type="echo_cast", target_id=actor_id, echo_turns=turns)


def _build_combat(
    player: Player | None = None,
    enemies: list[Enemy] | None = None,
    policy: CounterStopPolicy | None = None,
    seed: int = 42,
    event_store: EventStore | None = None,
) -> CombatContext:
    """
    Build a tanky CombatContext with the given (or default) counter policy.

    Both sides default to 100k HP / 0 starting charge / 5 max charge, so
    a many-turn scenario never ends combat early and charge accrues purely
    from natural per-round regen.
    """
    if player is None:
        player = create_test_player(
            hp=100_000, max_hp=100_000, temporal_charge=0, max_temporal_charge=5, attack=50
        )
    if enemies is None:
        enemies = [
            create_test_enemy(
                hp=100_000, max_hp=100_000, defense=25, temporal_charge=0, max_temporal_charge=5
            )
        ]
    if event_store is None:
        event_store = EventStore(":memory:")

    return CombatContext(
        combat_id="combat_001",
        seed=seed,
        player=player,
        enemies=enemies,
        event_store=event_store,
        session_id="sess_001",
        timeline_id="timeline_main",
        counter_policy=policy,
    )


def _play_n_player_turns(combat: CombatContext, n: int, action: CombatAction) -> None:
    """
    Advance *n* player turns in a round-aware loop (mirrors
    test_echo_scenarios.py's helper of the same name).
    """
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


def _get_all_events(combat: CombatContext) -> list:
    """Return all events for this combat's timeline."""
    return combat._event_store.get_events_by_timeline(combat._timeline_id)


# ============================================================================
# Full combat scenarios
# ============================================================================


class TestFullCombatWithCounteredRewind:
    """test_full_combat_with_countered_rewind."""

    def test_full_combat_with_countered_rewind(self) -> None:
        """
        Both sides bank 3 charge naturally; the player rewinds; the enemy
        counters. Combat continues on branch 0 with intact turn structure.
        """
        player = create_test_player(
            hp=100_000, max_hp=100_000, temporal_charge=0, max_temporal_charge=5, attack=50
        )
        enemy = create_test_enemy(
            hp=100_000, max_hp=100_000, defense=25, temporal_charge=0, max_temporal_charge=5
        )
        policy = ScriptedPolicy([enemy])
        combat = _build_combat(player=player, enemies=[enemy], policy=policy)

        _play_n_player_turns(combat, 3, _attack())
        assert combat.player.temporal_charge == 3
        assert enemy.temporal_charge == 3

        branch_before = combat._current_branch_id
        total_before = combat._total_turns
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT

        result = combat._temporal.rewind(combat, combat.player, turns=1)

        assert isinstance(result, CounterStopResult)
        assert combat._current_branch_id == branch_before
        assert combat._total_turns == total_before
        assert combat.player.temporal_charge == 2  # spent 1 (the rewind's own cost)
        assert enemy.temporal_charge == 0  # spent its whole pool (3) countering

        # Combat continues normally afterward, same branch.
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        msgs = combat.submit_player_action(_attack())
        assert msgs

        types = [e.event_type for e in _get_all_events(combat)]
        assert types.count(EventTypes.COUNTER_STOP_TRIGGERED) == 1
        assert types.count(EventTypes.TEMPORAL_REWIND) == 0


class TestCounteredEchoThenSuccessfulRecast:
    """test_countered_echo_then_successful_recast."""

    def test_countered_echo_then_successful_recast(self) -> None:
        """
        A counter drains the enemy to 0; the player re-accumulates charge
        and the re-cast goes through uncontested (responder no longer
        eligible, so the window is skipped, not merely declined).
        """
        player = create_test_player(
            hp=100_000, max_hp=100_000, temporal_charge=0, max_temporal_charge=5, attack=50
        )
        enemy = create_test_enemy(
            hp=100_000, max_hp=100_000, defense=25, temporal_charge=0, max_temporal_charge=5
        )
        policy = ScriptedPolicy([enemy])
        combat = _build_combat(player=player, enemies=[enemy], policy=policy)

        # 3 rounds bank 3 charge each side — the enemy needs >= COUNTER_STOP_COST
        # (3) to be eligible for the first counter.
        _play_n_player_turns(combat, 3, _attack())
        assert enemy.temporal_charge == 3

        result = combat._temporal.echo_cast(combat, combat.player, turns=1)
        assert isinstance(result, CounterStopResult)
        assert combat.player.temporal_charge == 1  # 3 - ECHO_CAST_COST(2)
        assert enemy.temporal_charge == 0  # spent its whole pool countering
        assert combat._active_echoes == {}

        # Re-accumulate: 2 more rounds bank 2 more charge for both sides.
        # The player reaches 3 (>= ECHO_CAST_COST); the enemy reaches only 2,
        # still under COUNTER_STOP_COST — ineligible for a second counter.
        _play_n_player_turns(combat, 2, _attack())
        assert combat.player.temporal_charge == 3
        assert enemy.temporal_charge == 2

        result2 = combat._temporal.echo_cast(combat, combat.player, turns=1)
        assert isinstance(result2, EchoCastResult)
        assert len(policy.calls) == 1  # window was skipped the second time, not declined
        assert "player" in combat._active_echoes


# ============================================================================
# Rewind interop
# ============================================================================


class TestRewindCounterInterop:
    """The §5 no-new-handlers property, exercised across a countered cast."""

    def test_rewind_before_countered_cast_refunds_both_sides(self) -> None:
        """
        Rewinding to a turn before a countered cast excludes both
        CHARGE_SPENTs from replay: both charge pools reflect the exclusion,
        while COUNTER_STOP_TRIGGERED remains queryable (persistent).
        """
        player = create_test_player(
            hp=100_000, max_hp=100_000, temporal_charge=0, max_temporal_charge=5, attack=50
        )
        enemy = create_test_enemy(
            hp=100_000, max_hp=100_000, defense=25, temporal_charge=0, max_temporal_charge=5
        )
        policy = ScriptedPolicy([enemy])
        combat = _build_combat(player=player, enemies=[enemy], policy=policy)

        _play_n_player_turns(combat, 1, _attack())
        target_turn = combat._total_turns

        _play_n_player_turns(combat, 2, _attack())  # bank the rest of the 3 needed
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat._temporal.rewind(combat, combat.player, turns=1)  # countered

        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = combat._total_turns - target_turn  # rewind's own spend
        combat.rewind_to_turn(target_turn)

        # Both the caster's and responder's CHARGE_SPENT for the countered
        # cast (and every round after target_turn) are excluded from the
        # replay window — only the single regen tick from round 1 (before
        # target_turn) survives, for both sides.
        assert combat.player.temporal_charge == 1
        assert enemy.temporal_charge == 1  # never spent on this branch

        trigger_events = [
            e for e in _get_all_events(combat) if e.event_type == EventTypes.COUNTER_STOP_TRIGGERED
        ]
        assert len(trigger_events) == 1  # persistent — still in the log

    def test_rewind_after_countered_cast_replays_charge_spends(self) -> None:
        """
        Rewinding to a turn *after* a countered cast replays both
        CHARGE_SPENTs; live charge totals match the pre-rewind values
        bit-exactly.
        """
        player = create_test_player(
            hp=100_000, max_hp=100_000, temporal_charge=0, max_temporal_charge=5, attack=50
        )
        enemy = create_test_enemy(
            hp=100_000, max_hp=100_000, defense=25, temporal_charge=0, max_temporal_charge=5
        )
        policy = ScriptedPolicy([enemy])
        combat = _build_combat(player=player, enemies=[enemy], policy=policy)

        _play_n_player_turns(combat, 3, _attack())
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat._temporal.rewind(combat, combat.player, turns=1)  # countered
        target_turn = combat._total_turns

        player_charge_before = combat.player.temporal_charge
        enemy_charge_before = enemy.temporal_charge

        _play_n_player_turns(combat, 1, _attack())  # one more turn past the countered cast

        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = combat._total_turns - target_turn  # rewind's own spend
        combat.rewind_to_turn(target_turn)

        assert combat.player.temporal_charge == player_charge_before
        assert enemy.temporal_charge == enemy_charge_before


# ============================================================================
# Chess-clock scenario (DESIGN success criterion)
# ============================================================================


class TestChessClockScenario:
    """test_chess_clock_scenario."""

    def test_chess_clock_scenario(self) -> None:
        """
        DESIGN's success criterion: a combat featuring 1 rewind, 1 echo
        cast, and 1 counter-stop completes deterministically.
        """
        player = create_test_player(
            hp=100_000, max_hp=100_000, temporal_charge=0, max_temporal_charge=5, attack=50
        )
        enemy = create_test_enemy(
            hp=100_000, max_hp=100_000, defense=25, temporal_charge=0, max_temporal_charge=5
        )
        policy = AlwaysFirstEligiblePolicy()
        combat = _build_combat(player=player, enemies=[enemy], policy=policy)

        # 1. Echo cast — countered. 3 rounds bank 3 charge each side, making
        # the enemy eligible (>= COUNTER_STOP_COST) for AlwaysFirstEligiblePolicy.
        _play_n_player_turns(combat, 3, _attack())
        assert combat.player.temporal_charge == 3
        assert enemy.temporal_charge == 3

        cast_result = combat._temporal.echo_cast(combat, combat.player, turns=1)
        assert isinstance(cast_result, CounterStopResult)
        assert combat.player.temporal_charge == 1  # 3 - ECHO_CAST_COST(2)
        assert enemy.temporal_charge == 0  # spent its whole pool countering
        assert combat._active_echoes == {}

        # 2. Rewind — 2 more rounds bank the player back up to 3, but the
        # enemy only reaches 2 (still under COUNTER_STOP_COST), so this one
        # goes through uncontested (window skipped: no eligible responder).
        _play_n_player_turns(combat, 2, _attack())
        assert combat.player.temporal_charge == 3
        assert enemy.temporal_charge == 2

        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        rewind_result = combat._temporal.rewind(combat, combat.player, turns=1)
        assert isinstance(rewind_result, RewindResult)

        assert not combat.is_over


# ============================================================================
# Determinism
# ============================================================================


class TestCounterStopDeterminism:
    """test_event_log_hash_stable_with_counter."""

    def test_event_log_hash_stable_with_counter(self) -> None:
        """
        A seeded combat including a countered cast, run twice, produces an
        identical (event_type, branch_id, turn_number) event log.
        """

        def _run(seed: int) -> list[tuple]:
            player = create_test_player(
                hp=100_000, max_hp=100_000, temporal_charge=0, max_temporal_charge=5, attack=50
            )
            enemy = create_test_enemy(
                hp=100_000, max_hp=100_000, defense=25, temporal_charge=0, max_temporal_charge=5
            )
            policy = ScriptedPolicy([enemy])
            combat = _build_combat(player=player, enemies=[enemy], policy=policy, seed=seed)

            _play_n_player_turns(combat, 3, _attack())
            combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
            combat._temporal.rewind(combat, combat.player, turns=1)  # countered

            events = _get_all_events(combat)
            return [
                (e.event_type, e.branch_id, json.loads(e.event_data).get("turn_number", 0))
                for e in events
            ]

        run1 = _run(seed=42)
        run2 = _run(seed=42)
        assert run1 == run2, "Event log must be bit-stable across identical seeded runs"
