"""Demo: l'agent espera reptes d'un humà al servidor local i mostra cada decisió en directe.

1. Engegar el servidor:   node showdown/pokemon-showdown start --no-security 8000
2. Engegar l'agent:       python -m agent.play_vs_human
3. Obrir http://localhost:8000, triar un nom, i reptar "TFGAgent" al format
   [Gen 9 Champions] BSS Reg M-C amb un equip legal (p. ex. teams/equip_b.txt).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from poke_env import AccountConfiguration

from .heuristic import HeuristicAgent

ROOT = Path(__file__).resolve().parent.parent


class NarratedAgent(HeuristicAgent):
    def _record(self, battle, entry):
        super()._record(battle, entry)
        if entry["type"] == "team preview":
            print(f"\n[Team preview] triats: {', '.join(entry['chosen'])}")
            return
        print(f"\n[Torn {entry['turn']}] {entry.get('context') or entry['type']}")
        for c in entry["candidates"][:3]:
            mark = "->" if c["action"] == entry["chosen"] else "  "
            print(f"  {mark} {c['action']:<24} {c['score']:>6.2f}  {c['reason']}")


async def main(team: str, n: int) -> None:
    agent = NarratedAgent(
        AccountConfiguration("TFGAgent", None),
        battle_format="gen9championsbssregmc",
        team=(ROOT / "teams" / f"{team}.txt").read_text(encoding="utf-8"),
        save_replays=str(ROOT / "replays"),
        trace_dir=ROOT / "traces",
    )
    print(f"TFGAgent connectat amb {team}. Repta'l des de http://localhost:8000")
    await agent.accept_challenges(None, n)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", default="equip_a")
    parser.add_argument("--battles", type=int, default=1)
    args = parser.parse_args()
    asyncio.run(main(args.team, args.battles))
