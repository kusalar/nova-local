# NOVA v0.4 — Tool Execution Architecture

## 1. Executive Summary

NOVA (Neural Operational Virtual Assistant) v0.4 introduces **Autonomous Desktop Operations & Safe Tool Execution**. In v0.1 through v0.3, NOVA provided real-time system telemetry, JARVIS-inspired holographic HUDs, offline openWakeWord + Vosk + Piper voice intelligence, and persistent SQLite vector memory.

In v0.4, NOVA advances into an active desktop assistant capable of safely translating natural-language queries and vocal directives into deterministic, permission-governed Windows desktop actions.

---

## 2. Architecture Overview

The tool execution system is located under `backend/app/tools/`:

```
backend/app/tools/
├── __init__.py               # Clean exports of core modules
├── tool_schemas.py           # Pydantic data schemas, enums, TaskPlan, TaskStep
├── tool_registry.py          # Central catalog of 23 verified tools & parameter definitions
├── tool_executor.py          # Safe subprocess & Windows OS operations execution engine
├── permission_manager.py     # Workspace boundaries, path traversal & symlink prevention
├── task_planner.py           # Multi-step intent deconstruction & memory workspace resolution
├── execution_manager.py      # Step sequencer, authorization gates, cancellation, timeouts
├── execution_logger.py       # Non-destructive SQLite persistence & sensitive argument masking
├── rollback_manager.py       # Reversible file operation undo manager
└── system_tools.py           # Non-blocking psutil telemetry engine
```

```mermaid
graph TD
    User([User Voice or Text Command]) --> Brain[Assistant Brain / Audio Manager]
    Brain --> Planner[Task Planner (task_planner.py)]
    Planner --> Memory[(Project Memory v0.3)]
    Planner --> Registry[Tool Registry (23 Tools)]
    Planner --> Plan[Structured TaskPlan (max 8 steps)]
    
    Plan --> ExecMgr[Execution Manager (execution_manager.py)]
    ExecMgr --> PermCheck{Permission Level}
    
    PermCheck -- READ_ONLY / LOW_RISK --> RunStep[Run Tool Step]
    PermCheck -- CONFIRMATION_REQUIRED --> AuthGate{User Approved?}
    AuthGate -- No / Pending --> Modal[Approval Modal (Frontend / Voice)]
    AuthGate -- Yes --> RunStep
    
    RunStep --> Executor[Tool Executor (tool_executor.py)]
    Executor --> Security[Permission Manager Path Guard]
    Security --> WindowsOS[Windows Subprocess / Explorer / File System]
    
    WindowsOS --> Logger[(Execution Logger / SQLite Audit)]
    Logger --> Rollback[Rollback Manager (Undo Ledger)]
```

---

## 3. Registered Tool Catalog

NOVA v0.4 registers 23 verified tools across 4 core operational categories:

### A. Windows Application Control (`APPLICATION`)
1. `app_open`: Safely launch installed Windows applications (`vscode`, `notepad`, `calc`, `wt`, `chrome`, `edge`, `explorer`) with optional path/flag arguments. Never invokes `shell=True`.
2. `app_detect_installed`: Verify application installation by scanning known Program Files, LocalAppData, and system PATH.
3. `file_open_default`: Launch files using Windows file association (`os.startfile`).
4. `folder_open_explorer`: Open specific folders in Windows File Explorer without command strings.

### B. File Intelligence (`FILE_SYSTEM`)
5. `folder_list_contents`: List files, directories, sizes, and timestamps within permitted workspace.
6. `file_search_name`: Find files matching glob/wildcard patterns.
7. `file_search_extension`: Search for files by file extension (e.g. `.py`, `.tsx`, `.pdf`).
8. `folder_create`: Create directory within permitted workspace (Reversible).
9. `file_rename`: Rename files with collision protection and dry-run preview (Reversible).
10. `file_move`: Move files between allowed workspace directories with collision protection (Reversible).
11. `file_copy`: Copy files with duplicate safeguards (Reversible).
12. `file_read_text`: Read UTF-8 text with strict 500 KB safety cap.
13. `file_get_metadata`: Inspect file attributes, read-only status, creation, and modification timestamps.
14. `folder_organize_preview`: Categorize folder contents into Documents, Images, Audio, Video, Archives, Code, and Installers.

### C. System Control (`SYSTEM_CONTROL`)
15. `system_battery_info`: Retrieve battery percentage, status, and power connection via psutil.
16. `system_cpu_ram`: Read live CPU percentage and RAM usage.
17. `system_disk_usage`: Read primary storage capacity and utilization.
18. `system_network_status`: Check internet connectivity, latency, and I/O counters.
19. `system_volume_get`: Query master audio volume.
20. `system_volume_set`: Change master volume percentage (Confirmation Required).
21. `system_lock_workstation`: Lock Windows workstation (`LockWorkStation`, Confirmation Required).

### D. Browser Operations (`BROWSER`)
22. `browser_open_url`: Open validated HTTP/HTTPS URL in the default browser.
23. `browser_search_web`: Perform web queries via privacy-first search providers in default browser.

---

## 4. Multi-Step Task Planning Engine

The `TaskPlanner` translates natural-language directives into structured `TaskPlan` instances:
- **Maximum 8 steps** per task to eliminate unbounded autonomous execution loops.
- **Deterministic Pattern Matching**: Evaluates common voice directives (e.g., "Open VS Code and open my NOVA project", "Organize my Downloads", "Check system status") in sub-millisecond latency without AI inference overhead.
- **Model Fallback**: Uses local Ollama model (`qwen3:4b` / `gemma2:2b`) with JSON schema enforcement when handling unstructured novel requests.
- **Project Memory Integration**: Resolves project references (e.g., "NOVA", "my project") to verified physical filesystem workspaces.
- **Dependency Tracking**: Halts subsequent steps immediately if a critical dependency fails.

---

## 5. Audit Logging & Non-Destructive Rollback

1. **Persistent SQLite Schema**:
   - `operational_tasks`: Stores task metadata, prompts, confirmation state, and completion timestamps.
   - `operational_task_steps`: Stores step statuses (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `SKIPPED`, `CANCELLED`).
   - `tool_executions`: Immutable audit ledger storing execution ID, tool name, redacted arguments, execution duration in milliseconds, result payload, and rollback metadata.
2. **Reversible Undo Ledger**:
   - `file_move`: Restores moved file from destination back to source directory.
   - `file_rename`: Renames file back to previous name.
   - `file_copy`: Removes copied target file.
   - `folder_create`: Deletes created directory if empty.
   - Prevents duplicate rollbacks through `is_rolled_back` database flags.
