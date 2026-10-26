# NOVA v0.7 — Automation Security & Autonomy Boundaries

## 1. Security Philosophy
Autonomous routines must operate strictly within bounded permissions. Automations are NEVER permitted to escalate their own privileges, execute arbitrary shell code, access credentials, bypass human confirmation gates, or silently mutate workspace files.

---

## 2. Autonomy Levels

| Level | Allowed Capabilities | Prohibited Capabilities |
|---|---|---|
| **OBSERVE** | Read permitted project info, query SQLite memory, read telemetry, generate reports, OCR screen read. | Workflow planning, tool execution, file modification. |
| **PREPARE** | Formulate workflow plans, prepare proposed desktop operations, draft summaries, generate recommendations. | Direct tool execution without explicit confirmation. |
| **EXECUTE_LOW_RISK** | Run approved read-only checks, open permitted apps, deliver in-app notifications, trigger safe test runners. | Mutating filesystem, deleting files, running arbitrary scripts. |
| **REQUIRES_APPROVAL** | Modify files, move/rename files, execute confirmation-required tools, alter sensitive preferences. | Must pause for explicit human confirmation; cannot proceed autonomously. |
| **BLOCKED** | *None* | Arbitrary shell (`cmd.exe`, `powershell.exe`), credential reading, privilege escalation, disabling security. |

---

## 3. Strict Safety Boundaries

### 3.1 Self-Escalation Prevention
- Automation rules are immutable during execution. A rule declared as `OBSERVE` or `EXECUTE_LOW_RISK` cannot invoke an action requiring `REQUIRES_APPROVAL`.
- If an agent workflow planned by an automation includes a confirmation-required step, execution halts with status `REQUIRES_APPROVAL` and dispatches a notification to the user.

### 3.2 Single-Use, Non-Reusable Approvals
- Approvals are cryptographically tied to exact action payloads and automation IDs.
- Approvals automatically expire after 300 seconds (5 minutes).
- Scheduled automations are prohibited from reusing stale approval tokens from past executions.

### 3.3 Test Runner Command Sanitization
- Project health checks execute test suites via narrowly scoped prefixes (`pytest`, `python -m unittest`, `npm test`).
- Shell metacharacters (`&&`, `;`, `\|`, `>`, `<`, `$`, `rm`, `del`, `curl`) are rejected outright with immediate critical termination.

### 3.4 Spoken Privacy & Sensitivity Gates
- Spoken notifications via Piper TTS are suppressed if the notification content is flagged as sensitive unless the user explicitly enables `speak_sensitive_content` in preferences.
- Zero secret keylogging, zero clipboard scraping, and zero covert screen recording.

### 3.5 Global Automation Kill Switch
- The user can pause all background automations and trigger evaluations at any moment via REST (`/api/automation/pause-all`), UI button, or voice command:
  *"Hey NOVA, pause all automations."*
- When globally paused, the scheduler and trigger engines skip all execution requests until explicitly resumed by the user.
