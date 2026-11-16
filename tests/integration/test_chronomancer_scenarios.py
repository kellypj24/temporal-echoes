"""End-to-end fights against a Chronomancer, driven through the public combat API."""

import json
from collections.abc import Callable

from src.core.ai import CombatAction
from src.core.combat import CombatContext, CombatOutcome, CombatPhase
from src.core.events import EventTypes, GameEvent
from src.core.persistence import EventStore
from src.core.temporal import CounterStopResult, RewindResult
from src.entities import Enemy, Player
from tests.fixtures.entity_fixtures import create_test_enemy, create_test_player

Decide = Callable[[CombatContext], CombatAction | None]


def _mage(hp: int = 1000, **overrides: object) -> Enemy:
    params: dict[str, object] = {
        "id": "mage",
        "name": "Chronomancer",
        "hp": hp,
        "max_hp": hp,
        "attack": 30,
        "defense": 40,
        "speed": 10,
        "archetype": "chronomancer",
    }
    params.update(overrides)
    return create_test_enemy(**params)  # type: ignore[arg-type]


def _hero(**overrides: object) -> Player:
    params: dict[str, object] = {"hp": 5000, "max_hp": 5000, "attack": 50, "speed": 99}
    params.update(overrides)
    return create_test_player(**params)  # type: ignore[arg-type]


def _combat(enemies: list[Enemy], player: Player | None = None, seed: int = 42) -> CombatContext:
    return CombatContext(
        combat_id="combat_001",
        seed=seed,
        player=player or _hero(),
        enemies=enemies,
        event_store=EventStore(":memory:"),
        session_id="sess_001",
        timeline_id="timeline_main",
    )


def _attack(combat: CombatContext) -> CombatAction:
    return CombatAction(action_type="attack", target_id=combat.living_enemies[0].id)


def _drive(combat: CombatContext, decide: Decide = _attack, max_steps: int = 400) -> None:
    """
    Run combat the way a front end must, honouring the enemy-rewind contract.

    `decide` returns the player's action, or None to stop at the player's turn.
    """
    boundary = {CombatPhase.INITIALIZING, CombatPhase.ROUND_START, CombatPhase.ROUND_END}
    for _ in range(max_steps):
        if combat.is_over:
            return
        if combat.phase in boundary:
            combat.start_round()
            continue
        current = combat.current_combatant
        if isinstance(current, Player):
            action = decide(combat)
            if action is None:
                return
            combat.submit_player_action(action)
        else:
            assert isinstance(current, Enemy)
            combat.execute_enemy_turn(current)
            if combat.phase is CombatPhase.AWAITING_PLAYER_INPUT:
                continue
        combat.advance_turn()
    raise AssertionError("combat did not finish")


def _events(combat: CombatContext, event_type: str | None = None) -> list[GameEvent]:
    events = [
        e
        for e in combat._event_store.get_events_by_timeline("timeline_main")
        if e.aggregate_id == combat.combat_id
    ]
    return [e for e in events if event_type is None or e.event_type == event_type]


def _stop_after(turns: int) -> Decide:
    taken = {"n": 0}

    def decide(combat: CombatContext) -> CombatAction | None:
        if taken["n"] >= turns:
            return None
        taken["n"] += 1
        return _attack(combat)

    return decide


def test_chronomancer_rewinds_after_a_big_hit() -> None:
    mage = _mage(hp=200)
    combat = _combat([mage])

    _drive(combat, _stop_after(1))

    rewinds = _events(combat, EventTypes.TEMPORAL_REWIND)
    assert len(rewinds) == 1
    assert json.loads(rewinds[0].event_data)["actor_id"] == mage.id
    assert mage.hp == mage.max_hp
    # Replay rebuilds her 1 charge at the earlier turn; the rewind's cost then stays spent.
    assert mage.temporal_charge == 0
    assert combat.phase is CombatPhase.AWAITING_PLAYER_INPUT
    assert combat.current_combatant is combat.player
    assert combat._current_branch_id == 1
    assert any("rewinds time" in line for line in combat.log_messages)


def test_combat_resumes_after_an_enemy_rewind_and_the_cap_ends_the_loop() -> None:
    mage = _mage(hp=200)
    combat = _combat([mage])

    _drive(combat)

    assert combat.outcome is CombatOutcome.VICTORY
    rewinds = len(_events(combat, EventTypes.TEMPORAL_REWIND))
    assert 1 <= rewinds <= 2
    assert combat.temporal_rewind_count(mage.id) == rewinds


