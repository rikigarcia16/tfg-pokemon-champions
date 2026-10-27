"""Agent heurístic per a Champions individuals (motor v1 de l'avantprojecte).

Per a cada acció legal calcula una puntuació a partir de:
  D  dany esperat (fracció de PS que treu al rival, amb bonus si debilita)
  K  risc de ser debilitat abans d'actuar (ordre de velocitat i amenaça del rival)
  T  avantatge d'enfrontament en els canvis
i tria la més alta. Cada decisió es desa a `self.traces` amb les alternatives i el motiu.

Les funcions de puntuació reben `View`s i no l'objecte Battle, perquè es puguin reutilitzar
per a dobles (avaluant cada parella atacant-objectiu).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from poke_env.battle import AbstractBattle, Battle
from poke_env.player import Player

from . import dex
from .estimator import View, best_damage, damage_fraction, view_opponent, view_own

PROTECT_MOVES = {"protect", "detect", "spikyshield", "kingsshield", "banefulbunker", "silktrap",
                 "burningbulwark"}
HEAL_MOVES = {"roost", "recover", "slackoff", "softboiled", "moonlight", "synthesis", "morningsun",
              "shoreup", "milkdrink"}
KO_BONUS = 0.6
SWITCH_TEMPO_COST = 0.15

log = logging.getLogger(__name__)


@dataclass
class Candidate:
    label: str
    score: float
    reason: str
    order: object = None


def move_first(me: View, opp: View, priority: int) -> bool:
    return priority > 0 or (priority == 0 and me.speed() > opp.speed())


def score_move(me: View, opp: View, move_id: str, weather: dict, opp_threat: float,
               last_move: str | None) -> tuple[float, str]:
    mv = dex.move(move_id)
    if mv is None:
        return 0.0, "moviment desconegut"
    first = move_first(me, opp, mv["priority"])
    dies_first = not first and opp_threat >= me.hp_frac

    if mv["category"] != "Status":
        acc = mv["accuracy"] / 100
        dmg = damage_fraction(me, opp, move_id, weather)
        knocks_out = dmg >= opp.hp_frac
        score = acc * (min(dmg, opp.hp_frac) + (KO_BONUS if knocks_out else 0.0))
        reason = f"treu ~{dmg:.0%} (rival a {opp.hp_frac:.0%})"
        if knocks_out:
            reason += ", debilita"
        if acc < 1:
            reason += f", precisió {acc:.0%}"
        if mv["selfSwitch"]:
            score += 0.05
        if dies_first:
            score *= 0.25
            reason += "; però el rival és més ràpid i ens debilita abans"
        return score, reason

    boosts = mv["selfBoost"] or (mv["boosts"] if mv["target"] == "self" else None)
    if boosts:
        main = max(boosts, key=boosts.get)
        if me.hp_frac >= 0.6 and opp_threat < 0.45 and me.boosts.get(main, 0) < 2:
            return 0.45, f"millora {main}; el rival només treu ~{opp_threat:.0%}"
        return 0.02, "millora d'estadístiques massa arriscada ara"
    if move_id == "willowisp":
        physical = opp.stats["atk"] > opp.stats["spa"]
        if opp.status is None and "Fire" not in opp.types and physical:
            return 0.45 * mv["accuracy"] / 100, "cremar un atacant físic"
        return 0.0, "cremada inútil contra aquest rival"
    if move_id in HEAL_MOVES or mv["heal"]:
        if me.hp_frac < 0.55 and opp_threat < 0.5:
            return 0.5, "recuperar PS amb poc risc"
        return 0.02, "no cal curar-se"
    if move_id in PROTECT_MOVES:
        if last_move in PROTECT_MOVES:
            return 0.0, "protecció consecutiva pot fallar"
        return 0.08 if dies_first else 0.04, "protecció"
    if mv["selfSwitch"]:
        return 0.2, "pivot de suport"
    return 0.05, "moviment d'estat"


def score_switch(candidate: View, opp: View, weather: dict) -> tuple[float, str]:
    incoming, _ = best_damage(opp, candidate, weather)
    outgoing, out_move = best_damage(candidate, opp, weather)
    survives = incoming < candidate.hp_frac * 0.9
    score = 0.5 * (outgoing - incoming) - SWITCH_TEMPO_COST - (0.0 if survives else 1.0)
    reason = f"rep ~{incoming:.0%} en entrar, després treu ~{outgoing:.0%} amb {out_move}"
    return score, reason


def matchup(mine: View, theirs: View) -> float:
    return best_damage(mine, theirs)[0] - best_damage(theirs, mine)[0]


class HeuristicAgent(Player):
    def __init__(self, *args, trace_dir: Path | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.traces: dict[str, list[dict]] = {}
        self.errors = 0
        self._trace_dir = trace_dir

    # --- Team preview: tria 3 de 6 segons enfrontaments ---------------------------------
    def teampreview(self, battle: AbstractBattle) -> str:
        team = list(battle.team.values())
        rivals = [view_opponent(p) for p in battle.teampreview_opponent_team]
        if not rivals:
            return self.random_teampreview(battle)
        scores = []
        for i, mon in enumerate(team, start=1):
            mine = view_own(mon)
            scores.append((sum(matchup(mine, r) for r in rivals) / len(rivals), i, mon))
        scores.sort(reverse=True)
        picked = scores[:3]
        for _, _, mon in picked:
            mon._selected_in_teampreview = True
        self._record(battle, {
            "turn": 0,
            "type": "team preview",
            "candidates": [{"action": m.species, "score": round(s, 3)} for s, _, m in scores],
            "chosen": [m.species for _, _, m in picked],
        })
        return "/team " + "".join(str(i) for _, i, _ in picked) + "".join(
            str(i) for _, i, _ in scores[3:])

    # --- Decisió de cada torn -------------------------------------------------------------
    def choose_move(self, battle: AbstractBattle):
        try:
            return self._choose(battle)
        except Exception:  # noqa: BLE001 - una excepció no ha de fer perdre el combat
            self.errors += 1
            log.exception("Error de l'agent al torn %s", battle.turn)
            return self.choose_random_move(battle)

    def _choose(self, battle: Battle):
        weather = battle.weather
        opp_mon = battle.opponent_active_pokemon
        if opp_mon is None or battle.active_pokemon is None:
            return self.choose_random_move(battle)
        opp = view_opponent(opp_mon)
        candidates: list[Candidate] = []

        if battle.force_switch or not battle.available_moves:
            for mon in battle.available_switches:
                s, why = score_switch(view_own(mon), opp, weather)
                candidates.append(Candidate(f"canvi a {mon.species}", s, why, self.create_order(mon)))
        else:
            me = view_own(battle.active_pokemon)
            opp_threat, threat_move = best_damage(opp, me, weather)
            last = self._last_move(battle)
            mega = battle.can_mega_evolve
            for move in battle.available_moves:
                s, why = score_move(me, opp, move.id, weather, opp_threat, last)
                label = move.id + (" + mega" if mega else "")
                candidates.append(Candidate(label, s, why, self.create_order(move, mega=mega)))
            best_move_score = max(c.score for c in candidates)
            dies_first = opp_threat >= me.hp_frac and me.speed() <= opp.speed()
            if dies_first or best_move_score < 0.25:
                for mon in battle.available_switches:
                    s, why = score_switch(view_own(mon), opp, weather)
                    candidates.append(Candidate(f"canvi a {mon.species}", s, why,
                                                self.create_order(mon)))
            context = (f"{me.species} {me.hp_frac:.0%} vs {opp.species} {opp.hp_frac:.0%}; "
                       f"amenaça rival ~{opp_threat:.0%} ({threat_move})")

        if not candidates:
            return self.choose_random_move(battle)
        candidates.sort(key=lambda c: c.score, reverse=True)
        chosen = candidates[0]
        self._record(battle, {
            "turn": battle.turn,
            "type": "canvi forçat" if battle.force_switch else "torn",
            "context": None if battle.force_switch else context,
            "candidates": [{"action": c.label, "score": round(c.score, 3), "reason": c.reason}
                           for c in candidates[:5]],
            "chosen": chosen.label,
        })
        return chosen.order

    def _last_move(self, battle: Battle) -> str | None:
        decisions = self.traces.get(battle.battle_tag, [])
        if not decisions or decisions[-1]["type"] != "torn" or decisions[-1]["turn"] != battle.turn - 1:
            return None
        return decisions[-1]["chosen"].removesuffix(" + mega")

    def _record(self, battle: AbstractBattle, entry: dict) -> None:
        self.traces.setdefault(battle.battle_tag, []).append(entry)

    def _battle_finished_callback(self, battle: AbstractBattle) -> None:
        if self._trace_dir is None:
            return
        self._trace_dir.mkdir(parents=True, exist_ok=True)
        out = {"battle": battle.battle_tag, "won": battle.won,
               "decisions": self.traces.get(battle.battle_tag, [])}
        (self._trace_dir / f"{battle.battle_tag}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
