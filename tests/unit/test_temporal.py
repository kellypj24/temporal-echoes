"""
Unit tests for TemporalSystem.rewind() — Phase 3 Step 3.

Covers the single-turn rewind path end-to-end at the unit level:
validation errors, event ordering, branch_id propagation, charge
decrements, result payload shape, and failure rollback.
"""

from __future__ import annotations

import json

import pytest

from src.core.combat import CombatPhase
from src.core.events import EventTypes
from src.core.exceptions import (
    InsufficientChargeError,
    RewindBoundaryError,
    RewindReplayError,
    RewindUnavailableError,
)
from src.core.temporal import RewindResult
from tests.fixtures.combat_fixtures import create_combat_context
from tests.fixtures.entity_fixtures import create_test_player

# ============================================================================
# Helpers
# ============================================================================


def _make_rewindable_combat(
    seed: int = 42,
    temporal_charge: int = 3,
) -> object:
    """
    Create a CombatContext positioned for a rewind (one completed player turn).

    The player attacks on turn 1, leaving combat in EXECUTING_TURN state
    after the action. We then manually advance to AWAITING_PLAYER_INPUT so
    the rewind pre-condition is satisfied.

    Args:
        seed: RNG seed for the combat.
        temporal_charge: Player's starting temporal charge (default 3).

    Returns:
        CombatContext with _total_turns == 1 and phase == AWAITING_PLAYER_INPUT.
    """
    from src.core.ai import CombatAction

    player = create_test_player(temporal_charge=temporal_charge, max_temporal_charge=3)
    combat = create_combat_context(seed=seed, player=player)
    combat.start_round()
    # Player attacks (turn 1)
    combat.submit_player_action(CombatAction(action_type="attack", target_id="enemy_1"))
    # Manually gate the phase so we can rewind from AWAITING_PLAYER_INPUT;
    # advance_turn() may set EXECUTING_TURN for enemy or ROUND_END.
    # We force AWAITING_PLAYER_INPUT to match the allowed phase set.
    combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
    return combat


# ============================================================================
# Test classes
# ============================================================================


class TestRewindValidation:
    """Validation error paths — no events emitted, no state mutated."""

    def test_rewind_with_zero_charge_raises_insufficient_charge(self) -> None:
        """
        InsufficientChargeError is raised when actor has 0 charge and no
        events are emitted to the event store.
        """
        from src.core.persistence import EventStore

        store = EventStore(":memory:")
        combat = create_combat_context(event_store=store)
        combat.start_round()
        # After start_round, player has 1 charge — drain it
        combat.player.temporal_charge = 0
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat._total_turns = 1  # need at least 1 turn so target_turn >= 0

        events_before = len(store.get_events_by_timeline("timeline_main"))

        with pytest.raises(InsufficientChargeError):
            combat._temporal.rewind(combat, combat.player, turns=1)

        events_after = len(store.get_events_by_timeline("timeline_main"))
        assert events_after == events_before, "No events should be emitted on validation failure"

    def test_rewind_zero_turns_raises_value_error(self) -> None:
        """ValueError is raised when turns=0 (must be >= 1)."""
        combat = _make_rewindable_combat()
        with pytest.raises(ValueError, match="at least 1"):
            combat._temporal.rewind(combat, combat.player, turns=0)

    def test_rewind_multi_turn_succeeds(self) -> None:
        """rewind(turns=2) rewinds two turns on a new branch, costing 2 charges."""
        from src.core.ai import CombatAction
        from src.core.combat import CombatPhase
        from tests.fixtures.entity_fixtures import create_test_enemy

        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        enemy = create_test_enemy(hp=5000, max_hp=5000)  # tanky: survive the hits
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])

        # Drive two full combat turns (player + enemy) so _total_turns == 2.
        combat.start_round()
        combat.submit_player_action(CombatAction(action_type="attack", target_id="enemy_1"))
        combat.advance_turn()
        combat.execute_enemy_turn(combat.current_combatant)
        combat.advance_turn()
        assert combat._total_turns == 2

        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        result = combat._temporal.rewind(combat, combat.player, turns=2)

        assert result.charge_spent == 2
        assert result.from_turn == 2
        assert result.to_turn == 0
        assert result.new_branch_id == 1
        # Combat is resumable (turn order rebuilt, player ready for input).
        assert combat.phase == CombatPhase.AWAITING_PLAYER_INPUT

    def test_rewind_before_turn_zero_raises_boundary_error(self) -> None:
        """
        RewindBoundaryError is raised when the target turn would be < 0
        (i.e. total_turns - turns < 0).
        """
        combat = create_combat_context()
        combat.start_round()
        combat._total_turns = 0
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 3

        with pytest.raises(RewindBoundaryError):
            combat._temporal.rewind(combat, combat.player, turns=1)

    def test_rewind_to_turn_zero_succeeds(self) -> None:
        """
        Rewinding to turn 0 is valid — only target < 0 is the boundary.
        A successful RewindResult is returned.
        """
        combat = _make_rewindable_combat()
        # total_turns == 1, so rewind(1) -> target_turn == 0 (valid)
        result = combat._temporal.rewind(combat, combat.player, turns=1)
        assert isinstance(result, RewindResult)
        assert result.to_turn == 0

    def test_rewind_when_combat_over_raises_unavailable(self) -> None:
        """RewindUnavailableError is raised when combat.is_over is True."""
        combat = _make_rewindable_combat()
        combat._phase = CombatPhase.COMBAT_OVER

        with pytest.raises(RewindUnavailableError, match="combat is over"):
            combat._temporal.rewind(combat, combat.player, turns=1)

    def test_rewind_during_executing_phase_raises_unavailable(self) -> None:
        """RewindUnavailableError is raised when phase == EXECUTING_TURN."""
        combat = _make_rewindable_combat()
        combat._phase = CombatPhase.EXECUTING_TURN

        with pytest.raises(RewindUnavailableError, match="EXECUTING_TURN"):
            combat._temporal.rewind(combat, combat.player, turns=1)


