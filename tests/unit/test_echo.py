"""
Unit tests for TemporalSystem.echo_cast() / execute_echo_turn() — Phase 3 Step 5.

Covers the Echo Cast path at the unit level: validation errors, event
ordering, deterministic echo_id, source-window embedding, and echo acting
mechanics (attack scaling, retargeting, fizzle, defend no-op, expiry).

Most tests call ``combat._temporal.echo_cast`` / ``execute_echo_turn``
directly (same pattern as test_temporal.py's rewind unit tests) rather than
going through the full turn dispatcher, so they can control history and
charge precisely without playing out full combats.
"""

from __future__ import annotations

import json

import pytest

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatPhase
from src.core.events import EventTypes
from src.core.exceptions import (
    EchoAlreadyActiveError,
    EchoHistoryError,
    EchoUnavailableError,
    InsufficientChargeError,
)
from src.core.temporal import ECHO_CAST_COST, Echo, EchoCastResult, EchoSourceAction
from src.entities import Combatant, DamageType
from tests.fixtures.combat_fixtures import create_combat_context
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player

# ============================================================================
# Helpers
# ============================================================================


def _attack(target_id: str = "enemy_1") -> CombatAction:
    """Return an attack CombatAction targeting the given ID."""
    return CombatAction(action_type="attack", target_id=target_id)


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
    temporal_charge: int = 2,
    seed: int = 42,
    enemy_hp: int = 5000,
    action: CombatAction | None = None,
) -> CombatContext:
    """
    Build a CombatContext with ``n_actions`` recorded player actions,
    positioned at AWAITING_PLAYER_INPUT with ``temporal_charge`` charge —
    ready for a direct ``echo_cast`` call.

    Uses a tanky enemy so the player's attacks never end combat early.

    Args:
        n_actions: Number of player turns to play beforehand.
        temporal_charge: Player's charge after setup (assigned directly;
            echo_cast reads this live value, so this bypasses the natural
            regen economy — fine here since no rewind follows in these tests).
        seed: RNG seed for the combat.
        enemy_hp: Enemy HP/max_hp (tanky by default).
        action: Action to play each of the ``n_actions`` turns (default: attack).

    Returns:
        CombatContext ready for ``combat._temporal.echo_cast(...)``.
    """
    if action is None:
        action = _attack()
    player = create_test_player(temporal_charge=0, max_temporal_charge=5, attack=50)
    enemy = create_test_enemy(hp=enemy_hp, max_hp=enemy_hp, defense=25)
    combat = create_combat_context(seed=seed, player=player, enemies=[enemy])
    _play_n_player_turns(combat, n_actions, action)
    combat._phase = CombatPhase.AWAITING_PLAYER_INPUT
    combat.player.temporal_charge = temporal_charge
    return combat


def _fresh_combat(seed: int = 42, enemy_hp: int = 200, **enemy_kwargs: object) -> CombatContext:
    """Build a freshly-started 1v1 combat with no history, for acting tests."""
    player = create_test_player(temporal_charge=3, max_temporal_charge=3, attack=50)
    enemy = create_test_enemy(hp=enemy_hp, max_hp=enemy_hp, defense=10, **enemy_kwargs)
    combat = create_combat_context(seed=seed, player=player, enemies=[enemy])
    combat.start_round()
    return combat


def _register_echo(
    combat: CombatContext,
    owner: Combatant,
    source_actions: list[EchoSourceAction],
    next_index: int = 0,
) -> Echo:
    """
    Directly register an Echo on ``owner``'s side, bypassing echo_cast().

    Gives acting tests full control over the source window without
    needing a real cast + charge economy behind it.

    Args:
        combat: The active CombatContext.
        owner: The echo's owner.
        source_actions: The echo's embedded source window.
        next_index: Starting index into source_actions.

    Returns:
        The registered Echo.
    """
    side = combat._side_of(owner)
    echo = Echo(
        echo_id=f"echo_{owner.id}_test",
        owner_id=owner.id,
        source_actions=tuple(source_actions),
        next_index=next_index,
    )
    combat._active_echoes[side] = echo
    return echo


