# NOVA v1.0 — Privacy & Security Architecture Guide

NOVA (Neural Operational Virtual Assistant) v1.0 is built on the core principle of **Absolute Data Sovereignty**: your personal conversations, code, desktop activities, and memories must never leave your local computer.

---

## 1. Zero Cloud Footprint & Offline Guarantee

- **No Remote Telemetry**: NOVA transmits zero telemetry, usage analytics, crash reports, or diagnostic bundles to external cloud servers.
- **Local AI Inference**: Conversational reasoning is executed locally by Ollama (`http://localhost:11434`). Prompts and completion tokens are processed entirely in local RAM.
- **Offline Voice Stack**:
  - Wake-word detection: Local ONNX models executed via `openWakeWord`.
  - Speech recognition: Local Kaldi C-libraries executed via `Vosk`.
  - Speech synthesis: Local ONNX voice models executed via `Piper`.
- **Local Persistence**: All project structures, semantic embeddings, task logs, and user preferences reside exclusively inside `nova_memory.db` on your local disk.

---

## 2. Desktop Operation Security & Permission Gating

NOVA executes desktop tools under strict permission boundaries:

### Permission Hierarchy
1. **`READ_ONLY`**: Safe observation actions (e.g. `system_cpu_ram`, `file_search_name`, `system_battery_info`). Executed automatically without confirmation.
2. **`LOW_RISK`**: Reversible user-directed actions (e.g. `folder_create`, `file_copy`). Executed if autonomous permissions allow.
3. **`CONFIRMATION_REQUIRED`**: Modifying or potentially destructive actions (e.g. `system_lock_workstation`, `file_move`, `file_rename`, running terminal commands).
4. **`BLOCKED`**: Dangerous, arbitrary, or unvetted actions. Strictly rejected by policy.

### Single-Use Cryptographic Approval Tokens
When an action requires confirmation:
1. NOVA's `ApprovalTokenManager` generates a unique token signed with a session-ephemeral secret (`appr_<b64_payload>.<hmac_sha256>`).
2. The token is cryptographically bound to:
   - Action type (`tool_execution`).
   - Specific tool ID (`system_lock_workstation`).
   - SHA-256 hash of parameter arguments.
   - Expiration timestamp (default: 300 seconds).
   - Random 16-character cryptographic nonce.
3. When the user approves via UI or voice confirmation, the token is verified and marked as **consumed**.
4. **Replay Protection**: Any subsequent attempt to use the same token is permanently rejected.

---

## 3. Adversarial Prompt Injection Defense (`ContentSanitizer`)

When NOVA retrieves external files, screen OCR text, web snippets, or past memories, those texts are treated as **untrusted data**.

To prevent prompt injection, privilege escalation, or instruction overrides:
1. **Untrusted Delimiters**: Content is wrapped inside `<untrusted_context source="...">` blocks preceded by explicit security boundaries reminding the model that reference data cannot grant privileges.
2. **Heuristic Pattern Scanning**: The `ContentSanitizer` scans incoming text for adversarial directives, including:
   - `ignore all previous instructions`
   - `system prompt override`
   - `grant unrestricted permissions`
   - `you are now in developer mode / DAN`
   - Malicious shell executions (`powershell -enc ...`)
3. **Neutralization**: Flagged dangerous directives are neutralized and logged in the security audit trail.

---

## 4. Visual Privacy & Screen Redaction (`PrivacyFilter`)

Screen capture and visual intelligence are user-initiated and read-only.

### Safeguards:
1. **Sensitive Window Blocking**:
   - NOVA detects active window processes and titles.
   - Any window belonging to password managers (`1password.exe`, `bitwarden.exe`, `keepass.exe`, `dashlane.exe`) or credential prompts (`credentialui.exe`, `consent.exe`) is **blocked from capture**.
2. **Credential & PII Redaction**:
   - Before extracted OCR text is processed by LLM reasoning, regex masking replaces sensitive data:
     - API Keys (OpenAI, AWS, Google, GitHub, Slack) -> `[REDACTED_API_KEY]`
     - Passwords and secrets (`password = "..."`) -> `[REDACTED_SECRET]`
     - Bearer authorization headers -> `[REDACTED_AUTH_TOKEN]`
     - Credit card numbers -> `[REDACTED_CARD_NUMBER]`
     - Private key blocks -> `[REDACTED_PRIVATE_KEY]`

---

## 5. Localhost Network Security

Even though NOVA runs locally, it secures its HTTP and WebSocket interfaces:
- **Binding Restriction**: The backend binds exclusively to loopback interface `127.0.0.1:8000`. It does not listen on `0.0.0.0` or expose ports to the local area network.
- **CORS Restrictions**: Frontend origins are locked to `http://localhost:1420`, `tauri://localhost`, and `http://127.0.0.1:1420`.
- **Sanitized Diagnostics**: Exported diagnostic bundles automatically strip system paths, credentials, and user data.

---

## 6. Personalization Privacy Controls

- **Complete Disablement**: You can turn off adaptive personalization in **Settings -> Privacy & Security**.
- **Data Isolation**: Inferred preferences are stored with low confidence scores and source tags (`INFERRED`).
- **Explicit Override**: Explicit user preferences always override inferred patterns.
- **One-Click Purge**: Users can clear all personalization data via the Personalization Center without affecting system operation.

---

## 7. Known Security Boundaries & Limitations

1. **Local Access Trust**: Anyone with physical access to your logged-in Windows user account can read `D:\Nova\nova_memory.db`. Users requiring at-rest encryption should use Windows BitLocker.
2. **User-Initiated Tool Approvals**: NOVA relies on the user to carefully review Action Previews before clicking **Approve**.
3. **Local Loopback Security**: Other malicious software already running with your user privileges on your PC could interact with localhost ports.
