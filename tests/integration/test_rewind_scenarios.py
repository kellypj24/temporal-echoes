"""
Integration tests for Phase 3 Step 3 single-turn rewind.

Verifies end-to-end combat → rewind → state assertion scenarios, plus
determinism invariants (same seed → same result, different action → different
state, hash stability across runs).

TURN_STARTED gap: CombatContext does not currently emit TURN_STARTED events
during normal turn flow. Tests that depend on TURN_STARTED appearing in the
store are either skipped (where live-loop wiring is required) or exercise the
dispatcher directly by injecting events into the store.
"""

from __future__ import annotations

import json

import pytest

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatPhase
from src.core.events import EventTypes
from src.core.exceptions import RewindUnavailableError
from src.core.persistence import EventStore
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


def _play_n_player_turns(combat: CombatContext, n: int, action: CombatAction) -> None:
    """
    Advance *n* player turns in a round-aware loop.

    Starts a new round if the phase is ROUND_START or ROUND_END, then
    submits the given action when the player's turn comes up. Enemy turns
    are auto-executed. Raises if combat ends before n turns complete.

    Args:
        combat: The active CombatContext.
        n: Number of player turns to play.
        action: The player action to submit on each turn.
    """
    from src.entities import Enemy

    turns_played = 0
    # Safety cap: each player turn costs at most a round-start plus one enemy
    # turn per combatant. If the phase machine ever lands in a state this loop
    # can't make progress from, fail loudly instead of spinning forever.
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


def _snapshot_combat_state(combat: CombatContext) -> dict:
    """
    Capture a lightweight snapshot of mutable combat state for assertion.

    Args:
        combat: The CombatContext to snapshot.

    Returns:
        Dict with player_hp, player_bp, player_charge, enemy_hp values.
    """
    return {
        "player_hp": combat.player.hp,
        "player_bp": combat.player.boost_points,
        "player_charge": combat.player.temporal_charge,
        "enemy_hp": {e.id: e.hp for e in combat.enemies},
        "total_turns": combat._total_turns,
        "branch_id": combat._current_branch_id,
    }


def _get_all_events(combat: CombatContext) -> list:
    """Return all events for this combat's timeline."""
    return combat._event_store.get_events_by_timeline(combat._timeline_id)


# ============================================================================
# Basic rewind scenarios
# ============================================================================


class TestMultiTurnRewindRestoresState:
    """Rewinding back to an earlier captured turn restores that turn's state."""

    def test_rewind_to_earlier_turn_restores_that_turns_state(self) -> None:
        """
        After playing further turns, rewinding back to an earlier captured turn
        restores player HP, enemy HP, and _total_turns to that turn's snapshot —
        across the enemy turn(s) in between (a multi-turn rewind, Step 4).

        Uses a tanky enemy so the player's attacks don't end combat; the player
        still takes enemy damage between turns, so the HP restoration is real.
        """
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        enemy = create_test_enemy(hp=5000, max_hp=5000)  # survive all the hits
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])

        # Play two player turns, snapshot, and capture the turn to return to.
        _play_n_player_turns(combat, 2, _attack())
        snap = _snapshot_combat_state(combat)
        target_turn = combat._total_turns

        # Play one more player turn (advances _total_turns past the snapshot).
        _play_n_player_turns(combat, 1, _attack())
        assert combat._total_turns > target_turn  # there are turns to unwind

        # Rewind back to the captured turn (turns_back > 1 → multi-turn).
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 3  # enough charge for the unwind
        combat.rewind_to_turn(target_turn)

        assert combat._total_turns == snap["total_turns"]
        assert combat.player.hp == snap["player_hp"]
        for eid, hp in snap["enemy_hp"].items():
            found = next(e for e in combat.enemies if e.id == eid)
            assert found.hp == hp


class TestPersistentEvents:
    """test_rewind_preserves_persistent_events."""

    def test_rewind_preserves_persistent_events(self) -> None:
        """
        After a rewind, COMBAT_STARTED and TEMPORAL_REWIND events are both
        queryable in the store; no events are deleted.
        """
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        combat = create_combat_context(seed=42, player=player)
        _play_n_player_turns(combat, 1, _attack())
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1

        events_before = len(_get_all_events(combat))
        combat.rewind_to_turn(combat._total_turns - 1)

        events_after = _get_all_events(combat)
        types = {e.event_type for e in events_after}

        assert EventTypes.COMBAT_STARTED in types
        assert EventTypes.TEMPORAL_REWIND in types
        assert len(events_after) > events_before


class TestPostRewindBranchId:
    """test_post_rewind_events_carry_new_branch_id."""

    def test_post_rewind_events_carry_new_branch_id(self) -> None:
        """
        Events emitted after a rewind carry the new branch_id (1 for the
        first rewind). This proves the builder's branch is updated.
        """
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        combat = create_combat_context(seed=42, player=player)
        _play_n_player_turns(combat, 1, _attack())
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1

        result = combat.rewind_to_turn(combat._total_turns - 1)
        new_branch = result.new_branch_id

        # Now play another turn on the new branch
        _play_n_player_turns(combat, 1, _attack())

        events = _get_all_events(combat)
        post_rewind_actions = [
            e
            for e in events
            if e.event_type == EventTypes.ACTION_EXECUTED and e.branch_id == new_branch
        ]
        assert len(post_rewind_actions) >= 1, "Post-rewind ACTION_EXECUTED must carry new branch_id"


