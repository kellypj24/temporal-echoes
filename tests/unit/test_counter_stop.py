"""
Unit tests for the Counter-Stop interrupt model — Phase 3 Step 6.

Covers the response window at the unit level: default-policy regression
guards, countered rewind, countered echo cast, and window mechanics
(eligibility, policy contract, event ordering, no-RNG, branch stamping).

Most tests call ``combat._temporal.rewind`` / ``echo_cast`` directly (same
pattern as test_temporal.py / test_echo.py) rather than going through the
full turn dispatcher, so they can control charge and the injected policy
precisely. ``ScriptedPolicy`` pops a response per call and records every
``(announcement, eligible)`` pair it saw, mirroring the plan's test-policy
spec (§7).
"""

from __future__ import annotations

import json

import pytest

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatPhase
from src.core.events import EventTypes, is_rewindable
from src.core.exceptions import InsufficientChargeError
from src.core.persistence import EventStore
from src.core.temporal import (
    COUNTER_STOP_COST,
    ECHO_CAST_COST,
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
    """
    Test policy: pops a scripted response per call, records every
    ``(announcement, eligible)`` pair it was asked to decide on.
    """

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


# ============================================================================
# Helpers
# ============================================================================


def _attack(target_id: str = "enemy_1") -> CombatAction:
    """Return an attack CombatAction targeting the given ID."""
    return CombatAction(action_type="attack", target_id=target_id)


def _build_combat(
    player: Player | None = None,
    enemies: list[Enemy] | None = None,
    policy: CounterStopPolicy | None = None,
    seed: int = 42,
    event_store: EventStore | None = None,
) -> CombatContext:
    """
    Build a CombatContext with the given (or default) counter policy.

    Args:
        player: Player instance (default: standard test player).
        enemies: List of enemies (default: single tanky test enemy).
        policy: CounterStopPolicy to inject (default: NeverCounterPolicy
            via TemporalSystem's own default).
        seed: RNG seed for deterministic replay.
        event_store: EventStore instance (default: in-memory).

    Returns:
        Configured CombatContext ready for testing.
    """
    if player is None:
        player = create_test_player(temporal_charge=0, max_temporal_charge=5, attack=50)
    if enemies is None:
        enemies = [
            create_test_enemy(
                hp=5000, max_hp=5000, defense=25, temporal_charge=0, max_temporal_charge=5
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


def _make_rewindable_combat(
    player_charge: int = 1,
    enemy_charge: int = 3,
    seed: int = 42,
) -> CombatContext:
    """
    Build a CombatContext positioned for a rewind (one completed player
    turn), with charge values assigned directly after setup — bypassing
    per-round regen so exact eligibility thresholds are easy to hit.

    Args:
        player_charge: Player's charge after setup.
        enemy_charge: Enemy's charge after setup.
        seed: RNG seed for the combat.

    Returns:
        CombatContext with _total_turns == 1, AWAITING_PLAYER_INPUT.
    """
    combat = _build_combat(seed=seed)
    combat.start_round()
    combat.submit_player_action(_attack())
    combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
    combat.player.temporal_charge = player_charge
    combat.enemies[0].temporal_charge = enemy_charge
    return combat


def _play_n_player_turns(combat: CombatContext, n: int, action: CombatAction) -> None:
    """
    Advance *n* player turns in a round-aware loop (mirrors
    test_echo.py's / test_rewind_scenarios.py's helper of the same name).
    """
    turns_played = 0
    iterations = 0
    max_iterations = n * 20 + 50
    while turns_played < n:
        iterations += 1
        if iterations > max_iterations:
            raise RuntimeError(
                f"_play_n_player_turns made no progress: stuck in phase "
                f"{combat.phase.name} after {iterations} iterations"
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


def _build_combat_with_history(
    n_actions: int = 1,
    player_charge: int = 2,
    enemy_charge: int = 3,
    seed: int = 42,
) -> CombatContext:
    """
    Build a CombatContext with ``n_actions`` recorded player attacks,
    positioned at AWAITING_PLAYER_INPUT with charge assigned directly.

    Returns:
        CombatContext ready for ``combat._temporal.echo_cast(...)``.
    """
    combat = _build_combat(seed=seed)
    _play_n_player_turns(combat, n_actions, _attack())
    combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
    combat.player.temporal_charge = player_charge
    combat.enemies[0].temporal_charge = enemy_charge
    return combat


def _all_events(combat: CombatContext) -> list:
    """Return all events for this combat's timeline."""
    return combat._event_store.get_events_by_timeline(combat._timeline_id)


# ============================================================================
# Default behavior (regression guard)
# ============================================================================


class TestDefaultPolicyBehavior:
    """NeverCounterPolicy leaves every existing flow behaviorally unchanged."""

    def test_default_policy_rewind_proceeds_unchanged(self) -> None:
        """With no policy injected, rewind() returns RewindResult as before."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=3)
        result = combat._temporal.rewind(combat, combat.player, turns=1)
        assert isinstance(result, RewindResult)

    def test_default_policy_echo_proceeds_unchanged(self) -> None:
        """With no policy injected, echo_cast() returns EchoCastResult as before."""
        combat = _build_combat_with_history(n_actions=1, player_charge=2, enemy_charge=3)
        result = combat._temporal.echo_cast(combat, combat.player, turns=1)
        assert isinstance(result, EchoCastResult)

    def test_no_eligible_responder_skips_policy_entirely(self) -> None:
        """An under-charged enemy means the window is skipped; policy never called."""
        policy = ScriptedPolicy([])
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=2)  # < COUNTER_STOP_COST
        combat._temporal._counter_policy = policy
        result = combat._temporal.rewind(combat, combat.player, turns=1)
        assert isinstance(result, RewindResult)
        assert len(policy.calls) == 0


# ============================================================================
# Countered rewind
# ============================================================================


class TestCounteredRewind:
    """A countered rewind fizzles: no snapshot restore, no branch, no replay."""

    def test_countered_rewind_returns_counter_stop_result(self) -> None:
        """Full CounterStopResult payload shape on a countered rewind."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=3)
        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        result = combat._temporal.rewind(combat, combat.player, turns=1)

        assert isinstance(result, CounterStopResult)
        assert result.countered_ability == "rewind"
        assert result.caster_id == combat.player.id
        assert result.responder_id == combat.enemies[0].id
        assert result.caster_charge_lost == 1
        assert result.responder_charge_spent == COUNTER_STOP_COST

    def test_countered_rewind_leaves_caster_charge_spent(self) -> None:
        """The caster's charge stays spent — countering does not refund it."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=3)
        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        combat._temporal.rewind(combat, combat.player, turns=1)

        assert combat.player.temporal_charge == 0
        assert combat.enemies[0].temporal_charge == 0  # spent its whole pool (3)

    def test_countered_rewind_does_not_bump_branch_or_emit_temporal_rewind(self) -> None:
        """No branch bump, no TEMPORAL_REWIND event for a countered rewind."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=3)
        branch_before = combat._current_branch_id
        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        combat._temporal.rewind(combat, combat.player, turns=1)

        assert combat._current_branch_id == branch_before
        assert not any(e.event_type == EventTypes.TEMPORAL_REWIND for e in _all_events(combat))

    def test_countered_rewind_leaves_combat_state_untouched(self) -> None:
        """HP/turns/phase/RNG are unchanged except the two charge pools."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=3)
        hp_before = combat.player.hp
        enemy_hp_before = combat.enemies[0].hp
        turns_before = combat._total_turns
        phase_before = combat._phase
        rng_before = combat._rng.getstate()

        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        combat._temporal.rewind(combat, combat.player, turns=1)

        assert combat.player.hp == hp_before
        assert combat.enemies[0].hp == enemy_hp_before
        assert combat._total_turns == turns_before
        assert combat._phase == phase_before
        assert combat._rng.getstate() == rng_before

    def test_countered_rewind_event_sequence(self) -> None:
        """caster CHARGE_SPENT -> responder CHARGE_SPENT(3) -> COUNTER_STOP_TRIGGERED."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=3)
        events_before = len(_all_events(combat))
        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        combat._temporal.rewind(combat, combat.player, turns=1)

        new_events = _all_events(combat)[events_before:]
        types = [e.event_type for e in new_events]
        assert types == [
            EventTypes.CHARGE_SPENT,
            EventTypes.CHARGE_SPENT,
            EventTypes.COUNTER_STOP_TRIGGERED,
        ]
        caster_charge, responder_charge, trigger = new_events
        assert json.loads(caster_charge.event_data)["actor_id"] == combat.player.id
        assert json.loads(caster_charge.event_data)["ability"] == "rewind"
        assert json.loads(responder_charge.event_data)["actor_id"] == combat.enemies[0].id
        assert json.loads(responder_charge.event_data)["amount"] == COUNTER_STOP_COST
        assert json.loads(responder_charge.event_data)["ability"] == "counter_stop"
        trigger_data = json.loads(trigger.event_data)
        assert trigger_data["actor_id"] == combat.enemies[0].id
        assert trigger_data["caster_id"] == combat.player.id
        assert trigger_data["target_ability"] == "rewind"


# ============================================================================
# Countered echo
# ============================================================================


class TestCounteredEcho:
    """A countered echo cast fizzles: no Echo built, no ECHO_SPAWNED."""

    def test_countered_echo_returns_counter_stop_result(self) -> None:
        """Full CounterStopResult payload shape on a countered echo cast."""
        combat = _build_combat_with_history(n_actions=1, player_charge=2, enemy_charge=3)
        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        result = combat._temporal.echo_cast(combat, combat.player, turns=1)

        assert isinstance(result, CounterStopResult)
        assert result.countered_ability == "echo_cast"
        assert result.caster_charge_lost == ECHO_CAST_COST
        assert result.responder_charge_spent == COUNTER_STOP_COST

    def test_countered_echo_spawns_nothing(self) -> None:
        """No Echo registered, no ECHO_SPAWNED event, on a countered cast."""
        combat = _build_combat_with_history(n_actions=1, player_charge=2, enemy_charge=3)
        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        combat._temporal.echo_cast(combat, combat.player, turns=1)

        assert combat._active_echoes == {}
        assert not any(e.event_type == EventTypes.ECHO_SPAWNED for e in _all_events(combat))

    def test_countered_echo_still_consumed_the_turn(self) -> None:
        """Via submit_player_action: turn is consumed either way (locked semantic 5)."""
        combat = _build_combat_with_history(n_actions=1, player_charge=2, enemy_charge=3)
        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        total_before = combat._total_turns

        combat.submit_player_action(CombatAction(action_type="echo_cast", target_id="player_1"))

        assert combat._total_turns == total_before + 1
        assert combat._phase == CombatPhase.EXECUTING_TURN


# ============================================================================
# Window mechanics
# ============================================================================


class TestWindowMechanics:
    """Eligibility, policy contract, event ordering, RNG, branch stamping."""

    def test_policy_receives_announcement_and_eligible_list(self) -> None:
        """Announcement fields and deterministic eligible order with 2 enemies."""
        player = create_test_player(temporal_charge=0, max_temporal_charge=5, attack=50)
        enemy_a = create_test_enemy(
            id="enemy_1", hp=5000, max_hp=5000, defense=25, temporal_charge=3, max_temporal_charge=5
        )
        enemy_b = create_test_enemy(
            id="enemy_2", hp=5000, max_hp=5000, defense=25, temporal_charge=3, max_temporal_charge=5
        )
        combat = _build_combat(player=player, enemies=[enemy_a, enemy_b])
        combat.start_round()
        combat.submit_player_action(_attack())
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1

        # Captured before the call: this policy declines (returns None), so
        # the rewind actually proceeds and resets _total_turns / enemy order
        # bookkeeping via replay — comparisons must use pre-call values.
        turn_before = combat._total_turns
        expected_eligible_ids = [e.id for e in combat.living_enemies]

        policy = ScriptedPolicy([None])
        combat._temporal._counter_policy = policy
        combat._temporal.rewind(combat, combat.player, turns=1)

        assert len(policy.calls) == 1
        announcement, eligible = policy.calls[0]
        assert announcement.ability == "rewind"
        assert announcement.caster_id == combat.player.id
        assert announcement.magnitude == 1
        assert announcement.turn_number == turn_before
        assert [c.id for c in eligible] == expected_eligible_ids

    def test_policy_consulted_exactly_once_per_cast(self) -> None:
        """The policy is called exactly once per announced cast (locked semantic 1)."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=3)
        policy = ScriptedPolicy([None])
        combat._temporal._counter_policy = policy
        combat._temporal.rewind(combat, combat.player, turns=1)
        assert len(policy.calls) == 1

    def test_responder_spends_exactly_three_charges(self) -> None:
        """A responder with more than 3 charge only spends exactly 3."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=5)
        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        combat._temporal.rewind(combat, combat.player, turns=1)
        assert combat.enemies[0].temporal_charge == 5 - COUNTER_STOP_COST

    def test_policy_returning_dead_combatant_raises_value_error(self) -> None:
        """A dead combatant is never in `eligible`; returning one raises ValueError."""
        player = create_test_player(temporal_charge=0, max_temporal_charge=5, attack=50)
        eligible_enemy = create_test_enemy(
            id="enemy_1", hp=5000, max_hp=5000, defense=25, temporal_charge=3, max_temporal_charge=5
        )
        dead_enemy = create_test_enemy(
            id="enemy_2", hp=0, max_hp=200, defense=25, temporal_charge=3, max_temporal_charge=5
        )
        combat = _build_combat(player=player, enemies=[eligible_enemy, dead_enemy])
        combat.start_round()
        combat.submit_player_action(_attack())
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1
        combat._temporal._counter_policy = ScriptedPolicy([dead_enemy])

        with pytest.raises(ValueError):
            combat._temporal.rewind(combat, combat.player, turns=1)

    def test_policy_returning_undercharged_combatant_raises_value_error(self) -> None:
        """A combatant under COUNTER_STOP_COST is never in `eligible`."""
        player = create_test_player(temporal_charge=0, max_temporal_charge=5, attack=50)
        eligible_enemy = create_test_enemy(
            id="enemy_1", hp=5000, max_hp=5000, defense=25, temporal_charge=3, max_temporal_charge=5
        )
        weak_enemy = create_test_enemy(
            id="enemy_2", hp=5000, max_hp=5000, defense=25, temporal_charge=1, max_temporal_charge=5
        )
        combat = _build_combat(player=player, enemies=[eligible_enemy, weak_enemy])
        combat.start_round()
        combat.submit_player_action(_attack())
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1
        combat._temporal._counter_policy = ScriptedPolicy([weak_enemy])

        with pytest.raises(ValueError):
            combat._temporal.rewind(combat, combat.player, turns=1)

    def test_policy_returning_wrong_side_combatant_raises_value_error(self) -> None:
        """Returning the caster's own side (the player itself) raises ValueError."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=3)
        combat._temporal._counter_policy = ScriptedPolicy([combat.player])

        with pytest.raises(ValueError):
            combat._temporal.rewind(combat, combat.player, turns=1)

    def test_validation_failure_never_announces(self) -> None:
        """An invalid cast never opens the window: zero policy calls, zero events."""
        combat = _make_rewindable_combat(player_charge=0, enemy_charge=3)
        policy = ScriptedPolicy([])
        combat._temporal._counter_policy = policy
        events_before = len(_all_events(combat))

        with pytest.raises(InsufficientChargeError):
            combat._temporal.rewind(combat, combat.player, turns=1)

        assert len(_all_events(combat)) == events_before
        assert len(policy.calls) == 0

    def test_counter_path_draws_no_rng(self) -> None:
        """The window, default policy, and resolution draw zero RNG."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=3)
        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        rng_before = combat._rng.getstate()
        damage_rng_before = combat._damage_calc.rng.getstate()

        combat._temporal.rewind(combat, combat.player, turns=1)

        assert combat._rng.getstate() == rng_before
        assert combat._damage_calc.rng.getstate() == damage_rng_before

    def test_counter_events_carry_current_branch(self) -> None:
        """Counter events land at the current turn, current branch (locked semantic 10)."""
        combat = _make_rewindable_combat(player_charge=1, enemy_charge=3)
        branch = combat._current_branch_id
        combat._temporal._counter_policy = ScriptedPolicy([combat.enemies[0]])
        events_before = len(_all_events(combat))

        combat._temporal.rewind(combat, combat.player, turns=1)

        new_events = _all_events(combat)[events_before:]
        assert len(new_events) == 3
        assert all(e.branch_id == branch for e in new_events)

    def test_counter_stop_triggered_is_not_rewindable(self) -> None:
        """Guards the events.py classification: COUNTER_STOP_TRIGGERED is persistent."""
        assert is_rewindable(EventTypes.COUNTER_STOP_TRIGGERED) is False

    def test_player_can_counter_enemy_echo_cast(self) -> None:
        """Symmetric: the player can counter a manually-driven enemy echo cast."""
        player = create_test_player(hp=1000, max_hp=1000, temporal_charge=3, max_temporal_charge=5)
        enemy = create_test_enemy(
            hp=200, max_hp=200, defense=10, attack=80, temporal_charge=0, max_temporal_charge=5
        )
        combat = _build_combat(player=player, enemies=[enemy])
        combat.start_round()

        combat.submit_player_action(CombatAction(action_type="defend", target_id="player_1"))
        combat.advance_turn()
        combat.execute_enemy_turn(enemy)
        combat.advance_turn()
        assert len(combat._action_history[enemy.id]) == 1

        enemy.temporal_charge = ECHO_CAST_COST
        combat._temporal._counter_policy = ScriptedPolicy([combat.player])
        result = combat._temporal.echo_cast(combat, enemy, turns=1)

        assert isinstance(result, CounterStopResult)
        assert result.responder_id == combat.player.id
        assert combat._active_echoes == {}
