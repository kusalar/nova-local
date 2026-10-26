# NOVA v1.0 Production Launcher
# Single-instance enforcement, graceful shutdown trap, and clean process management

$ErrorActionPreference = "Stop"

$NovaRoot = Split-Path -Parent $PSScriptRoot
Set-Location $NovaRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "     NOVA v1.0 — Production Desktop Assistant" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Single Instance Check
$active8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($active8000) {
    Write-Host "[NOTICE] NOVA backend is already active on port 8000." -ForegroundColor Yellow
    Write-Host "Opening NOVA Command Center..." -ForegroundColor Green
    Start-Process "http://localhost:1420"
    exit 0
}

# 2. Check Ollama
$ollamaActive = Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue
if (-not $ollamaActive) {
    Write-Host "[INFO] Starting local Ollama engine..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
} else {
    Write-Host "[OK] Ollama neural engine online on port 11434." -ForegroundColor Green
}

# 3. Start Backend
Write-Host "[INFO] Starting NOVA AI Backend (FastAPI / Uvicorn)..." -ForegroundColor Cyan
$backendDir = Join-Path $NovaRoot "backend"
$backendProc = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden

# 4. Wait for Backend Readiness
$backendReady = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/system/status" -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($res -and $res.status) {
            $backendReady = $true
            break
        }
    } catch {}
    Start-Sleep -Milliseconds 600
}

if ($backendReady) {
    Write-Host "[OK] Backend ready on http://127.0.0.1:8000" -ForegroundColor Green
} else {
    Write-Host "[WARN] Backend taking longer than expected. Continuing..." -ForegroundColor Yellow
}

# 5. Start Frontend
Write-Host "[INFO] Starting Desktop Interface..." -ForegroundColor Cyan
$desktopDir = Join-Path $NovaRoot "apps\desktop"
$frontendProc = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $desktopDir -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 2
Start-Process "http://localhost:1420"

Write-Host ""
Write-Host "NOVA v1.0 is running." -ForegroundColor Green
Write-Host "Press Ctrl+C in this window or close it to stop NOVA." -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan

# 6. Lifecycle Management & Process Cleanup
try {
    while ($true) {
        Start-Sleep -Seconds 2
        if ($backendProc.HasExited) {
            Write-Host "[NOTICE] Backend process stopped." -ForegroundColor Red
            break
        }
    }
} finally {
    Write-Host "`nStopping NOVA processes..." -ForegroundColor Yellow
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    }
    # Clean any lingering listener
    Get-NetTCPConnection -LocalPort 8000, 1420 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        try { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } catch {}
    }
    Write-Host "[OK] All NOVA processes cleanly terminated." -ForegroundColor Green
}