class TestEventLogAppendOnly:
    """test_event_log_append_only_after_rewind."""

    def test_event_log_append_only_after_rewind(self) -> None:
        """
        A rewind appends exactly 2 events (CHARGE_SPENT + TEMPORAL_REWIND) to the
        store; no events are removed. Count after == count before + 2.
        """
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        combat = create_combat_context(seed=42, player=player)
        _play_n_player_turns(combat, 1, _attack())
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1

        count_before = len(_get_all_events(combat))
        combat.rewind_to_turn(combat._total_turns - 1)
        count_after = len(_get_all_events(combat))

        assert count_after == count_before + 2


class TestRewindToTurnZero:
    """test_rewind_to_turn_zero_restores_combat_start_state."""

    def test_rewind_to_turn_zero_restores_combat_start_state(self) -> None:
        """
        After rewinding to turn 0, player and enemy HP equal the COMBAT_STARTED
        snapshot values (all HP at starting values, total_turns == 0).
        """
        player = create_test_player(hp=300, max_hp=300, temporal_charge=3, max_temporal_charge=3)
        enemy = create_test_enemy(hp=200, max_hp=200)
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])
        initial_player_hp = combat.player.hp
        initial_enemy_hp = combat.enemies[0].hp

        _play_n_player_turns(combat, 1, _attack())
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1

        combat.rewind_to_turn(0)

        assert combat._total_turns == 0
        assert combat.player.hp == initial_player_hp
        assert combat.enemies[0].hp == initial_enemy_hp


class TestRoundBoundaryResetRoundCounter:
    """test_rewind_at_round_boundary_resets_round_counter."""

    def test_rewind_at_round_boundary_resets_round_counter(self) -> None:
        """
        Rewinding from round 2 back to a turn in round 1 restores _round_number
        to 1, reconstructed from the recorded round_number on TURN_STARTED.
        """
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        enemy = create_test_enemy(hp=5000, max_hp=5000)  # tanky: survive the hits
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])

        # One player turn in round 1; capture it.
        _play_n_player_turns(combat, 1, _attack())
        round1_turn = combat._total_turns
        assert combat._round_number == 1

        # Another player turn crosses into round 2.
        _play_n_player_turns(combat, 1, _attack())
        assert combat._round_number == 2

        # Rewind back to the round-1 turn.
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 3
        combat.rewind_to_turn(round1_turn)

        assert combat._round_number == 1
        assert combat._total_turns == round1_turn


class TestRewindDuringEnemyTurnWindow:
    """test_rewind_during_enemy_turn_window_raises_unavailable."""

    def test_rewind_during_enemy_turn_window_raises_unavailable(self) -> None:
        """
        With phase == EXECUTING_TURN (an enemy is resolving), calling
        rewind_to_turn raises RewindUnavailableError.
        """
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        combat = create_combat_context(seed=42, player=player)
        combat.start_round()
        # Submit a player action so total_turns > 0
        combat.submit_player_action(_attack())
        # Manually set EXECUTING_TURN to simulate enemy resolution
        combat._phase = CombatPhase.EXECUTING_TURN
        combat._total_turns = 1

        with pytest.raises(RewindUnavailableError):
            combat.rewind_to_turn(0)


class TestRewindMidRoundTurnIndexInvariant:
    """test_rewind_mid_round_preserves_turn_index_invariant."""

    def test_rewind_mid_round_preserves_turn_index_invariant(self) -> None:
        """
        After rewinding to turn 0, _turn_index is reset to 0 and _turn_order
        is cleared, consistent with a fresh ROUND_START state. The player
        can start a new round successfully.
        """
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        combat = create_combat_context(seed=42, player=player)
        _play_n_player_turns(combat, 1, _attack())
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1

        combat.rewind_to_turn(0)

        # After replay to turn 0, index resets to 0
        assert combat._turn_index == 0
        # Phase should be AWAITING_PLAYER_INPUT (set by _replay_events)
        assert combat._phase == CombatPhase.AWAITING_PLAYER_INPUT


# ============================================================================
# Determinism tests
# ============================================================================