# ============================================================================
# Validation
# ============================================================================


class TestEchoCastValidation:
    """Validation error paths — no events emitted, no state mutated on failure."""

    def test_echo_cast_turns_zero_raises_value_error(self) -> None:
        """turns=0 raises ValueError (must be 1-3)."""
        combat = _build_combat_with_history(n_actions=1, temporal_charge=2)
        with pytest.raises(ValueError, match="between 1 and"):
            combat._temporal.echo_cast(combat, combat.player, turns=0)

    def test_echo_cast_turns_above_cap_raises_value_error(self) -> None:
        """turns=4 exceeds MAX_ECHO_TURNS and raises ValueError."""
        combat = _build_combat_with_history(n_actions=3, temporal_charge=2)
        with pytest.raises(ValueError, match="between 1 and"):
            combat._temporal.echo_cast(combat, combat.player, turns=4)

    def test_echo_cast_insufficient_charge_raises_and_emits_nothing(self) -> None:
        """1 charge held (cost is 2) raises InsufficientChargeError; no events."""
        combat = _build_combat_with_history(n_actions=1, temporal_charge=1)
        store = combat._event_store
        events_before = len(store.get_events_by_timeline(combat._timeline_id))

        with pytest.raises(InsufficientChargeError):
            combat._temporal.echo_cast(combat, combat.player, turns=1)

        events_after = len(store.get_events_by_timeline(combat._timeline_id))
        assert events_after == events_before

    def test_echo_cast_insufficient_history_raises_echo_history_error(self) -> None:
        """Casting turns=2 after only 1 recorded action raises EchoHistoryError."""
        combat = _build_combat_with_history(n_actions=1, temporal_charge=2)
        with pytest.raises(EchoHistoryError):
            combat._temporal.echo_cast(combat, combat.player, turns=2)

    def test_echo_cast_second_on_same_side_raises_already_active(self) -> None:
        """A second cast on a side with a live echo raises EchoAlreadyActiveError."""
        combat = _build_combat_with_history(n_actions=1, temporal_charge=4)
        combat._temporal.echo_cast(combat, combat.player, turns=1)
        combat.player.temporal_charge = 2

        with pytest.raises(EchoAlreadyActiveError):
            combat._temporal.echo_cast(combat, combat.player, turns=1)

    def test_echo_cast_when_combat_over_raises_unavailable(self) -> None:
        """combat.is_over raises EchoUnavailableError."""
        combat = _build_combat_with_history(n_actions=1, temporal_charge=2)
        combat._phase = CombatPhase.COMBAT_OVER

        with pytest.raises(EchoUnavailableError, match="combat is over"):
            combat._temporal.echo_cast(combat, combat.player, turns=1)

    def test_echo_cast_allowed_when_prior_echo_expired(self) -> None:
        """A side cap is freed once the existing echo has expired."""
        combat = _build_combat_with_history(n_actions=1, temporal_charge=4)
        combat._temporal.echo_cast(combat, combat.player, turns=1)
        combat._active_echoes["player"].next_index = 1  # force expiry
        combat.player.temporal_charge = 2

        result = combat._temporal.echo_cast(combat, combat.player, turns=1)
        assert isinstance(result, EchoCastResult)

    def test_echo_cast_allowed_when_prior_echo_owner_dead(self) -> None:
        """A side cap is freed once the existing echo's owner is dead (inert)."""
        combat = _build_combat_with_history(n_actions=1, temporal_charge=4)
        combat._temporal.echo_cast(combat, combat.player, turns=1)
        combat.player.hp = 0
        combat.player.temporal_charge = 2

        result = combat._temporal.echo_cast(combat, combat.player, turns=1)
        assert isinstance(result, EchoCastResult)


# ============================================================================
# Cast mechanics
# ============================================================================


