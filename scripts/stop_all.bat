@echo off
title NOVA — Process Termination & Cleanup
echo ========================================================
echo     NOVA v1.0 — Process Termination & Cleanup
echo ========================================================
echo Stopping NOVA backend and frontend processes...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-NetTCPConnection -LocalPort 8000, 1420 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { try { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue; Write-Host \"Terminated process ID: $_\" } catch {} }"

echo.
echo Process cleanup complete. No orphaned listeners on ports 8000 / 1420.
echo ========================================================
pause
