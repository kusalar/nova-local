# NOVA v0.8 — Personalization Privacy & Data Governance

## 1. Zero-Cloud Privacy Commitment

NOVA is engineered from the ground up as a fully offline, private AI assistant. Personalization and adaptive intelligence features adhere to strict non-intrusive boundaries:

1. **Local-Only Processing**: All preferences, graph connections, interaction logs, and recommendations reside exclusively in `D:\Nova\nova_memory.db`.
2. **Zero Cloud Telemetry**: No user preferences, prompts, or interaction telemetry are transmitted over the network.
3. **No Hidden Background Surveillance**:
   - No keystroke loggers or background key interceptors.
   - No automatic clipboard sniffing.
   - No collection of credentials, passwords, or personal identifying tokens.
4. **Ephemerality of Screen OCR Context**: OCR text extracted from v0.5 visual intelligence is strictly ephemeral in memory for immediate question answering; raw screen frames are never permanently stored in the knowledge graph or preferences database.
5. **Deterministic Precedence**: Explicit user commands immediately override any learned or inferred preference.

---

## 2. Granular User Controls

The Personalization Settings UI and REST API provide complete user oversight:

| Setting Key | Default | Description |
| :--- | :--- | :--- |
| `enabled` | `true` | Master switch. Disabling immediately halts all adaptive logic, recommendations, and graph reasoning. |
| `adaptive_analysis_enabled` | `true` | Analyzes permitted conversation turns to adapt response style. |
| `recommendations_enabled` | `true` | Evaluates workflow failures, pending tasks, and stale checks. |
| `store_inferred_preferences` | `true` | Persists inferred interaction patterns to SQLite. |
| `active_window_awareness_enabled` | `true` | Uses current foreground window to assist in project resolution. |
| `voice_personalization_enabled` | `true` | Allows voice commands to query and modify preferences. |

---

## 3. Data Sanitization & Wipe Operations

Users have complete data self-determination through the `PersonalizationPrivacy` interface or API:

- **Soft Clear (`include_explicit=false`)**:
  - Deletes all inferred preferences.
  - Clears recommendation history and dismissals.
  - Clears interaction logs and feedback records.
  - **Retains** explicitly saved user preferences.
- **Factory Reset (`include_explicit=true`)**:
  - Wipes all personalization tables completely.
  - Reverts all preferences and graph relationships to initial blank state.
