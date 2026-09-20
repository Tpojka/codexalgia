@echo off
REM Windows: remove Codexalgia.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 -m codexalgia.install uninstall) else (python -m codexalgia.install uninstall)