class TestRewindEventOrdering:
    """Event order and payload assertions for successful rewinds."""

    def test_rewind_emits_charge_spent_then_temporal_rewind(self) -> None:
        """
        After a successful rewind, CHARGE_SPENT appears before TEMPORAL_REWIND
        in the event store (exact ordering per §3 of the plan).
        """
        from src.core.persistence import EventStore

        store = EventStore(":memory:")
        combat = _make_rewindable_combat()
        # Wire shared store
        combat._event_store = store
        combat._temporal._event_store = store
        # Emit a combat_started to give replay something to anchor on
        store.append_event(
            combat._event_builder.combat_started(
                rng_seed=42,
                player={"id": "player_1", "hp": 300},
                enemies=[{"id": "enemy_1", "hp": 200}],
            )
        )

        combat._temporal.rewind(combat, combat.player, turns=1)

        events = store.get_events_by_timeline("timeline_main")
        temporal_events = [
            e
            for e in events
            if e.event_type in (EventTypes.CHARGE_SPENT, EventTypes.TEMPORAL_REWIND)
        ]
        # There should be at least CHARGE_SPENT + TEMPORAL_REWIND
        types = [e.event_type for e in temporal_events]
        charge_idx = next(i for i, t in enumerate(types) if t == EventTypes.CHARGE_SPENT)
        rewind_idx = next(i for i, t in enumerate(types) if t == EventTypes.TEMPORAL_REWIND)
        assert charge_idx < rewind_idx, "CHARGE_SPENT must precede TEMPORAL_REWIND"

    def test_temporal_rewind_event_carries_new_branch_id(self) -> None:
        """TEMPORAL_REWIND event.branch_id equals the newly allocated branch_id."""
        combat = _make_rewindable_combat()
        old_branch = combat._current_branch_id
        result = combat._temporal.rewind(combat, combat.player, turns=1)

        store = combat._event_store
        events = store.get_events_by_timeline("timeline_main")
        rewind_evt = next(e for e in reversed(events) if e.event_type == EventTypes.TEMPORAL_REWIND)
        assert rewind_evt.branch_id == old_branch + 1
        assert rewind_evt.branch_id == result.new_branch_id

    def test_charge_spent_event_carries_old_branch_id(self) -> None:
        """CHARGE_SPENT event is stamped with the pre-rewind branch_id (branch 0)."""
        combat = _make_rewindable_combat()
        old_branch = combat._current_branch_id

        combat._temporal.rewind(combat, combat.player, turns=1)

        store = combat._event_store
        events = store.get_events_by_timeline("timeline_main")
        # Find the last CHARGE_SPENT (rewind's own, not regen-related)
        charge_events = [e for e in events if e.event_type == EventTypes.CHARGE_SPENT]
        rewind_charge_evt = charge_events[-1]
        assert rewind_charge_evt.branch_id == old_branch

    def test_branch_id_increments_by_one_per_rewind(self) -> None:
        """Each successive rewind increments _current_branch_id by exactly 1."""
        from src.core.ai import CombatAction

        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        combat = create_combat_context(seed=42, player=player)
        combat.start_round()

        assert combat._current_branch_id == 0

        # First rewind (turn 1)
        combat.submit_player_action(CombatAction(action_type="attack", target_id="enemy_1"))
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 3
        combat._temporal.rewind(combat, combat.player, turns=1)
        assert combat._current_branch_id == 1

        # Second rewind (turn 1 again on new branch)
        combat.player.temporal_charge = 3
        combat.submit_player_action(CombatAction(action_type="attack", target_id="enemy_1"))
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 3
        combat._temporal.rewind(combat, combat.player, turns=1)
        assert combat._current_branch_id == 2


