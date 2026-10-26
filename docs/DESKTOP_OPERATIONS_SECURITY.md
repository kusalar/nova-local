# NOVA v0.4 — Desktop Operations Security Architecture

## 1. Security Philosophy & Threat Model

NOVA is an offline-first desktop assistant designed to operate with high autonomy while maintaining zero tolerance for unauthorized resource modification or privilege escalation.

The threat model addresses:
1. **Prompt Injection / Jailbreak**: Malicious or ambiguous LLM output attempting to execute arbitrary code or shell scripts.
2. **Path Traversal / Escape**: Attempts to navigate outside allowed workspace directories using `../` or symlinks.
3. **Accidental Destruction**: Silent file overwriting or unintended permanent file deletion.
4. **Data Exfiltration**: Reading sensitive system files (`.env`, `id_rsa`, `credentials.json`, `SAM`).
5. **Unauthorized System Impact**: Modifying audio, locking workstations, or executing destructive batch commands without user consent.

---

## 2. Permission Classification Model

Every registered tool is bound to a strict, non-bypassable permission level:

| Permission Level | Description | Example Tools | Execution Gate |
|---|---|---|---|
| **`READ_ONLY`** | Harmless interrogation of state, filesystem, or telemetry. | `system_cpu_ram`, `folder_list_contents`, `file_search_name`, `file_get_metadata` | Allowed immediately |
| **`LOW_RISK`** | Launches trusted applications, default browser, or empty folders. | `app_open`, `file_open_default`, `browser_open_url`, `folder_create` | Allowed immediately |
| **`CONFIRMATION_REQUIRED`** | Moves, renames, copies files, alters volume, or locks screen. | `file_move`, `file_rename`, `file_copy`, `system_volume_set`, `system_lock_workstation` | **Paused until explicit user approval** |
| **`BLOCKED`** | Arbitrary shell commands, registry modifications, credential access. | `powershell.exe`, `cmd.exe`, `rmdir /s`, `format`, `eval()`, `exec()` | **Strictly Rejected & Logged** |

---

## 3. Filesystem Sandboxing & Boundary Enforcement

The `PermissionManager` (`backend/app/tools/permission_manager.py`) validates every single path before filesystem access:

### A. Configured Workspace Roots
Operations are restricted to an explicit whitelist of allowed base directories:
- NOVA Repository Root (`D:\Nova`)
- User Home Directory (`C:\Users\<User>`)
- Standard User Libraries: `Desktop`, `Documents`, `Downloads`, `Pictures`, `Music`, `Videos`, `Projects`

### B. Path Traversal & Symlink Guard
- **Traversal Prevention**: Rejects any path string containing `/../`, `\..\`, or leading traversal sequences.
- **Canonical Resolution**: Resolves paths using `Path.resolve()`, evaluating all symbolic links and NTFS junction points to their true target.
- **Boundary Verification**: Checks whether the canonical target starts with at least one whitelisted root (`root in resolved.parents or resolved == root`). If not, a `SecurityViolationError` is raised.

### C. Sensitive File Protection
Direct access to sensitive credentials and system hives is strictly blocked by regex anchors:
- `^\.env`
- `^id_rsa`, `^id_ed25519`
- `^credentials(\..*)?$`
- `^\.aws`, `^\.ssh`
- `^SAM$`, `^SYSTEM$`, `^ntds\.dit$`
- `^web\.config$`
- `^\.git[\\/]config$`
- `^api_keys?(\..*)?$`

---

## 4. Subprocess & Command Execution Safety

- **No Shell Execution**: Subprocesses are spawned using explicit argument lists (`[executable_path, arg1, arg2]`) without `shell=True`.
- **Application Whitelisting**: `app_open` verifies that the target executable exists in verified system locations (Program Files, LocalAppData, system PATH) rather than executing arbitrary strings.
- **Dry-Run Simulation**: Bulk operations (such as folder organization) produce a non-destructive dry-run preview containing file counts, target directories, and reversibility details before asking for confirmation.

---

## 5. Voice & UI Authorization Gates

For any plan containing `CONFIRMATION_REQUIRED` steps:
1. **Frontend**: The `ApprovalModal` automatically intercepts the plan, presents the affected resources, reversibility status, and exact operation count, requiring an explicit button click ("Approve & Execute" or "Reject").
2. **Voice**: NOVA speaks the proposed action via Piper TTS (e.g. *"I have prepared an operation to organize your Downloads folder. This action requires confirmation. Would you like me to proceed?"*) and waits for an explicit approval ("Yes", "Proceed", "Confirm") or rejection ("No", "Cancel"). Silence or timeouts automatically cancel the pending action.

---

## 6. Sensitive Data Redaction in Audit Logs

All arguments and telemetry payloads recorded in `nova_memory.db` pass through recursive redaction:
- Keys matching `token`, `password`, `key`, `secret`, `auth`, or `credential` are masked with `[REDACTED]`.
- Bearer tokens matching `Bearer [A-Za-z0-9_-]+` are automatically sanitized.
