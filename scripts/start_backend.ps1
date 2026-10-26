# NOVA Backend Launcher
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptDir\..\backend"
Write-Host "[NOVA] Launching FastAPI AI Engine on http://127.0.0.1:8000..." -ForegroundColor Cyan
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