class TestRewindStateEffects:
    """In-memory state mutations after a successful rewind."""

    def test_rewind_decrements_actor_charge_by_one(self) -> None:
        """
        After a successful rewind, actor.temporal_charge has been decremented
        by 1 (the spend) and then reset to combat-start state (0) by replay.
        The spend is verified by the CHARGE_SPENT event in the store; the
        in-memory charge ends at the replay-derived value (0 from COMBAT_STARTED
        snapshot, since no CHARGE_REGENERATED events fall in the to_turn=0 window).
        """
        from src.core.events import EventTypes

        combat = _make_rewindable_combat(temporal_charge=3)

        combat._temporal.rewind(combat, combat.player, turns=1)

        # Verify the spend is recorded as an event (charge WAS decremented by 1)
        store = combat._event_store
        events = store.get_events_by_timeline("timeline_main")
        import json as _json

        charge_events = [
            e
            for e in events
            if e.event_type == EventTypes.CHARGE_SPENT
            and _json.loads(e.event_data).get("ability") == "rewind"
        ]
        assert len(charge_events) >= 1, "CHARGE_SPENT must be emitted for the rewind"
        spent_amount = _json.loads(charge_events[-1].event_data)["amount"]
        assert spent_amount == 1

        # Replay resets charge to combat-start state (0), then derives forward.
        # At to_turn=0 there are no CHARGE_REGENERATED events in the replay
        # window, so in-memory charge ends at 0.
        assert combat.player.temporal_charge == 0

    def test_rewind_result_payload_shape(self) -> None:
        """
        RewindResult contains all 5 required fields with correct types and
        semantically correct values.
        """
        combat = _make_rewindable_combat()
        from_turn_expected = combat._total_turns

        result = combat._temporal.rewind(combat, combat.player, turns=1)

        assert isinstance(result, RewindResult)
        assert result.from_turn == from_turn_expected
        assert result.to_turn == from_turn_expected - 1
        assert result.new_branch_id >= 1
        assert isinstance(result.events_replayed, int)
        assert result.events_replayed >= 0
        assert result.charge_spent == 1


