@echo off
title NOVA — Unified Launcher
echo ========================================================
echo     NOVA — Neural Operational Virtual Assistant v0.1
echo ========================================================
echo Starting Backend AI Engine...
start cmd /k "%~dp0start_backend.bat"
timeout /t 2 /nobreak >nul
echo Starting Desktop Command Center Frontend...
start cmd /k "%~dp0start_frontend.bat"
echo.
echo NOVA System Initialization Complete.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:1420
echo ========================================================
pause
