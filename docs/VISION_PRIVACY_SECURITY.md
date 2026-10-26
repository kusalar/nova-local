# NOVA v0.5 — Vision Intelligence Privacy & Security Specification

## 1. Security Tenets

The Multimodal Visual Intelligence subsystem in NOVA v0.5 adheres to strict offline, privacy-first engineering standards:

1. **Zero Cloud Egress**: All screen captures, window enumeration, and OCR extraction are executed 100% locally on the host machine. No image bytes or extracted text are ever transmitted to external or cloud endpoints.
2. **Explicit User Intent Only**: Screen capture is strictly triggered upon explicit user command (e.g. "Hey NOVA, look at my screen" or explicit UI button click). Background continuous screen recording is strictly disallowed by architecture.
3. **Ephemeral by Default**: Screenshots are treated as temporary volatile memory. Captured images are purged immediately after question analysis unless the user explicitly alters their retention settings.
4. **Sensitive Window Shielding**: Windows belonging to password managers, credential vaults, authenticators, or Windows User Account Control (UAC) prompts are automatically detected and blocked from optical capture.
5. **Multi-Pattern Credential Redaction**: Extracted OCR text is sanitized through regex filters before being passed to inference models or persistent storage. Passwords, API tokens, bearer headers, and financial credentials are never retained in plain text.
6. **Decoupled from Operations**: Vision intelligence is read-only. It provides descriptive understanding but cannot bypass the permission and confirmation safeguards of the v0.4 Operations Center.

---

## 2. Sensitive Window Protection Matrix

The `WindowManager` and `PrivacyFilter` continuously evaluate foreground and enumerated windows against the following security signatures:

| Application / Process | Executable Signature | Security Classification | Protection Behavior |
|---|---|---|---|
| **1Password** | `1password.exe`, `1password` | Credential Vault | Optical capture blocked; returns security warning |
| **Bitwarden** | `bitwarden.exe`, `bitwarden` | Credential Vault | Optical capture blocked; returns security warning |
| **KeePass / KeePassXC** | `keepass.exe`, `keepassxc.exe` | Key Store | Optical capture blocked; returns security warning |
| **LastPass / Dashlane** | `lastpass.exe`, `dashlane.exe` | Password Manager | Optical capture blocked; returns security warning |
| **Windows UAC / CredentialUI** | `consent.exe`, `credentialui.exe` | OS Privilege Elevation | Optical capture blocked; returns security warning |
| **Authenticator Apps** | `authy.exe`, `authenticator` | 2FA / TOTP Tokens | Optical capture blocked; returns security warning |

If `exclude_sensitive_windows` is enabled in settings (default: `True`), any request to capture an active sensitive window raises a `ScreenCaptureError` and prevents desktop imaging.

---

## 3. Automated Credential & PII Redaction

When local OCR runs across captured desktop imagery, extracted text passes through `PrivacyFilter.redact_text` and `PrivacyFilter.sanitize_ocr_result`:

| Category | Targeted Pattern | Replacement Token |
|---|---|---|
| **OpenAI API Keys** | `\b(sk-[a-zA-Z0-9]{20,48})\b` | `[REDACTED_OPENAI_KEY]` |
| **Google Cloud / Gemini** | `\b(AIza[0-9A-Za-z-_]{20,45})\b` | `[REDACTED_API_KEY]` |
| **GitHub Tokens** | `\b(ghp_[a-zA-Z0-9]{36})\b` | `[REDACTED_GITHUB_TOKEN]` |
| **GitLab Tokens** | `\b(glpat-[a-zA-Z0-9\-_]{20,})\b` | `[REDACTED_GITLAB_TOKEN]` |
| **AWS Access Keys** | `\b(AKIA[0-9A-Z]{16})\b` | `[REDACTED_AWS_KEY]` |
| **Bearer Tokens** | `Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*` | `[REDACTED_AUTH_TOKEN]` |
| **JWT Tokens** | `ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}` | `[REDACTED_JWT_TOKEN]` |
| **Key-Value Passwords** | `(?:password\|secret\|token)\s*[:=]\s*["\']?...["\']?` | `[REDACTED_SECRET]` |
| **Credit Card Numbers** | `\b(?:\d{4}[-\s]?){3}\d{4}\b` | `[REDACTED_CARD_NUMBER]` |
| **Private Keys** | `-----BEGIN (RSA\|EC\|DSA\|OPENSSH\|PGP) PRIVATE KEY-----` | `[REDACTED_PRIVATE_KEY]` |

Both aggregate text (`full_text`) and individual word nodes (`lines[].words[].text`) are redacted, guaranteeing that UI coordinates and structured inspection views never display credentials.

---

## 4. Retention Lifecycle Policies

Users can configure the retention policy through the Vision Center settings:

1. **`EPHEMERAL` (Default)**:
   - Screenshot is saved to a temporary RAM/disk cache strictly for the duration of OCR and prompt construction.
   - Immediately upon completion of the LLM response, the image file is unlinked and deleted.
   - Ephemeral cache size remains 0 between queries.
2. **`SESSION`**:
   - Screenshots are retained in the `temp_captures/` folder during the active desktop session to permit follow-up questions without re-capturing.
   - All files are purged when the user clicks "Clear Captures" or when the desktop backend shuts down.
3. **`PERSISTENT`**:
   - Retained only when explicitly requested by user action.
   - Managed under the user's explicit control.

---

## 5. UI Transparency & User Awareness

- **Visible Vision Indicator**: The top navigation bar displays a persistent `VISION v0.5 ACTIVE` indicator informing the user that visual awareness is enabled.
- **Active Window Status Card**: The Vision Center explicitly indicates whether the currently focused window is classified as `CAPTURE PERMITTED` or `SENSITIVE PRIVACY SHIELD`.
- **Instant Cache Purge Button**: A one-click `Clear Captures` button in the dashboard allows instantaneous deletion of all ephemeral screenshot files with visual confirmation of the count of deleted files.
- **Microphone Protection**: Visual analysis is handled asynchronously and does not lock or block audio capture devices.
