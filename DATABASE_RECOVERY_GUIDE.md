# NOVA v0.9 — Database Hardening, Backup & Disaster Recovery Guide

## 1. Overview & Architecture

NOVA v0.9 introduces an enterprise-grade SQLite persistence, hardening, and disaster-recovery layer designed to ensure zero data loss, concurrency safety, and full disaster recoverability for local Windows desktop operations.

The persistence architecture consists of:
- **Centralized Connection & Transaction Governor (`app.database.db_manager`)**:
  - Enforces **Write-Ahead Logging (WAL)** mode on all database connections.
  - Configures **5000ms `busy_timeout`** to prevent `SQLITE_BUSY` contention during simultaneous reads and writes.
  - Sets `PRAGMA synchronous = NORMAL` for optimal balance between SSD write speed and durability against application/OS crashes.
  - Enforces `PRAGMA foreign_keys = ON` to guarantee relational integrity across projects, memories, workflows, automations, and personalization graphs.
  - Provides a safe `db_manager.transaction()` context manager with automated rollbacks on any unhandled exception.
- **Online Backup & Disaster Recovery Manager (`app.database.backup_manager`)**:
  - Leverages SQLite's native online backup API (`source_conn.backup(dest_conn, pages=-1)`) to take non-blocking, point-in-time database snapshots without locking out user tasks or chat queries.
  - Generates verifiable SHA-256 cryptographic hashes and companion metadata (`.meta.json`) for every backup.
  - Runs automatic SHA-256 and `PRAGMA integrity_check` verification immediately after backup creation and prior to any restore operation.
  - Implements **two-phase restoration preview** with cryptographic confirmation tokens.
  - Takes a pre-restore safety snapshot before replacing active databases to guarantee that a restore can never destroy an existing database copy.

---

## 2. SQLite Configuration Details

| Parameter | Value | Rationale |
| :--- | :--- | :--- |
| **Journal Mode** | `WAL` | Enables concurrent readers alongside a single active writer without mutual blocking. |
| **Busy Timeout** | `5000 ms` | Prevents immediate failure during high-concurrency bursts (e.g. background automation + user voice interaction). |
| **Synchronous** | `NORMAL` | Standard WAL mode setting. Fsyncs WAL header during checkpoints; safe from corruptions during application crashes. |
| **Foreign Keys** | `ON` | Enforces relational integrity across memories, workflows, automations, and knowledge graph edges. |
| **Cache Size** | `-8000` (8 MB) | Memory-efficient in-RAM cache tuned for Intel Core i3 (12 GB RAM) hardware. |

---

## 3. Backup Management

### 3.1 Backup Triggers
1. **Automated Baseline Backup**: Initiated on first startup if no backups have occurred in the last 24 hours.
2. **Pre-Migration Backup**: Initiated before applying database migrations or schema updates.
3. **Scheduled Automated Backup**: Configurable routine backups (default retention: 10 snapshots).
4. **Manual On-Demand Backup**: Triggered via HUD UI or REST API (`POST /api/system/database/backups`).

### 3.2 Backup Storage & Layout
Backups are stored in `D:\Nova\backups` (configurable via `NOVA_BACKUP_DIR` in `.env`).

Each backup comprises two files:
- `backup_<YYYYMMDD_HHMMSS>_<uuid>.db`: The complete, raw SQLite database snapshot.
- `backup_<YYYYMMDD_HHMMSS>_<uuid>.meta.json`: Diagnostic metadata:
  ```json
  {
    "backup_id": "backup_20261021_164440_2cd3d0",
    "filename": "backup_20261021_164440_2cd3d0.db",
    "path": "D:\\Nova\\backups\\backup_20261021_164440_2cd3d0.db",
    "trigger": "manual",
    "description": "Pre-maintenance snapshot",
    "created_at": "2026-10-21T16:44:40.973829",
    "size_bytes": 237568,
    "sha256": "7b915f4a48b299745b9e00964ccff969579dfe995e2f97f19cf065d4d4a2dbfc",
    "app_version": "0.9.0",
    "tables_count": 23,
    "total_records": 11,
    "table_counts": {
      "messages": 2,
      "memories": 3,
      "projects": 1,
      "agent_workflows": 1
    },
    "healthy": true
  }
  ```

