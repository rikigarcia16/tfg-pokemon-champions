@echo off
rem Jugar contra l'agent al navegador (cal tenir 1_servidor.bat obert)
chcp 65001 > nul
cd /d "%~dp0"
rem Client web de Showdown servit en local al port 8080
start "Client Showdown (no tancar)" /min ".venv\Scripts\python.exe" -m http.server 8080 --bind 127.0.0.1 --directory client\play.pokemonshowdown.com
timeout /t 2 > nul
start "" "http://localhost:8080/jugar.html"
echo Al navegador: tria un nom, carrega un equip i repta TFGAgent
echo al format [Gen 9 Champions] BSS Reg M-C. Les decisions surten aqui.
".venv\Scripts\python.exe" -m agent.play_vs_human --team equip_a --battles 10
pause
