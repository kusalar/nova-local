# NOVA v1.0 — Upgrade, Backup & Disaster Recovery Guide

This guide describes how to safely upgrade NOVA across versions, perform verified database backups, restore corrupted databases, and execute emergency rollbacks without losing conversational memories or user preferences.

---

## 1. Upgrade Principles & Data Preservation

NOVA follows three immutable rules during all version upgrades:
1. **Zero Silent Resets**: NOVA will never overwrite or erase an existing `nova_memory.db` file without explicit confirmation.
2. **Mandatory Pre-Upgrade Snapshots**: Whenever the installer (`setup_windows.ps1`) runs, it detects existing databases and automatically copies them to `backups/pre_upgrade_backup_<timestamp>.db` before applying any migrations.
3. **Additive Schema Migrations**: All SQLite schema evolutions use `IF NOT EXISTS` or non-destructive column additions.

---

## 2. Upgrading NOVA to a New Version

To upgrade an existing NOVA installation:
1. Stop running NOVA processes:
   ```bash
   scripts\stop_all.bat
   ```
2. Pull the latest repository changes or unpack the new release package into `D:\Nova`.
3. Run the automated installer:
   ```bash
   scripts\setup_windows.bat
   ```
4. The installer performs:
   - Verification of system prerequisites.
   - **Automatic safety backup** of `nova_memory.db` into `D:\Nova\backups/`.
   - Dependency updates via `pip` and `npm`.
   - Production Vite compilation.
   - Non-destructive SQLite schema verification.
5. Launch NOVA via your Desktop shortcut. All previous memories, conversations, and custom settings will be immediately active.

---

## 3. Database Backup Management

NOVA includes an integrated, checksum-verified backup manager (`BackupManager`).

### Manual Backup Creation
- **Via Command Center**: Navigate to **System Reliability -> Backups** and click **Create Backup**.
- **Via REST API**:
  ```bash
  curl -X POST http://127.0.0.1:8000/api/system/database/backups -H "Content-Type: application/json" -d "{\"description\": \"Pre-maintenance backup\"}"
  ```
- Backups are stored in `D:\Nova\backups/` as `backup_YYYYMMDD_HHMMSS_<hash>.db`.
- Each backup generates an accompanying `.json` metadata file recording:
  - Timestamp & application version.
  - SHA-256 cryptographic checksum.
  - Table counts and record counts across all SQLite tables.

### Backup Integrity Validation
Before any restoration is permitted, NOVA verifies:
1. Physical file existence on disk.
2. SHA-256 hash matches the original snapshot.
3. SQLite `PRAGMA integrity_check` returns `ok`.

---

## 4. Transactional Restoration & Rollback

If you ever need to restore your database from a previous backup:

### Step 1: Restoration Preview (Dry-Run)
- Open **System Reliability -> Backups**.
- Click **Restore** next to your desired backup.
- NOVA renders a **Dry-Run Comparison**:
  - Displays record counts in the current database vs. the backup.
  - Verifies file integrity.
  - Generates a single-use confirmation token.

### Step 2: Automatic Pre-Restore Safety Snapshot
- When you click **Authorize Restoration**:
  - NOVA immediately creates a safety snapshot of your *current* database (`pre_restore_backup_<timestamp>.db`).
  - This ensures that even if you accidentally restore the wrong backup, your current state is never lost.

### Step 3: Atomic Replacement & Checkpoint
- The database connection is closed cleanly.
- The validated backup file is copied over `nova_memory.db`.
- WAL mode and busy timeouts are re-established.
- Connections resume immediately without restarting the application.

---

## 5. Emergency Manual Recovery (Corrupted Database)

In the rare event of severe disk corruption or accidental file deletion:

### Scenario A: Reverting to a Previous Backup Manually
1. Terminate all NOVA processes:
   ```bash
   scripts\stop_all.bat
   ```
2. Navigate to `D:\Nova\backups/`.
3. Choose the latest healthy `.db` file (e.g. `pre_upgrade_backup_20261021_170000.db`).
4. Copy it to `D:\Nova\nova_memory.db`, replacing the corrupted file.
5. Delete any leftover `nova_memory.db-wal` or `nova_memory.db-shm` files.
6. Launch NOVA:
   ```bash
   scripts\start_production.bat
   ```

### Scenario B: Recovering Corrupted SQLite Data with SQLite CLI
If SQLite reports corruption on `nova_memory.db`:
```powershell
# In PowerShell:
sqlite3 nova_memory.db ".recover" | sqlite3 recovered_memory.db
Move-Item -Path nova_memory.db -Destination nova_memory_corrupt.db -Force
Move-Item -Path recovered_memory.db -Destination nova_memory.db -Force
```
Then start NOVA to resume normal operations.
