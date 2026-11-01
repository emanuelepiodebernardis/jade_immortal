@echo off
rem Jade Immortal: avvia il gioco anche per il telefono (stessa Wi-Fi di casa).
rem La prima volta Windows chiede il permesso del firewall: scegli "Reti private" e consenti.
cd /d "%~dp0"
python dashboard.py --rete
pause