class TestEchoCastMechanics:
    """Event ordering, payload shape, and result shape for successful casts."""

    def test_cast_emits_charge_spent_then_echo_spawned_in_order(self) -> None:
        """CHARGE_SPENT appears before ECHO_SPAWNED in the store."""
        combat = _build_combat_with_history(n_actions=1, temporal_charge=2)
        combat._temporal.echo_cast(combat, combat.player, turns=1)

        events = combat._event_store.get_events_by_timeline(combat._timeline_id)
        types = [e.event_type for e in events]
        charge_idx = max(i for i, t in enumerate(types) if t == EventTypes.CHARGE_SPENT)
        spawn_idx = types.index(EventTypes.ECHO_SPAWNED)
        assert charge_idx < spawn_idx

    def test_cast_spends_exactly_two_charges_regardless_of_turns(self) -> None:
        """Cost is flat ECHO_CAST_COST regardless of the requested turns."""
        combat = _build_combat_with_history(n_actions=3, temporal_charge=3)
        result = combat._temporal.echo_cast(combat, combat.player, turns=3)

        assert result.charge_spent == ECHO_CAST_COST == 2
        assert combat.player.temporal_charge == 1

    def test_echo_id_is_deterministic(self) -> None:
        """Two identical seeded runs produce the same echo_id (no UUIDs)."""

        def _cast_and_get_id() -> str:
            combat = _build_combat_with_history(n_actions=1, temporal_charge=2, seed=7)
            result = combat._temporal.echo_cast(combat, combat.player, turns=1)
            return result.echo_id

        id1 = _cast_and_get_id()
        id2 = _cast_and_get_id()
        assert id1 == id2
        assert id1 == "echo_player_1_t1"

    def test_echo_spawned_payload_embeds_source_actions(self) -> None:
        """ECHO_SPAWNED payload embeds the source window in chronological order."""
        combat = _build_combat_with_history(n_actions=2, temporal_charge=2)
        combat._temporal.echo_cast(combat, combat.player, turns=2)

        events = combat._event_store.get_events_by_timeline(combat._timeline_id)
        spawn_evt = next(e for e in events if e.event_type == EventTypes.ECHO_SPAWNED)
        payload = json.loads(spawn_evt.event_data)
        source_actions = payload["source_actions"]

        assert len(source_actions) == 2
        assert [sa["source_turn"] for sa in source_actions] == sorted(
            sa["source_turn"] for sa in source_actions
        )
        assert all(sa["action_type"] == "attack" for sa in source_actions)

    def test_cast_emits_no_action_executed(self) -> None:
        """The cast turn's record has no ACTION_EXECUTED event."""
        combat = _build_combat_with_history(n_actions=1, temporal_charge=2)
        store = combat._event_store

        def _count_action_executed() -> int:
            return len(
                [
                    e
                    for e in store.get_events_by_timeline(combat._timeline_id)
                    if e.event_type == EventTypes.ACTION_EXECUTED
                ]
            )

        before = _count_action_executed()
        combat._temporal.echo_cast(combat, combat.player, turns=1)
        assert _count_action_executed() == before

    def test_echo_cast_result_shape(self) -> None:
        """EchoCastResult carries all fields with correct values."""
        combat = _build_combat_with_history(n_actions=2, temporal_charge=2)
        result = combat._temporal.echo_cast(combat, combat.player, turns=2)

        assert isinstance(result, EchoCastResult)
        assert result.owner_id == combat.player.id
        assert result.duration == 2
        assert result.charge_spent == ECHO_CAST_COST
        assert len(result.source_turns) == 2
        assert result.echo_id == combat._active_echoes["player"].echo_id


# ============================================================================
# Acting
# ============================================================================


