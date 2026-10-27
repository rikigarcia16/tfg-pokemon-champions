@echo off
rem Un combat narrat de l'agent contra el bot heuristic (cal tenir 1_servidor.bat obert)
chcp 65001 > nul
cd /d "%~dp0"
".venv\Scripts\python.exe" -m agent.demo
pause
