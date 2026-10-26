# NOVA v1.0 Windows Setup & Installation Script
# Automated environment validation, database safety backup, dependency installation & shortcut creation

$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "     NOVA v1.0 — Windows Setup & Installation" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$NovaRoot = Split-Path -Parent $PSScriptRoot
Set-Location $NovaRoot

# 1. Environment Verification
Write-Host "[1/6] Verifying system prerequisites..." -ForegroundColor Yellow

# Check Python
try {
    $pythonVer = & python --version 2>&1
    Write-Host "  -> Python detected: $pythonVer" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python is not installed or not in PATH. Please install Python 3.10+ (64-bit)." -ForegroundColor Red
    exit 1
}

# Check Node.js
try {
    $nodeVer = & node --version 2>&1
    Write-Host "  -> Node.js detected: $nodeVer" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Node.js is not installed or not in PATH. Please install Node.js 18+." -ForegroundColor Red
    exit 1
}

# Check Ollama
try {
    $ollamaVer = & ollama --version 2>&1
    Write-Host "  -> Ollama detected: $ollamaVer" -ForegroundColor Green
} catch {
    Write-Host "  [NOTICE] Ollama command line not detected in PATH. Ensure Ollama is installed from https://ollama.com" -ForegroundColor Yellow
}

# 2. Database Safety & Upgrade Preservation
Write-Host ""
Write-Host "[2/6] Preserving user database and memory integrity..." -ForegroundColor Yellow
$DbPath = Join-Path $NovaRoot "nova_memory.db"
$BackupsDir = Join-Path $NovaRoot "backups"

if (-not (Test-Path $BackupsDir)) {
    New-Item -ItemType Directory -Path $BackupsDir -Force | Out-Null
}

if (Test-Path $DbPath) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $preUpgradeBackup = Join-Path $BackupsDir "pre_upgrade_backup_$timestamp.db"
    Copy-Item -Path $DbPath -Destination $preUpgradeBackup -Force
    Write-Host "  -> Existing user database found." -ForegroundColor Green
    Write-Host "  -> Safety pre-upgrade backup created: $preUpgradeBackup" -ForegroundColor Green
} else {
    Write-Host "  -> Fresh installation detected. Database will be initialized on first launch." -ForegroundColor Cyan
}

# 3. Backend Python Dependencies
Write-Host ""
Write-Host "[3/6] Installing backend Python dependencies..." -ForegroundColor Yellow
$reqFile = Join-Path $NovaRoot "backend\requirements.txt"
if (Test-Path $reqFile) {
    & python -m pip install -q -r $reqFile
    Write-Host "  -> Backend dependencies verified." -ForegroundColor Green
}

# 4. Frontend Desktop Application Build
Write-Host ""
Write-Host "[4/6] Building production desktop frontend bundle..." -ForegroundColor Yellow
$desktopDir = Join-Path $NovaRoot "apps\desktop"
Push-Location $desktopDir
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "  -> Installing frontend dependencies..." -ForegroundColor Gray
        & npm install --silent
    }
    Write-Host "  -> Compiling production assets with Vite..." -ForegroundColor Gray
    & npm run build
    Write-Host "  -> Frontend build successful." -ForegroundColor Green
} finally {
    Pop-Location
}

# 5. Windows Desktop & Start Menu Shortcut Creation
Write-Host ""
Write-Host "[5/6] Creating Windows desktop and Start Menu shortcuts..." -ForegroundColor Yellow
$WshShell = New-Object -ComObject WScript.Shell
$TargetLauncher = Join-Path $NovaRoot "scripts\start_production.bat"

# Desktop Shortcut
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$DesktopShortcut = Join-Path $DesktopPath "NOVA.lnk"
$Shortcut = $WshShell.CreateShortcut($DesktopShortcut)
$Shortcut.TargetPath = $TargetLauncher
$Shortcut.WorkingDirectory = $NovaRoot
$Shortcut.Description = "NOVA — Neural Operational Virtual Assistant v1.0"
$Shortcut.Save()
Write-Host "  -> Desktop shortcut created: $DesktopShortcut" -ForegroundColor Green

# Start Menu Shortcut
$StartMenuPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::StartMenu)
$ProgramsPath = Join-Path $StartMenuPath "Programs"
$StartShortcut = Join-Path $ProgramsPath "NOVA.lnk"
$Shortcut2 = $WshShell.CreateShortcut($StartShortcut)
$Shortcut2.TargetPath = $TargetLauncher
$Shortcut2.WorkingDirectory = $NovaRoot
$Shortcut2.Description = "NOVA — Neural Operational Virtual Assistant v1.0"
$Shortcut2.Save()
Write-Host "  -> Start Menu shortcut created: $StartShortcut" -ForegroundColor Green

# 6. Installation Summary
Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "     NOVA v1.0 Installation Successfully Completed!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "You can now launch NOVA from:" -ForegroundColor White
Write-Host "  1. Desktop icon: NOVA" -ForegroundColor Cyan
Write-Host "  2. Start Menu: NOVA" -ForegroundColor Cyan
Write-Host "  3. Running scripts\start_production.bat directly" -ForegroundColor Cyan
Write-Host ""
Write-Host "User data location: $DbPath" -ForegroundColor White
Write-Host "Safety backups:     $BackupsDir" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Green