class TestEchoActing:
    """Echo act dispatch: attack scaling, retargeting, fizzle, defend, expiry."""

    def test_echo_does_not_act_on_cast_turn(self) -> None:
        """No ECHO_ACTED is emitted on the same turn the echo is cast."""
        combat = _build_combat_with_history(n_actions=1, temporal_charge=2)
        combat.submit_player_action(CombatAction(action_type="echo_cast", target_id="player_1"))

        events = combat._event_store.get_events_by_timeline(combat._timeline_id)
        acted_events = [e for e in events if e.event_type == EventTypes.ECHO_ACTED]
        assert acted_events == []
        assert combat._active_echoes["player"].next_index == 0

    def test_echo_attack_deals_floor_half_recorded_damage(self) -> None:
        """Echo attack damage is floor(recorded damage * 0.5)."""
        combat = _fresh_combat(enemy_hp=5000)
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=3, action_type="attack", target_id="enemy_1", damage_dealt=203
                )
            ],
        )
        hp_before = combat.enemies[0].hp
        combat._temporal.execute_echo_turn(combat, combat.player)

        assert hp_before - combat.enemies[0].hp == 101  # floor(203 * 0.5) = 101

    def test_echo_attack_minimum_one_damage(self) -> None:
        """Echo attack damage floors to 0 but the minimum floor is 1."""
        combat = _fresh_combat(enemy_hp=5000)
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=3, action_type="attack", target_id="enemy_1", damage_dealt=1
                )
            ],
        )
        hp_before = combat.enemies[0].hp
        combat._temporal.execute_echo_turn(combat, combat.player)

        assert hp_before - combat.enemies[0].hp == 1

    def test_echo_attack_consumes_no_rng(self) -> None:
        """Echo attack draws zero RNG — combat/damage-calc RNG state is unchanged."""
        combat = _fresh_combat(enemy_hp=5000)
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=3, action_type="attack", target_id="enemy_1", damage_dealt=203
                )
            ],
        )
        rng_before = combat._rng.getstate()
        damage_rng_before = combat._damage_calc.rng.getstate()

        combat._temporal.execute_echo_turn(combat, combat.player)

        assert combat._rng.getstate() == rng_before
        assert combat._damage_calc.rng.getstate() == damage_rng_before

    def test_echo_retargets_first_living_enemy_when_target_dead(self) -> None:
        """A dead original target retargets to living_enemies[0]."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3, attack=50)
        dead_enemy = create_test_enemy(id="enemy_1", hp=0, max_hp=200, defense=10)
        alive_enemy = create_test_enemy(id="enemy_2", hp=200, max_hp=200, defense=10)
        combat = create_combat_context(seed=42, player=player, enemies=[dead_enemy, alive_enemy])
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=3, action_type="attack", target_id="enemy_1", damage_dealt=100
                )
            ],
        )
        hp_before = alive_enemy.hp
        combat._temporal.execute_echo_turn(combat, combat.player)

        assert alive_enemy.hp < hp_before

    def test_echo_fizzles_when_no_living_target(self) -> None:
        """No living enemy means the attack fizzles instead of retargeting."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3, attack=50)
        dead_enemy = create_test_enemy(id="enemy_1", hp=0, max_hp=200, defense=10)
        combat = create_combat_context(seed=42, player=player, enemies=[dead_enemy])
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=3, action_type="attack", target_id="enemy_1", damage_dealt=100
                )
            ],
        )
        msgs = combat._temporal.execute_echo_turn(combat, combat.player)

        assert any("fizzle" in m.lower() for m in msgs)
        events = combat._event_store.get_events_by_timeline(combat._timeline_id)
        acted = next(e for e in events if e.event_type == EventTypes.ECHO_ACTED)
        assert json.loads(acted.event_data)["action_type"] == "fizzle"

    def test_defend_source_replays_as_defend_noop(self) -> None:
        """A recorded defend source action replays as a no-op ECHO_ACTED."""
        combat = _fresh_combat(enemy_hp=5000)
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=3, action_type="defend", target_id=None, damage_dealt=None
                )
            ],
        )
        hp_before = combat.enemies[0].hp
        combat._temporal.execute_echo_turn(combat, combat.player)

        assert combat.enemies[0].hp == hp_before
        events = combat._event_store.get_events_by_timeline(combat._timeline_id)
        acted = next(e for e in events if e.event_type == EventTypes.ECHO_ACTED)
        assert json.loads(acted.event_data)["action_type"] == "defend"

    def test_flee_source_replays_as_fizzle(self) -> None:
        """A recorded flee source action replays as a fizzle — echoes can't leave."""
        combat = _fresh_combat(enemy_hp=5000)
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=3, action_type="flee", target_id=None, damage_dealt=None
                )
            ],
        )
        combat._temporal.execute_echo_turn(combat, combat.player)

        events = combat._event_store.get_events_by_timeline(combat._timeline_id)
        acted = next(e for e in events if e.event_type == EventTypes.ECHO_ACTED)
        assert json.loads(acted.event_data)["action_type"] == "fizzle"

    def test_echo_expires_after_n_acts_and_is_removed(self) -> None:
        """After replaying all source actions, the echo is removed from its side."""
        combat = _fresh_combat(enemy_hp=5000)
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=1, action_type="attack", target_id="enemy_1", damage_dealt=100
                ),
                EchoSourceAction(
                    source_turn=3, action_type="attack", target_id="enemy_1", damage_dealt=100
                ),
            ],
        )
        combat._temporal.execute_echo_turn(combat, combat.player)
        assert "player" in combat._active_echoes

        combat._temporal.execute_echo_turn(combat, combat.player)
        assert "player" not in combat._active_echoes

    def test_echo_acted_payload_shape(self) -> None:
        """ECHO_ACTED payload carries resolved target, scaled damage, source_turn."""
        combat = _fresh_combat(enemy_hp=5000)
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=3, action_type="attack", target_id="enemy_1", damage_dealt=200
                )
            ],
        )
        combat._temporal.execute_echo_turn(combat, combat.player)

        events = combat._event_store.get_events_by_timeline(combat._timeline_id)
        acted = next(e for e in events if e.event_type == EventTypes.ECHO_ACTED)
        payload = json.loads(acted.event_data)

        assert payload["target_id"] == "enemy_1"
        assert payload["damage_dealt"] == 100
        assert payload["source_turn"] == 3
        assert payload["action_type"] == "attack"

    def test_echo_shield_break_emits_shield_broken(self) -> None:
        """An echo attack that breaks the shield emits SHIELD_BROKEN."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3, attack=50)
        enemy = create_test_enemy(
            hp=5000,
            max_hp=5000,
            defense=10,
            shield_points=1,
            max_shield_points=1,
            weaknesses=[DamageType.PHYSICAL],
        )
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=3, action_type="attack", target_id="enemy_1", damage_dealt=200
                )
            ],
        )
        combat._temporal.execute_echo_turn(combat, combat.player)

        assert enemy.is_broken
        events = combat._event_store.get_events_by_timeline(combat._timeline_id)
        assert any(e.event_type == EventTypes.SHIELD_BROKEN for e in events)

    def test_echo_kill_emits_combatant_defeated(self) -> None:
        """An echo attack that reduces the target to 0 HP emits COMBATANT_DEFEATED."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3, attack=50)
        enemy = create_test_enemy(hp=50, max_hp=200, defense=10)
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=3, action_type="attack", target_id="enemy_1", damage_dealt=200
                )
            ],
        )
        combat._temporal.execute_echo_turn(combat, combat.player)

        assert not enemy.is_alive
        events = combat._event_store.get_events_by_timeline(combat._timeline_id)
        assert any(e.event_type == EventTypes.COMBATANT_DEFEATED for e in events)

    def test_player_and_enemy_echoes_coexist(self) -> None:
        """A player-owned and an enemy-owned echo can both be live simultaneously."""
        player = create_test_player(temporal_charge=3, max_temporal_charge=3, attack=50)
        enemy = create_test_enemy(hp=5000, max_hp=5000, defense=10)
        combat = create_combat_context(seed=42, player=player, enemies=[enemy])
        combat._total_turns = 5
        _register_echo(
            combat,
            combat.player,
            [
                EchoSourceAction(
                    source_turn=1, action_type="attack", target_id="enemy_1", damage_dealt=100
                )
            ],
        )
        _register_echo(
            combat,
            enemy,
            [
                EchoSourceAction(
                    source_turn=2, action_type="attack", target_id="player_1", damage_dealt=80
                )
            ],
        )
        assert "player" in combat._active_echoes
        assert "enemy" in combat._active_echoes

        player_hp_before = combat.player.hp
        enemy_hp_before = combat.enemies[0].hp
        combat._temporal.execute_echo_turn(combat, combat.player)
        combat._temporal.execute_echo_turn(combat, enemy)

        assert combat.enemies[0].hp < enemy_hp_before
        assert combat.player.hp < player_hp_before
