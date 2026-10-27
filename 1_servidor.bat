@echo off
rem Engega el servidor local de Pokemon Showdown al port 8000
cd /d "%~dp0showdown"
"%~dp0tools\node-v22.11.0-win-x64\node.exe" pokemon-showdown start --no-security 8000
