@echo off
title NOVA v1.0 — Windows Setup & Installation
echo ========================================================
echo     NOVA v1.0 — Automated Windows Setup
echo ========================================================
echo Launching PowerShell Setup with Administrator/User rights...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"
echo.
pause