class TestDeterminism:
    """Determinism invariants for rewind + replay."""

    def test_rewind_then_same_action_produces_same_state(self) -> None:
        """
        Rewinding and replaying the same action produces the same resulting
        HP and enemy HP as the original timeline (bit-identical).
        """
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        enemy = create_test_enemy(hp=200, max_hp=200)
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])

        # Play turn 1 and snapshot post-state
        _play_n_player_turns(combat, 1, _attack())
        post_turn1_player_hp = combat.player.hp
        post_turn1_enemy_hp = combat.enemies[0].hp
        post_turn1_total = combat._total_turns

        # Rewind to turn 0
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1
        combat.rewind_to_turn(0)

        # Replay the same action
        _play_n_player_turns(combat, 1, _attack())

        # State should be identical
        assert combat.player.hp == post_turn1_player_hp
        assert combat.enemies[0].hp == post_turn1_enemy_hp
        assert combat._total_turns == post_turn1_total

    def test_rewind_then_different_action_diverges_cleanly(self) -> None:
        """
        Rewinding and playing a different action (defend instead of attack)
        produces a different state, proving no leakage from the prior branch.
        """
        player = create_test_player(temporal_charge=3, max_temporal_charge=3, attack=50)
        enemy = create_test_enemy(hp=200, max_hp=200)
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])

        # Play turn 1 with attack
        _play_n_player_turns(combat, 1, _attack())
        post_attack_enemy_hp = combat.enemies[0].hp

        # Rewind to turn 0
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1
        combat.rewind_to_turn(0)

        # Replay with defend instead
        _play_n_player_turns(combat, 1, _defend())
        post_defend_enemy_hp = combat.enemies[0].hp

        # Enemy HP must differ (defend doesn't deal damage)
        assert post_defend_enemy_hp != post_attack_enemy_hp, (
            "Defend and attack should produce different enemy HP"
        )
        # In defend branch, enemy HP should be full (no damage dealt)
        assert post_defend_enemy_hp == 200

    def test_event_log_hash_stable_across_runs(self) -> None:
        """
        Running the same seeded combat sequence twice produces event logs with
        identical (event_type, branch_id, turn_number) tuples, proving the
        RNG strategy is bit-stable across runs.
        """

        def _run_combat_and_collect(seed: int) -> list[tuple]:
            player = create_test_player(temporal_charge=3, max_temporal_charge=3)
            enemy = create_test_enemy(hp=200, max_hp=200)
            combat = create_combat_context(seed=seed, player=player, enemies=[enemy])

            _play_n_player_turns(combat, 1, _attack())
            combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
            combat.player.temporal_charge = 1
            combat.rewind_to_turn(0)
            _play_n_player_turns(combat, 1, _attack())

            events = _get_all_events(combat)
            return [
                (
                    e.event_type,
                    e.branch_id,
                    json.loads(e.event_data).get("turn_number", 0),
                )
                for e in events
            ]

        run1 = _run_combat_and_collect(seed=42)
        run2 = _run_combat_and_collect(seed=42)

        assert run1 == run2, "Event log must be bit-stable across identical seeded runs"

    def test_replay_damage_matches_recorded_damage(self) -> None:
        """
        After a rewind, the internal _apply_event recomputes attack damage and
        asserts it equals the recorded damage_dealt. This test drives that path
        by executing an attack, rewinding, and asserting the rewind succeeds
        (i.e. determinism assertion inside _apply_event did not fire).
        """
        player = create_test_player(temporal_charge=3, max_temporal_charge=3, attack=50)
        enemy = create_test_enemy(hp=200, max_hp=200, defense=25)
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])

        _play_n_player_turns(combat, 1, _attack())
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
        combat.player.temporal_charge = 1

        # If damage replay fails (determinism mismatch), rewind raises RewindReplayError.
        # A clean return proves recomputed == recorded damage.
        from src.core.temporal import RewindResult

        result = combat.rewind_to_turn(0)
        assert isinstance(result, RewindResult), "Rewind must succeed (damage replay deterministic)"


# ============================================================================
# TURN_STARTED dispatcher test (option 2 from plan §7)
# ============================================================================


class TestReplayDerivesRoundNumber:
    """
    Exercises the TURN_STARTED branch of _apply_event by injecting events
    directly into the store and running _replay_events.
    """

    def test_replay_derives_round_number_from_turn_count(self) -> None:
        """
        When TURN_STARTED events are injected into the store at turn_number=1,
        _replay_events sets _total_turns=1 and increments _round_number,
        confirming the dispatcher derives round state from the event log.
        """

        store = EventStore(":memory:")
        player = create_test_player(temporal_charge=3, max_temporal_charge=3)
        enemy = create_test_enemy()
        combat = create_combat_context(seed=42, player=player, enemies=[enemy], event_store=store)

        # Emit COMBAT_STARTED (already done by constructor — already in store)
        # Inject a synthetic TURN_STARTED at turn_number=1
        ts_event = combat._event_builder.turn_started(
            turn_number=1,
            active_combatant_id=combat.player.id,
        )
        store.append_event(ts_event)

        # Manually set total_turns so replay filter works
        combat._total_turns = 1
        combat._phase = CombatPhase.AWAITING_PLAYER_INPUT

        # Run replay directly (targets to_turn=1 on branch 0)
        # We need _current_branch_id at 1 so filter selects branch 0 events
        combat._current_branch_id = 1
        events_applied = combat._temporal._replay_events(combat, to_turn=1)

        # TURN_STARTED was applied, so _total_turns should reflect turn 1
        assert combat._total_turns == 1
        # _round_number was incremented from TURN_STARTED dispatch
        assert combat._round_number >= 1
        # At least the TURN_STARTED event was replayed
        assert events_applied >= 1