def test_a_chronomancer_with_allies_does_not_echo_but_still_rewinds() -> None:
    mage = _mage(hp=200)
    ally = create_test_enemy(id="ally", hp=100_000, max_hp=100_000, speed=5)
    combat = _combat([mage, ally])

    _drive(combat, _stop_after(6))

    assert _events(combat, EventTypes.ECHO_SPAWNED) == []
    assert len(_events(combat, EventTypes.TEMPORAL_REWIND)) >= 1


def test_lone_chronomancer_echoes_and_the_echo_hits_the_player() -> None:
    mage = _mage(hp=100_000)
    combat = _combat([mage], player=_hero(max_temporal_charge=1))

    _drive(combat, _stop_after(6))

    spawned = _events(combat, EventTypes.ECHO_SPAWNED)
    acted = _events(combat, EventTypes.ECHO_ACTED)
    assert spawned and json.loads(spawned[0].event_data)["owner_id"] == mage.id
    assert acted and all(json.loads(e.event_data)["owner_id"] == mage.id for e in acted)
    assert any(json.loads(e.event_data)["target_id"] == combat.player.id for e in acted)
    assert _events(combat, EventTypes.TEMPORAL_REWIND) == []


def test_bait_the_counter_then_rewind_freely() -> None:
    mage = _mage(hp=100_000)
    combat = _combat([mage])
    outcomes: list[object] = []

    def decide(c: CombatContext) -> CombatAction | None:
        if c.round_number < 3:
            return _attack(c)
        if c.round_number == 3 and not outcomes:
            outcomes.append("echo")
            return CombatAction(action_type="echo_cast", target_id="", echo_turns=1)
        if c.round_number == 4:
            outcomes.append(c.temporal_system.rewind(c, c.player, turns=1))
            return None
        return _attack(c)

    _drive(combat, decide)

    counters = _events(combat, EventTypes.COUNTER_STOP_TRIGGERED)
    assert len(counters) == 1
    assert json.loads(counters[0].event_data)["target_ability"] == "echo_cast"
    assert _events(combat, EventTypes.ECHO_SPAWNED) == []
    assert isinstance(outcomes[1], RewindResult)
    assert not isinstance(outcomes[1], CounterStopResult)


def test_countered_enemy_rewind_passes_the_turn_as_a_defend() -> None:
    class PlayerCounters:
        def decide(self, combat, announcement, eligible):  # type: ignore[no-untyped-def]
            return eligible[0]

    mage = _mage(hp=200)
    combat = CombatContext(
        combat_id="combat_001",
        seed=42,
        player=_hero(temporal_charge=3),
        enemies=[mage],
        event_store=EventStore(":memory:"),
        session_id="sess_001",
        timeline_id="timeline_main",
        counter_policy=PlayerCounters(),
    )

    _drive(combat, _stop_after(1))

    assert _events(combat, EventTypes.TEMPORAL_REWIND) == []
    assert len(_events(combat, EventTypes.COUNTER_STOP_TRIGGERED)) == 1
    assert mage.hp < mage.max_hp
    assert combat._current_branch_id == 0
    assert any("defensive stance" in line for line in combat.log_messages)


def test_mirror_match_is_deterministic() -> None:
    def run() -> list[tuple[str, int, str]]:
        mage = _mage(hp=400)
        ally = create_test_enemy(id="ally", hp=120, max_hp=120, speed=5)
        combat = _combat([mage, ally], seed=1234)
        cast = {"rewound": False, "echoed": False}

        def decide(c: CombatContext) -> CombatAction | None:
            if c.round_number == 3 and not cast["rewound"] and c.player.temporal_charge >= 1:
                cast["rewound"] = True
                c.temporal_system.rewind(c, c.player, turns=1)
            if c.round_number >= 4 and not cast["echoed"] and c.player.temporal_charge >= 2:
                cast["echoed"] = True
                return CombatAction(action_type="echo_cast", target_id="", echo_turns=1)
            return CombatAction(
                action_type="attack", target_id=mage.id if mage.is_alive else "ally"
            )

        _drive(combat, decide)
        assert combat.outcome is CombatOutcome.VICTORY
        return [(e.event_type, e.branch_id, e.event_data) for e in _events(combat)]

    first, second = run(), run()

    assert first == second
    types = {t for t, _, _ in first}
    assert EventTypes.TEMPORAL_REWIND in types
    assert {b for _, b, _ in first} >= {0, 1, 2}
