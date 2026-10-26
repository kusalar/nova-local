# NOVA v0.7 — Scheduler & Trigger Engine Design

## 1. Overview
The scheduling and trigger subsystems in NOVA v0.7 provide local, dependable routine execution tailored for offline desktop environments. Designed specifically for low-overhead operation on consumer hardware (Intel Core i3, 12 GB RAM), it avoids continuous busy-wait loops, high CPU polling, and duplicate task launches.

---

## 2. Timezone & Schedule Computation

### 2.1 Schedule Types
1. **DAILY**:
   - Computes local wall-clock time in the configured timezone (`Asia/Kolkata`, `UTC`, `America/New_York`, etc.).
   - Converts next target occurrence to a canonical UTC ISO-8601 string (`YYYY-MM-DDTHH:MM:SS+00:00`).
   - If the time has already passed today in the target timezone, advances to the next day.
2. **WEEKLY**:
   - Takes `days_of_week` array (0 = Monday, 5 = Saturday, 6 = Sunday).
   - Iterates through the next 7 days in target local timezone to find the closest matching day.
3. **RECURRING**:
   - Calculates next execution as `now_utc + timedelta(seconds=interval_seconds)`.
4. **ONCE**:
   - Executes at a fixed specific datetime and is deactivated after execution.

### 2.2 Timezone Implementation
Using Python's standard `zoneinfo.ZoneInfo`:
```python
tz = ZoneInfo(sched.timezone or "UTC")
now_local = now_utc.astimezone(tz)
candidate = now_local.replace(hour=hour, minute=minute, second=0)
if candidate <= now_local:
    candidate += timedelta(days=1)
next_run_iso = candidate.astimezone(timezone.utc).isoformat()
```

---

## 3. Missed Schedule Recovery & Duplicate Prevention

### 3.1 Reboot Recovery
When the NOVA backend boots up:
1. `AutomationScheduler.handle_restart_recovery(rules)` queries all active automations from SQLite.
2. If `rule.next_run_at <= now_utc`:
   - Checks `rule.last_run_at`. If executed within the past 10 minutes, execution is skipped to prevent duplicate triggers.
   - If a scheduled window was genuinely missed while the system was offline, NOVA dispatches a catch-up execution.
   - Immediately recalculates `next_run_at` to the future and commits to SQLite.

### 3.2 Duplicate Trigger Prevention
- Before launching an execution task, the scheduler advances `rule.next_run_at` in the database.
- `AutomationExecutor` tracks active tasks in memory (`_active_runs[rule.id]`). If a routine is already executing, subsequent triggers return `status: "SKIPPED"`.

---

## 4. Event-Driven Trigger Engine

### 4.1 Zero-Polling Evaluation
Rather than spinning high-frequency background loops, NOVA evaluates triggers reactively:
- **System Resource Thresholds**: Sampled on non-blocking intervals or when the user queries the assistant.
- **Application Events**: Evaluated on process detection events rather than continuous scanning.
- **Workflow Events**: Emitted directly by `AgentEventBus` upon workflow completion or failure.
- **Task Overdue**: Evaluated during periodic heartbeats or memory queries.

### 4.2 Bounded Retries & Backoff
- Each rule configures a `RetryPolicy` (`max_retries`, `retry_delay_seconds`, `stop_on_critical`).
- Critical exceptions (`ValueError`, `PermissionError`, security blocks) abort immediately without wasting CPU cycles.
