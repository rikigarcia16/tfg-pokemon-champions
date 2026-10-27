"""Demo de consola: un combat narrat de l'agent contra el bot heurístic de poke-env."""

from __future__ import annotations

import asyncio
import sys
import time

from poke_env import AccountConfiguration
from poke_env.player import SimpleHeuristicsPlayer

from .play_vs_human import ROOT, NarratedAgent


async def main() -> None:
    tag = int(time.time()) % 10000
    agent = NarratedAgent(
        AccountConfiguration(f"TFGAgent{tag}", None),
        battle_format="gen9championsbssregmc",
        team=(ROOT / "teams" / "equip_a.txt").read_text(encoding="utf-8"),
        save_replays=str(ROOT / "replays_demo"),
        trace_dir=ROOT / "traces",
    )
    rival = SimpleHeuristicsPlayer(
        AccountConfiguration(f"Rival{tag}", None),
        battle_format="gen9championsbssregmc",
        team=(ROOT / "teams" / "equip_b.txt").read_text(encoding="utf-8"),
    )
    await agent.battle_against(rival, n_battles=1)
    battle = next(iter(agent.battles.values()))
    print(f"\nResultat: {'VICTÒRIA' if battle.won else 'DERROTA'} en {battle.turn} torns")
    print(f"Repetició desada a {ROOT / 'replays_demo'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    asyncio.run(main())
