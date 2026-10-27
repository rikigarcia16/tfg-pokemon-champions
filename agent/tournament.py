"""Mini torneig: l'agent heurístic contra els baselines de poke-env al format Champions.

Ús (amb el servidor local engegat al port 8000):
    python -m agent.tournament --battles 50

Cada enfrontament es juga amb els equips en els dos sentits (A contra B i B contra A)
perquè el resultat no depengui de quin equip és millor.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from pathlib import Path

from poke_env import AccountConfiguration
from poke_env.player import MaxBasePowerPlayer, RandomPlayer, SimpleHeuristicsPlayer

from .heuristic import HeuristicAgent

FORMAT = "gen9championsbssregmc"
ROOT = Path(__file__).resolve().parent.parent
TEAMS = {name: (ROOT / "teams" / f"{name}.txt").read_text(encoding="utf-8")
         for name in ("equip_a", "equip_b")}
BASELINES = {
    "Aleatori": RandomPlayer,
    "MaxPotencia": MaxBasePowerPlayer,
    "HeuristicPokeEnv": SimpleHeuristicsPlayer,
}


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


async def play(baseline_name: str, our_team: str, their_team: str, n: int, run: int) -> dict:
    tag = f"{run}{our_team[-1]}"
    ours = HeuristicAgent(
        AccountConfiguration(f"TFGAgent{baseline_name[:4]}{tag}", None),
        battle_format=FORMAT, team=TEAMS[our_team], max_concurrent_battles=10,
        save_replays=str(ROOT / "replays"), trace_dir=ROOT / "traces",
    )
    rival = BASELINES[baseline_name](
        AccountConfiguration(f"{baseline_name[:10]}{tag}", None),
        battle_format=FORMAT, team=TEAMS[their_team], max_concurrent_battles=10,
    )
    start = time.perf_counter()
    await ours.battle_against(rival, n_battles=n)
    elapsed = time.perf_counter() - start
    return {
        "rival": baseline_name, "equip_agent": our_team, "equip_rival": their_team,
        "combats": ours.n_finished_battles, "victories": ours.n_won_battles,
        "errors_agent": ours.errors, "segons": round(elapsed, 1),
    }


async def main(n: int) -> None:
    run = int(time.time()) % 1000
    rows = []
    for baseline in BASELINES:
        for our_team, their_team in (("equip_a", "equip_b"), ("equip_b", "equip_a")):
            row = await play(baseline, our_team, their_team, n, run)
            rows.append(row)
            print(f"{baseline:17} {our_team} vs {their_team}: "
                  f"{row['victories']}/{row['combats']}  (errors: {row['errors_agent']})")

    summary = []
    for baseline in BASELINES:
        wins = sum(r["victories"] for r in rows if r["rival"] == baseline)
        total = sum(r["combats"] for r in rows if r["rival"] == baseline)
        lo, hi = wilson(wins, total)
        summary.append({"rival": baseline, "victories": wins, "combats": total,
                        "taxa": wins / total, "ic95": [lo, hi]})

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "resultats.json").write_text(
        json.dumps({"format": FORMAT, "detall": rows, "resum": summary}, indent=1),
        encoding="utf-8")
    lines = ["| Rival | Victòries agent | Taxa | IC 95% |", "| --- | --- | --- | --- |"]
    for s in summary:
        lines.append(f"| {s['rival']} | {s['victories']}/{s['combats']} | {s['taxa']:.0%} | "
                     f"{s['ic95'][0]:.0%}–{s['ic95'][1]:.0%} |")
    (out / "resultats.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--battles", type=int, default=50, help="combats per sentit i rival")
    asyncio.run(main(parser.parse_args().battles))
