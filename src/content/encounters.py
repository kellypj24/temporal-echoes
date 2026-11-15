"""
Authored combat encounters.

Each encounter is a frozen spec — pure data describing who fights whom and
with what stats. `Encounter.build()` turns a spec into fresh `Player` /
`Enemy` entities; nothing here holds mutable combat state, so replaying an
encounter from the same spec and seed produces an identical fight.

Tuning notes (damage formula is `ATK * 100 / (DEF * 0.5 + 10)`, times a
0.85–1.0 variance roll):
- Encounters are tuned so a player who only ever attacks wins the first
  fight, is pressured in the second, and needs Boost Points or a temporal
  ability in the third.
- Every enemy is weak to PHYSICAL so a basic attack can reach the Break
  System without an elemental skill tree (skills land in Phase 5).
"""

from dataclasses import dataclass, field

from src.entities import DamageType, Enemy, Player


@dataclass(frozen=True)
class PlayerSpec:
    """
    Starting stats for the player in an encounter.

    Attributes:
        name: Display name.
        level: Character level (cosmetic until the progression system lands).
        max_hp: Starting and maximum HP.
        attack: Attack stat, numerator of the damage formula.
        defense: Defense stat, denominator of incoming damage.
        speed: Turn-order stat; higher acts earlier.
        max_boost_points: BP cap (1 BP granted per round).
        max_temporal_charge: Temporal charge cap (1 charge granted per round).
    """

    name: str
    level: int
    max_hp: int
    attack: int
    defense: int
    speed: int
    max_boost_points: int = 5
    max_temporal_charge: int = 3

    def build(self, combatant_id: str = "player_1", hp: int | None = None) -> Player:
        """
        Instantiate a `Player` with empty BP and charge.

        Args:
            combatant_id: Unique combatant id used in events and targeting.
            hp: Starting HP, clamped to [1, max_hp]. None means full HP.

        Returns:
            A fresh `Player` entity.
        """
        start_hp = self.max_hp if hp is None else max(1, min(hp, self.max_hp))
        return Player(
            id=combatant_id,
            name=self.name,
            level=self.level,
            hp=start_hp,
            max_hp=self.max_hp,
            attack=self.attack,
            defense=self.defense,
            speed=self.speed,
            boost_points=0,
            max_boost_points=self.max_boost_points,
            temporal_charge=0,
            max_temporal_charge=self.max_temporal_charge,
        )


@dataclass(frozen=True)
class EnemySpec:
    """
    Stats for one enemy in an encounter.

    Attributes:
        id: Unique combatant id — this is what the player types to target.
        name: Display name.
        level: Enemy level (cosmetic).
        max_hp: Starting and maximum HP.
        attack: Attack stat.
        defense: Defense stat.
        speed: Turn-order stat.
        shield_points: Break System shield; each weakness hit removes one.
        weaknesses: Damage types that chip the shield.
        archetype: AI behaviour ("aggressive", "defensive", "tactical",
            "berserker", "chronomancer").
    """

    id: str
    name: str
    level: int
    max_hp: int
    attack: int
    defense: int
    speed: int
    shield_points: int
    weaknesses: tuple[DamageType, ...] = (DamageType.PHYSICAL,)
    archetype: str = "aggressive"

    def build(self) -> Enemy:
        """
        Instantiate an `Enemy` at full HP with a full shield.

        Returns:
            A fresh `Enemy` entity.
        """
        return Enemy(
            id=self.id,
            name=self.name,
            level=self.level,
            hp=self.max_hp,
            max_hp=self.max_hp,
            attack=self.attack,
            defense=self.defense,
            speed=self.speed,
            shield_points=self.shield_points,
            max_shield_points=self.shield_points,
            weaknesses=list(self.weaknesses),
            archetype=self.archetype,
        )


