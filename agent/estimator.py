"""Estimador de dany per a Champions sota informació parcial.

Els Pokémon propis es descriuen amb les estadístiques exactes del |request| del servidor.
Els del rival s'estimen amb la fórmula de Champions i un supòsit explícit de punts
(SP_ASSUMED), que és la peça que el TFG substituirà per inferència amb dades d'ús.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from poke_env.battle import Pokemon, Status, Weather

from . import dex

# Supòsit de punts d'estadística del rival (màxim 32 per estadística, 66 en total).
# Pessimista en atac i velocitat: preferim sobreestimar l'amenaça.
SP_ASSUMED = {"hp": 16, "atk": 32, "def": 8, "spa": 32, "spd": 8, "spe": 32}
SPEED_NATURE_ASSUMED = 1.1
RANDOM_ROLL_MEAN = 0.925
UNKNOWN_BP = 60  # moviments de potència variable (Low Kick, Gyro Ball...)
HYPOTHETICAL_STAB_BP = 90

TYPE_ITEMS = {
    "blackbelt": "Fighting", "blackglasses": "Dark", "charcoal": "Fire", "dragonfang": "Dragon",
    "fairyfeather": "Fairy", "hardstone": "Rock", "magnet": "Electric", "metalcoat": "Steel",
    "miracleseed": "Grass", "mysticwater": "Water", "nevermeltice": "Ice", "poisonbarb": "Poison",
    "sharpbeak": "Flying", "silkscarf": "Normal", "silverpowder": "Bug", "softsand": "Ground",
    "spelltag": "Ghost", "twistedspoon": "Psychic",
}
IMMUNITY_ABILITIES = {
    "levitate": "Ground", "eartheater": "Ground", "flashfire": "Fire", "waterabsorb": "Water",
    "stormdrain": "Water", "dryskin": "Water", "voltabsorb": "Electric", "lightningrod": "Electric",
    "motordrive": "Electric", "sapsipper": "Grass",
}
ATE_ABILITIES = {"pixilate": "Fairy", "aerilate": "Flying", "refrigerate": "Ice", "galvanize": "Electric"}


def boost_mult(stage: int) -> float:
    return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)


@dataclass
class View:
    """El que l'agent sap (o suposa) d'un Pokémon en un moment del combat."""

    species: str
    types: list[str]
    stats: dict[str, int]
    hp_frac: float
    boosts: dict[str, int] = field(default_factory=dict)
    status: Status | None = None
    item: str | None = None
    ability: str | None = None
    possible_abilities: list[str] = field(default_factory=list)
    moves: list[str] = field(default_factory=list)
    is_opponent: bool = False

    @property
    def max_hp(self) -> int:
        return self.stats["hp"]

    def has_ability(self, ability_id: str) -> bool:
        if self.ability:
            return self.ability == ability_id
        return self.possible_abilities == [ability_id]

    def speed(self) -> float:
        spe = self.stats["spe"] * boost_mult(self.boosts.get("spe", 0))
        if self.item == "choicescarf":
            spe *= 1.5
        if self.status == Status.PAR:
            spe *= 0.5
        return spe


def _species_entry(mon: Pokemon) -> dict:
    return dex.species(mon.species) or dex.species(mon.base_species) or {
        "types": [t.name.title() for t in mon.types if t is not None],
        "baseStats": mon.base_stats,
        "abilities": [],
    }


def _known(value: str | None) -> str | None:
    return None if value in (None, "", "unknown_item") else value


def view_own(mon: Pokemon) -> View:
    entry = _species_entry(mon)
    stats = {k: v for k, v in (mon.stats or {}).items() if v}
    stats["hp"] = mon.max_hp or dex.stat_value(entry["baseStats"]["hp"], 0, "hp")
    for stat in ("atk", "def", "spa", "spd", "spe"):
        stats.setdefault(stat, dex.stat_value(entry["baseStats"][stat], 0, stat))
    return View(
        species=mon.species,
        types=entry["types"],
        stats=stats,
        hp_frac=mon.current_hp_fraction,
        boosts=dict(mon.boosts),
        status=mon.status,
        item=_known(mon.item),
        ability=mon.ability,
        moves=list(mon.moves),
    )


def view_opponent(mon: Pokemon) -> View:
    entry = _species_entry(mon)
    base = entry["baseStats"]
    stats = {s: dex.stat_value(base[s], SP_ASSUMED[s], s) for s in SP_ASSUMED}
    stats["spe"] = int(stats["spe"] * SPEED_NATURE_ASSUMED)
    return View(
        species=mon.species,
        types=entry["types"],
        stats=stats,
        hp_frac=mon.current_hp_fraction,
        boosts=dict(mon.boosts),
        status=mon.status,
        item=_known(mon.item),
        ability=mon.ability,
        possible_abilities=[dex.to_id(a) for a in entry.get("abilities", [])],
        moves=list(mon.moves),
        is_opponent=True,
    )


def _damage(att: View, dfn: View, move_type: str, bp: float, physical: bool,
            weather: dict | None, hits: float = 1) -> float:
    if move_type == "Normal":
        for ability, new_type in ATE_ABILITIES.items():
            if att.has_ability(ability):
                move_type, bp = new_type, bp * 1.2
    for ability, immune_type in IMMUNITY_ABILITIES.items():
        if move_type == immune_type and dfn.has_ability(ability):
            return 0.0
    eff = dex.type_effectiveness(move_type, dfn.types)
    if eff == 0:
        return 0.0

    a_stat, d_stat = ("atk", "def") if physical else ("spa", "spd")
    attack = att.stats[a_stat] * boost_mult(att.boosts.get(a_stat, 0))
    defense = dfn.stats[d_stat] * boost_mult(dfn.boosts.get(d_stat, 0))
    damage = math.floor(math.floor(22 * bp * attack / defense) / 50) + 2

    mods = RANDOM_ROLL_MEAN * eff * hits
    if move_type in att.types:
        mods *= 2.0 if att.has_ability("adaptability") else 1.5
    if physical and att.status == Status.BRN and not att.has_ability("guts"):
        mods *= 0.5
    weather = weather or {}
    if Weather.SUNNYDAY in weather or Weather.DESOLATELAND in weather:
        mods *= {"Fire": 1.5, "Water": 0.5}.get(move_type, 1.0)
    if Weather.RAINDANCE in weather or Weather.PRIMORDIALSEA in weather:
        mods *= {"Water": 1.5, "Fire": 0.5}.get(move_type, 1.0)
    if att.item == "lifeorb":
        mods *= 1.3
    if att.item and TYPE_ITEMS.get(att.item) == move_type:
        mods *= 1.2
    if att.item == "expertbelt" and eff > 1:
        mods *= 1.2
    if (att.item == "muscleband" and physical) or (att.item == "wiseglasses" and not physical):
        mods *= 1.1
    if dfn.has_ability("multiscale") and dfn.hp_frac >= 1.0:
        mods *= 0.5
    return damage * mods / dfn.max_hp


def damage_fraction(att: View, dfn: View, move_id: str, weather: dict | None = None) -> float:
    """Dany esperat (sense precisió) com a fracció dels PS màxims del defensor."""
    mv = dex.move(move_id)
    if mv is None or mv["category"] == "Status":
        return 0.0
    hits = mv["multihit"] or 1
    if isinstance(hits, list):
        hits = 3
    return _damage(att, dfn, mv["type"], mv["basePower"] or UNKNOWN_BP,
                   mv["category"] == "Physical", weather, hits)


def best_damage(att: View, dfn: View, weather: dict | None = None) -> tuple[float, str]:
    """Millor dany esperat (amb precisió) d'att contra dfn i el moviment que el fa.

    Per al rival, als moviments revelats s'hi afegeix un moviment STAB hipotètic per
    cada tipus: no haver vist un moviment no vol dir que no el tingui.
    """
    best, best_move = 0.0, "cap"
    for move_id in att.moves:
        mv = dex.move(move_id)
        acc = mv["accuracy"] / 100 if mv else 1.0
        dmg = damage_fraction(att, dfn, move_id, weather) * acc
        if dmg > best:
            best, best_move = dmg, move_id
    if att.is_opponent:
        physical = att.stats["atk"] >= att.stats["spa"]
        for stab_type in att.types:
            dmg = _damage(att, dfn, stab_type, HYPOTHETICAL_STAB_BP, physical, weather)
            if dmg > best:
                best, best_move = dmg, f"STAB {stab_type} suposat"
    return best, best_move
