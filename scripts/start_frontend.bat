@echo off
title NOVA Command Center — Frontend
cd /d "%~dp0\..\apps\desktop"
echo [NOVA] Launching Desktop Frontend on http://localhost:1420 ...
npm run dev
pause
