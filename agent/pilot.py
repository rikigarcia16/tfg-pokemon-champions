"""Pilot: dos jugadors aleatoris al format Champions BSS per comprovar que poke-env funciona."""

import asyncio
import sys
from pathlib import Path

from poke_env import AccountConfiguration
from poke_env.player import RandomPlayer

FORMAT = "gen9championsbssregmc"
TEAMS = Path(__file__).resolve().parent.parent / "teams"


async def main(n_battles: int) -> None:
    p1 = RandomPlayer(
        AccountConfiguration("PilotA", None),
        battle_format=FORMAT,
        team=(TEAMS / "equip_a.txt").read_text(encoding="utf-8"),
    )
    p2 = RandomPlayer(
        AccountConfiguration("PilotB", None),
        battle_format=FORMAT,
        team=(TEAMS / "equip_b.txt").read_text(encoding="utf-8"),
    )
    await p1.battle_against(p2, n_battles=n_battles)
    print(f"Combats: {p1.n_finished_battles}  vict. A: {p1.n_won_battles}  vict. B: {p2.n_won_battles}")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 30))