---

## 4. Disaster Recovery & Restoration Procedures

### 4.1 Safety Architecture
Restoring a database replaces the user's active persistent memory. To eliminate risk:
1. **Integrity Pre-Check**: The backup file is checked for SHA-256 checksum match and SQLite integrity.
2. **Dry-Run Preview**: A preview is generated comparing current active database records against backup records.
3. **Explicit Confirmation**: The user must acknowledge the action and submit a single-use confirmation token.
4. **Pre-Restoration Safety Snapshot**: Prior to touching active files, NOVA takes a temporary snapshot of the active database (`D:\Nova\backups\pre_restore_safety_<timestamp>.db`).
5. **Atomic File Swap**: The restored database is validated in a staging file before being atomically replaced via `os.replace()`, ensuring an interrupted restore leaves the system intact.

### 4.2 Step-by-Step Restoration via UI
1. Open NOVA Desktop and navigate to the **System Reliability** panel (`ShieldCheck` icon in sidebar).
2. Click the **Database & Backups** tab.
3. In the **Available Database Backups** list, locate the target snapshot.
4. Click **Validate** to ensure the backup's SHA-256 and internal pages are 100% healthy.
5. Click **Preview Restore**. A modal will display:
   - Target database path.
   - Current record counts vs. backup record counts.
   - Warning notification regarding unsaved active sessions.
6. Check **"I authorize replacing active database"** and click **Execute Restoration**.
7. The system applies the restoration, restarts connections in WAL mode, and refreshes the health telemetry.

### 4.3 Step-by-Step Restoration via REST API
```bash
# 1. List available backups
curl -X GET "http://localhost:8000/api/system/database/backups"

# 2. Validate backup integrity
curl -X POST "http://localhost:8000/api/system/database/backups/validate" \
     -H "Content-Type: application/json" \
     -d '{"backup_id": "backup_20261021_164440_2cd3d0"}'

# 3. Request restore preview & obtain single-use confirmation token
curl -X POST "http://localhost:8000/api/system/database/restore/preview" \
     -H "Content-Type: application/json" \
     -d '{"backup_id": "backup_20261021_164440_2cd3d0"}'

# 4. Execute restoration with explicit confirmation
curl -X POST "http://localhost:8000/api/system/database/restore/execute" \
     -H "Content-Type: application/json" \
     -d '{
       "backup_id": "backup_20261021_164440_2cd3d0",
       "confirmed": true
     }'
```

### 4.4 Manual Offline Recovery (Cold Recovery)
If the backend cannot boot due to severe filesystem corruption:
1. Terminate all NOVA backend and frontend processes.
2. Navigate to `D:\Nova`.
3. Locate `nova_memory.db`, `nova_memory.db-wal`, and `nova_memory.db-shm`.
4. Move them to a rescue folder: `D:\Nova\corrupt_rescue\`.
5. Open `D:\Nova\backups` and select the most recent valid backup (e.g. `backup_20261021_164440_2cd3d0.db`).
6. Copy the chosen backup file to `D:\Nova\nova_memory.db`.
7. Launch NOVA backend (`python -m uvicorn app.main:app`). The supervisor will detect the restored database, enforce WAL mode, and resume operation.

---

## 5. API Reference Summary

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/system/database/status` | `GET` | Health, size, WAL size, and per-table record counts |
| `/api/system/database/backups` | `GET` | List all available backups and metadata |
| `/api/system/database/backups` | `POST` | Trigger online non-blocking backup |
| `/api/system/database/backups/validate` | `POST` | Verify SHA-256 checksum and page integrity |
| `/api/system/database/restore/preview` | `POST` | Dry-run preview and diff analysis |
| `/api/system/database/restore/execute` | `POST` | Execute atomic restore with safety rollback snapshot |
