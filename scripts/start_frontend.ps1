# NOVA Frontend Launcher
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptDir\..\apps\desktop"
Write-Host "[NOVA] Launching Desktop Frontend on http://localhost:1420..." -ForegroundColor Cyan
npm run dev