@dataclass(frozen=True)
class Encounter:
    """
    A named, self-contained fight.

    Attributes:
        id: Short slug used on the command line.
        title: Display title shown above the fight.
        intro: Scene-setting text shown once, before round 1.
        seed: Default RNG seed; the same seed replays the same fight.
        player: The player's starting stats for this encounter.
        enemies: Enemies to fight, in roster order.
    """

    id: str
    title: str
    intro: str
    seed: int
    player: PlayerSpec
    enemies: tuple[EnemySpec, ...] = field(default_factory=tuple)

    def build(self, player_hp: int | None = None) -> tuple[Player, list[Enemy]]:
        """
        Instantiate fresh entities for this encounter.

        Args:
            player_hp: The player's starting HP, clamped to [1, max_hp].
                None means full HP.

        Returns:
            A `(player, enemies)` pair; enemies are at full HP.
        """
        return self.player.build(hp=player_hp), [spec.build() for spec in self.enemies]


_SUNDIAL = Encounter(
    id="sundial",
    title="The Sundial Courtyard",
    intro=(
        "Frost creeps across a stopped sundial. Something built of gears and "
        "grievance unfolds itself from the dial's shadow and turns to face you."
    ),
    seed=1337,
    player=PlayerSpec(
        name="Kael",
        level=5,
        max_hp=520,
        attack=45,
        defense=55,
        speed=40,
    ),
    enemies=(
        EnemySpec(
            id="sentry_1",
            name="Clockwork Sentry",
            level=4,
            max_hp=340,
            attack=34,
            defense=32,
            speed=22,
            shield_points=2,
            archetype="aggressive",
        ),
    ),
)

_CROSSROADS = Encounter(
    id="crossroads",
    title="Crossroads Ambush",
    intro=(
        "Two silhouettes step out of the same second, a half-breath apart. "
        "They have been waiting here for a long time — possibly for you, "
        "possibly for a you who has not happened yet."
    ),
    seed=7,
    player=PlayerSpec(
        name="Kael",
        level=7,
        max_hp=600,
        attack=45,
        defense=58,
        speed=38,
    ),
    enemies=(
        EnemySpec(
            id="raider_1",
            name="Timeworn Raider",
            level=6,
            max_hp=260,
            attack=30,
            defense=34,
            speed=28,
            shield_points=2,
            archetype="aggressive",
        ),
        EnemySpec(
            id="raider_2",
            name="Hollow Raider",
            level=6,
            max_hp=260,
            attack=30,
            defense=34,
            speed=24,
            shield_points=2,
            archetype="defensive",
        ),
    ),
)

_GATE = Encounter(
    id="gate",
    title="The Chronomancer's Gate",
    intro=(
        "The Chronomancer does not draw a weapon. She watches your hands, and "
        "the moment before your hands move — and she is willing to spend "
        "everything she has to make sure that moment never arrives."
    ),
    seed=99,
    player=PlayerSpec(
        name="Kael",
        level=10,
        max_hp=700,
        attack=48,
        defense=58,
        speed=36,
    ),
    enemies=(
        EnemySpec(
            id="chronomancer",
            name="The Chronomancer",
            level=12,
            max_hp=380,
            attack=30,
            defense=40,
            speed=34,
            shield_points=3,
            archetype="chronomancer",
        ),
        EnemySpec(
            id="acolyte_1",
            name="Gate Acolyte",
            level=8,
            max_hp=150,
            attack=22,
            defense=28,
            speed=26,
            shield_points=1,
            archetype="aggressive",
        ),
        EnemySpec(
            id="acolyte_2",
            name="Gate Acolyte",
            level=8,
            max_hp=150,
            attack=22,
            defense=28,
            speed=20,
            shield_points=1,
            archetype="defensive",
        ),
    ),
)

ENCOUNTERS: dict[str, Encounter] = {enc.id: enc for enc in (_SUNDIAL, _CROSSROADS, _GATE)}
"""All authored encounters, keyed by id, in intended play order."""

DEFAULT_ENCOUNTER_ID = _SUNDIAL.id
"""Encounter used when the player does not name one."""


def get_encounter(encounter_id: str) -> Encounter:
    """
    Look up an encounter by id.

    Args:
        encounter_id: Encounter slug (see `ENCOUNTERS`).

    Returns:
        The matching `Encounter`.

    Raises:
        KeyError: If no encounter has that id.
    """
    try:
        return ENCOUNTERS[encounter_id]
    except KeyError:
        known = ", ".join(ENCOUNTERS)
        raise KeyError(f"Unknown encounter '{encounter_id}'. Available: {known}") from None


def list_encounters() -> list[Encounter]:
    """Return all encounters in intended play order."""
    return list(ENCOUNTERS.values())
