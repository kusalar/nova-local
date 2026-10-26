# NOVA v0.7 — Automation Architecture

## 1. Overview & Vision
NOVA v0.7 transforms NOVA from an on-demand reactive assistant into a proactive personal intelligence companion. It supports user-configured routines, scheduled workflows, reminders, project health checks, daily briefings, and event-triggered automation without repetitive manual prompts.

Crucially, NOVA v0.7 preserves all v0.1–v0.6 capabilities, adheres strictly to existing v0.4 tool permission boundaries and v0.6 agent orchestrator DAG architectures, and runs completely offline on consumer hardware (Intel Core i3, 12 GB RAM).

---

## 2. System Architecture & Component Interactions

```
                                  +-----------------------------+
                                  |   NOVA Voice & Desktop HUD  |
                                  |  (Tauri, React, Piper STT)  |
                                  +--------------+--------------+
                                                 |
                       REST API (/api/automations, /api/notifications)
                                                 |
                                  +--------------v--------------+
                                  |     AutomationManager       |
                                  +-------+--------------+------+
                                          |              |
                      +-------------------+              +------------------+
                      |                                                     |
         +------------v------------+                           +------------v------------+
         |   AutomationScheduler   |                           |      TriggerEngine      |
         | (Timezone, Missed-Runs) |                           | (Thresholds, App Events)|
         +------------+------------+                           +------------+------------+
                      |                                                     |
                      +-------------------+              +------------------+
                                          |              |
                                  +-------v--------------v------+
                                  |     AutomationExecutor      |
                                  +--------------+--------------+
                                                 |
         +--------------------+------------------+-------------------+--------------------+
         |                    |                                      |                    |
+--------v-------+   +--------v-------+                     +--------v-------+   +--------v-------+
| Daily Briefing |   | Project Health |                     | Smart Reminder |   | Agent Workflow |
|  (Memory/Stats)|   | (Safe Tests)   |                     |  (Snooze/Done) |   | (Orchestrator) |
+----------------+   +----------------+                     +----------------+   +----------------+
```

---

## 3. Core Subsystems

### 3.1 AutomationManager (`backend/app/automation/automation_manager.py`)
Central facade coordinating:
- Routine lifecycle (CRUD, enable, disable, run immediately).
- High-level telemetry status reporting.
- Global pause and resume controls.

### 3.2 AutomationScheduler (`backend/app/automation/automation_scheduler.py`)
- Async low-overhead heartbeat loop (5s interval).
- Computes `next_run_at` for `DAILY`, `WEEKLY`, `RECURRING`, and `ONCE` routines.
- Timezone-aware using standard Python `zoneinfo.ZoneInfo`.
- Startup missed-run recovery preventing duplicate executions.

### 3.3 TriggerEngine (`backend/app/automation/trigger_engine.py`)
- Evaluates non-polling, event-driven conditions:
  - System resource thresholds (CPU%, RAM% via `psutil`).
  - Application launch or exit events.
  - Prior workflow outcomes (e.g. on `COMPLETED` or `FAILED`).
  - Overdue tasks and deadlines.
- Absolute privacy guarantees: no hidden screen capture, no keylogger, no clipboard snooping.

### 3.4 AutomationExecutor (`backend/app/automation/automation_executor.py`)
- Concurrency limiter: max 2 parallel read-only workflows.
- Dispatches specialized handlers:
  - **Daily Briefing**: Verifiable synthesis of memory tasks, deadlines, project updates, and system metrics.
  - **Project Health Monitor**: Inspects workspace `.git`, validates test runners, reports actual exit codes.
  - **Smart Reminders**: Evaluates due dates, notifies user, manages snooze/completion.
  - **Agent Workflows**: Direct invocation of `AgentOrchestrator` without duplicate engines.
- Bounded retries: honors `max_retries` and `stop_on_critical` for validation/security exceptions.

### 3.5 NotificationManager (`backend/app/automation/notification_manager.py`)
- In-app notification queue stored persistently in SQLite.
- Real-time WebSocket broadcasting to Tauri frontend.
- Optional Piper TTS spoken alerts with sensitivity gating.

### 3.6 AutomationLogger (`backend/app/automation/automation_logger.py`)
- Non-destructive SQLite schema migrations for `automations`, `automation_history`, `notifications`, and `reminders`.
- Full execution audit trails.

---

## 4. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/automations` | List all configured automations |
| `POST` | `/api/automations` | Create a new automation rule |
| `GET` | `/api/automations/{id}` | Get automation details |
| `PATCH` | `/api/automations/{id}` | Update automation rule |
| `DELETE` | `/api/automations/{id}` | Delete automation and history |
| `POST` | `/api/automations/{id}/enable` | Enable automation |
| `POST` | `/api/automations/{id}/disable` | Disable automation |
| `POST` | `/api/automations/{id}/run` | Manually run automation immediately |
| `GET` | `/api/automations/{id}/history` | Retrieve execution audit trail |
| `GET` | `/api/automation/status` | Get global automation engine telemetry |
| `POST` | `/api/automation/pause-all` | Globally pause all automation triggers |
| `POST` | `/api/automation/resume-all` | Resume all automations |
| `GET` | `/api/automation/templates` | Fetch pre-configured routine templates |
| `GET` | `/api/notifications` | List in-app notifications |
| `POST` | `/api/notifications/{id}/read` | Mark notification as read |
| `POST` | `/api/notifications/{id}/dismiss` | Dismiss notification |
| `POST` | `/api/notifications/{id}/snooze` | Snooze notification |
| `GET` | `/api/reminders` | List pending smart reminders |
| `POST` | `/api/reminders` | Create smart reminder |
| `POST` | `/api/reminders/{id}/complete` | Mark reminder complete |
| `POST` | `/api/reminders/{id}/snooze` | Snooze reminder |