class TestRewindRollback:
    """Failure rollback contract (§8a of the plan)."""

    def test_rewind_replay_failure_restores_actor_charge(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        When _apply_event raises during replay, the actor's temporal_charge is
        restored to its pre-rewind value and the branch_id is reverted.
        """
        combat = _make_rewindable_combat(temporal_charge=3)
        charge_before = combat.player.temporal_charge
        branch_before = combat._current_branch_id
        phase_before = combat._phase

        def _fail_apply(c: object, e: object) -> None:
            raise RuntimeError("injected replay failure")

        monkeypatch.setattr(combat._temporal, "_apply_event", _fail_apply)

        with pytest.raises(RewindReplayError):
            combat._temporal.rewind(combat, combat.player, turns=1)

        assert combat.player.temporal_charge == charge_before
        assert combat._current_branch_id == branch_before
        assert combat._phase == phase_before

    def test_rewind_replay_failure_leaves_charge_spent_in_store(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        CHARGE_SPENT event remains in the store even after a failed replay
        (immutable historical record — Constitution principle 11).
        """
        combat = _make_rewindable_combat(temporal_charge=3)

        def _fail_apply(c: object, e: object) -> None:
            raise RuntimeError("injected replay failure")

        monkeypatch.setattr(combat._temporal, "_apply_event", _fail_apply)

        with pytest.raises(RewindReplayError):
            combat._temporal.rewind(combat, combat.player, turns=1)

        store = combat._event_store
        events = store.get_events_by_timeline("timeline_main")
        charge_events = [e for e in events if e.event_type == EventTypes.CHARGE_SPENT]
        # Rewind emits exactly 1 CHARGE_SPENT before replay; it must survive
        rewind_charges = [
            e for e in charge_events if json.loads(e.event_data).get("ability") == "rewind"
        ]
        assert len(rewind_charges) >= 1, "CHARGE_SPENT for rewind must survive failed replay"

    def test_rewind_replay_failure_restores_rng_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        After a failed replay, the combat RNG state is restored to its
        pre-rewind value (Random.getstate() equality).
        """
        combat = _make_rewindable_combat(temporal_charge=3)
        rng_state_before = combat._rng.getstate()

        def _fail_apply(c: object, e: object) -> None:
            raise RuntimeError("injected replay failure")

        monkeypatch.setattr(combat._temporal, "_apply_event", _fail_apply)

        with pytest.raises(RewindReplayError):
            combat._temporal.rewind(combat, combat.player, turns=1)

        rng_state_after = combat._rng.getstate()
        assert rng_state_after == rng_state_before, "RNG state must be restored after failed replay"


class TestRewindRollbackEchoState:
    """Rollback contract (§8a) extended for echo + action-history state (Step 5)."""

    def test_rewind_replay_failure_restores_active_echoes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        When _apply_event raises during replay, _active_echoes is restored
        to its pre-rewind snapshot (same echo_id, owner_id, next_index,
        source_actions).
        """
        from src.core.temporal import Echo, EchoSourceAction

        combat = _make_rewindable_combat(temporal_charge=3)
        combat._active_echoes["player"] = Echo(
            echo_id="echo_player_1_t1",
            owner_id=combat.player.id,
            source_actions=(
                EchoSourceAction(
                    source_turn=1, action_type="attack", target_id="enemy_1", damage_dealt=100
                ),
            ),
            next_index=0,
        )
        echo_before = combat._active_echoes["player"]

        def _fail_apply(c: object, e: object) -> None:
            raise RuntimeError("injected replay failure")

        monkeypatch.setattr(combat._temporal, "_apply_event", _fail_apply)

        with pytest.raises(RewindReplayError):
            combat._temporal.rewind(combat, combat.player, turns=1)

        echo_after = combat._active_echoes["player"]
        assert echo_after.echo_id == echo_before.echo_id
        assert echo_after.owner_id == echo_before.owner_id
        assert echo_after.next_index == echo_before.next_index
        assert echo_after.source_actions == echo_before.source_actions

    def test_rewind_replay_failure_restores_action_history(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        When _apply_event raises during replay, _action_history is restored
        to its pre-rewind snapshot (same recorded entries, same order).
        """
        combat = _make_rewindable_combat(temporal_charge=3)
        history_before = {
            combatant_id: list(history) for combatant_id, history in combat._action_history.items()
        }
        assert history_before, "setup attack should have recorded a history entry"

        def _fail_apply(c: object, e: object) -> None:
            raise RuntimeError("injected replay failure")

        monkeypatch.setattr(combat._temporal, "_apply_event", _fail_apply)

        with pytest.raises(RewindReplayError):
            combat._temporal.rewind(combat, combat.player, turns=1)

        history_after = {
            combatant_id: list(history) for combatant_id, history in combat._action_history.items()
        }
        assert history_after == history_before
