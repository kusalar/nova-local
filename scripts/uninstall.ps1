# NOVA v1.0 Safe Uninstallation Script
# Removes shortcuts, stops processes, and safely prompts before touching user data

Write-Host "========================================================" -ForegroundColor Yellow
Write-Host "     NOVA v1.0 — Uninstallation & Cleanup" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Yellow
Write-Host ""

$NovaRoot = Split-Path -Parent $PSScriptRoot

# 1. Stop any active processes
Write-Host "[1/3] Terminating active NOVA background processes..." -ForegroundColor Cyan
Get-NetTCPConnection -LocalPort 8000, 1420 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
    try { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } catch {}
}

# 2. Remove shortcuts
Write-Host "[2/3] Removing desktop and Start Menu shortcuts..." -ForegroundColor Cyan
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$DesktopShortcut = Join-Path $DesktopPath "NOVA.lnk"
if (Test-Path $DesktopShortcut) {
    Remove-Item -Path $DesktopShortcut -Force
    Write-Host "  -> Removed Desktop shortcut" -ForegroundColor Green
}

$StartMenuPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::StartMenu)
$StartShortcut = Join-Path $StartMenuPath "Programs\NOVA.lnk"
if (Test-Path $StartShortcut) {
    Remove-Item -Path $StartShortcut -Force
    Write-Host "  -> Removed Start Menu shortcut" -ForegroundColor Green
}

# 3. User Data Protection Prompt
Write-Host ""
Write-Host "[3/3] Checking persistent SQLite user data..." -ForegroundColor Cyan
$DbPath = Join-Path $NovaRoot "nova_memory.db"
$BackupsDir = Join-Path $NovaRoot "backups"

if (Test-Path $DbPath) {
    Write-Host "  Persistent database found: $DbPath" -ForegroundColor White
    $keepData = Read-Host "Do you want to KEEP your conversational memories, preferences, and backups? (Y/N) [Default: Y]"
    if ($keepData -eq "" -or $keepData.ToUpper() -eq "Y") {
        Write-Host "  -> User database and backups preserved safely." -ForegroundColor Green
    } else {
        $confirm = Read-Host "Are you SURE you want to permanently delete nova_memory.db and backups? Type 'DELETE' to confirm"
        if ($confirm -eq "DELETE") {
            Remove-Item -Path $DbPath -Force -ErrorAction SilentlyContinue
            Remove-Item -Path $BackupsDir -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  -> User data deleted as confirmed." -ForegroundColor Yellow
        } else {
            Write-Host "  -> Confirmation mismatch. Data preserved." -ForegroundColor Green
        }
    }
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "NOVA v1.0 uninstallation completed." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
