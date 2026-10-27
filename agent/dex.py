"""Dades de Pokémon Champions exportades del mod de Showdown (tools/export_dex.js)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "champions_dex.json"

# Codis de damageTaken de Showdown: 0 neutre, 1 súper eficaç, 2 poc eficaç, 3 immune
_EFFECTIVENESS = {0: 1.0, 1: 2.0, 2: 0.5, 3: 0.0}


def to_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def species(species_id: str) -> dict | None:
    return _data()["species"].get(to_id(species_id))


def move(move_id: str) -> dict | None:
    return _data()["moves"].get(to_id(move_id))


def type_effectiveness(move_type: str, defender_types: list[str]) -> float:
    chart = _data()["typeChart"]
    mult = 1.0
    for t in defender_types:
        mult *= _EFFECTIVENESS[chart[t].get(move_type, 0)]
    return mult


def stat_value(base: int, stat_points: int, stat: str, nature_mult: float = 1.0) -> int:
    """Fórmula d'estadístiques de Champions a nivell 50 (data/mods/champions/scripts.ts)."""
    if stat == "hp":
        return base + stat_points + 75
    return int((base + stat_points + 20) * nature_mult)
