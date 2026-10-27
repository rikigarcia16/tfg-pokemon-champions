# Prova de concepte · Agent per a Pokémon Champions a Showdown

Agent que juga combats de **Pokémon Champions** (format `[Gen 9 Champions] BSS Reg M-C`,
individuals, 6 trien 3) en un servidor local de Pokémon Showdown. Correspon al motor v1
de l'avantprojecte: puntuació d'un torn amb dany esperat, risc de ser debilitat i
enfrontaments.

## Demo ràpida (per ensenyar)

1. Doble clic a `1_servidor.bat` i deixar la finestra oberta.
2. Doble clic a `3_demo_consola.bat`: l'agent juga un combat contra el bot heurístic de
   poke-env i, a cada torn, mostra les tres millors accions, la seva puntuació i el motiu.
   La repetició queda a `replays_demo/` i s'obre amb doble clic (necessita internet).

**Jugar contra l'agent** (`2_jugar_contra_agent.bat`, amb `1_servidor.bat` obert):

1. S'obre el navegador a `http://localhost:8080/jugar.html`.
2. *Elegir nombre* → qualsevol nom (no cal contrasenya).
3. *Editor de equipos* → *Nuevo equipo* → *Importar*, enganxar `teams/equip_b.txt`,
   i triar el format *[Gen 9 Champions] BSS Reg M-C*.
4. *Buscar un usuario* → `TFGAgent` → *Retar*, amb aquest format i equip.
5. A la finestra de l'agent es veu el raonament de cada torn.

El client de Showdown (`client/`, `smogon/pokemon-showdown-client`, commit `702e90d`)
es serveix en local perquè `http://localhost:8000` redirigeix a `localhost.psim.us`, que
el 27-10-2026 donava error 522. `jugar.html` el genera `tools/fer_jugar_html.py`: és el
client de prova amb el nom d'usuari enviat directament al servidor local, sense passar
pel servidor d'inicis de sessió oficial.

## Torneig contra baselines

```
.venv\Scripts\python.exe -m agent.tournament --battles 50
```

Juga 50 combats per sentit (equips intercanviats) contra tres rivals de poke-env i
escriu `results/resultats.md`. Desa les repeticions a `replays/` (s'obren amb el
navegador) i la traça de cada decisió a `traces/`.

## Estructura

| Ruta | Què hi ha |
| --- | --- |
| `showdown/` | Pokémon Showdown (commit `cbdc851`, 26-10-2026) amb el mod `champions` |
| `tools/node-v22.11.0-win-x64/` | Node portable (no cal instal·lar res) |
| `tools/export_dex.js` | Exporta espècies, moviments i taula de tipus del mod Champions |
| `tools/validate.js` | Valida un equip contra un format: `node tools/validate.js <format> <fitxer>` |
| `agent/dex.py` | Dades de Champions i fórmula d'estadístiques (punts en lloc d'EV) |
| `agent/estimator.py` | Estimador de dany sota informació parcial |
| `agent/heuristic.py` | Agent: team preview, puntuació de moviments i canvis, traça |
| `agent/tournament.py` | Torneig reproduïble amb IC del 95% (Wilson) |
| `agent/play_vs_human.py` | Demo contra un humà amb decisions narrades |
| `teams/` | Equips de prova validats per a Reg M-C |

## Coses apreses al pilot

- Showdown ja implementa Champions (`data/mods/champions`); poke-env 0.16.1 el juga sense canvis.
- Al mod Champions el camp `EVs` conté **punts d'estadística** (0–32, 66 en total) i la
  fórmula a nivell 50 és `base + punts + 20` (PS: `base + punts + 75`).
- La calculadora de poke-env necessita les estadístiques exactes del rival, que en un
  combat real no es coneixen: per això l'agent té el seu propi estimador.
- Llista d'objectes reduïda: no hi ha Choice Band/Specs ni Heavy-Duty Boots.

## Limitacions conegudes (feina del TFG)

- El rival s'estima amb un supòsit fix de punts; no hi ha inferència amb dades d'ús.
- Horitzó d'un torn; no hi ha cerca ni simulació.
- La Megaevolució s'activa sempre que es pot.
- Habilitats i objectes només parcialment modelats.
