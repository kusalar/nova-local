# NOVA v1.0 — Centralized Configuration Guide

This guide details all configuration options, environment variables, settings schemas, and export/import mechanisms in NOVA v1.0.

---

## 1. Configuration Hierarchy

NOVA resolves configuration in the following order of precedence:
1. **Runtime In-Memory Settings & Dynamic UI Preferences** (configured in the Desktop HUD).
2. **Persistent User Preferences** (stored in SQLite `user_preferences` table).
3. **Environment Variables** (loaded from `.env` or system environment).
4. **Application Defaults** (defined in `backend/app/config.py`).

---

## 2. Environment Variables & Defaults (`backend/app/config.py`)

You can customize NOVA by creating a `.env` file in `D:\Nova\backend\` or setting environment variables:

| Variable | Default Value | Description |
|---|---|---|
| `VERSION` | `1.0.0` | Application release version. |
| `API_HOST` | `127.0.0.1` | Local backend listen IP (strictly localhost). |
| `API_PORT` | `8000` | Backend REST/WebSocket port. |
| `DATABASE_PATH` | `nova_memory.db` | Main SQLite storage database file path. |
| `BACKUP_DIR` | `backups` | Directory for automated and manual database snapshots. |
| `DB_BUSY_TIMEOUT_MS` | `5000` | SQLite lock wait timeout in milliseconds. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint for the local Ollama daemon. |
| `DEFAULT_MODEL` | `qwen2.5:3b` | Default Ollama model for conversational reasoning. |
| `FALLBACK_MODEL` | `qwen2.5:1.5b` | Fallback model if the default model is unavailable. |
| `VOICE_ENABLED` | `True` | Master toggle for the offline voice pipeline. |
| `WAKE_WORD_ENGINE` | `openWakeWord` | Engine for offline wake phrase detection. |
| `WAKE_WORD_MODEL` | `hey_jarvis` | Active wake model (`hey_jarvis` built-in; optional `hey_nova`). |
| `WAKE_WORD_THRESHOLD` | `0.50` | Detection sensitivity (0.1–0.9; higher = fewer false triggers). |
| `VOSK_MODEL_PATH` | `models/vosk-model-small-en-us-0.15` | Offline speech recognition acoustic model path. |
| `PIPER_MODEL_PATH` | `models/piper/en_US-lessac-medium.onnx` | Offline neural TTS model path. |
| `PIPER_CONFIG_PATH` | `models/piper/en_US-lessac-medium.onnx.json` | TTS phoneme mapping configuration file. |
| `TTS_SPEECH_RATE` | `1.05` | Playback speed multiplier (0.75x – 1.5x). |
| `TTS_VOLUME` | `1.0` | Output speech volume multiplier (0.2 – 1.5). |
| `APPROVAL_TOKEN_TTL` | `300` | Lifetime of single-use action approval tokens (seconds). |
| `MAX_CONCURRENT_INFERENCES` | `2` | Bounded concurrent Ollama inference slots to protect CPU. |
| `MAX_CONCURRENT_OCR` | `1` | Maximum simultaneous screen OCR extraction jobs. |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

---

## 3. UI Settings Reference

Accessible via the **Settings (Gear Icon)** in the Command Center top bar.

### Tab 1: Voice & Audio
- **Offline Wake Word Detection**: Toggle on/off. When off, speech input only occurs via manual push-to-talk.
- **Sensitivity Threshold**: Range from 0.10 to 0.90. (Recommended: 0.50 for standard rooms; 0.65 for noisy environments).
- **Microphone Input Device**: Select from physical hardware microphones enumerated via Windows WASAPI/MME.
- **Speaker Output Device**: Select preferred speakers or headphones for Piper vocal playback.
- **Speaking Rate & Volume**: Tune speech pacing and playback gain.

### Tab 2: AI Neural Engine
- **Local Ollama Endpoint**: Default `http://localhost:11434`.
- **Active AI Model**: Switch active LLM on the fly without restarting NOVA.
- **Inference Temperature**: Controls randomness (0.1 = strictly deterministic; 1.0 = highly creative).
- **Max Generation Tokens**: Upper bound for generation output tokens (default: 2,048).

### Tab 3: Privacy & Security
- **Adaptive Personalization**: Toggle whether NOVA observes interaction history to tailor future responses.
- **Screen Capture Permission**: Authorizes on-demand OCR screen reading.
- **Memory Retention (Days)**: Specifies retention period for transient conversation turns (default: 90 days). Permanent project decisions are retained indefinitely.

### Tab 4: Persistence
- Displays database engine details: SQLite 3.x, WAL mode active, 5,000 ms busy timeout.
- Storage path: `D:\Nova\nova_memory.db`.

### Tab 5: Import / Export
- **Export Configuration**: Downloads a sanitized `nova_settings_YYYY-MM-DD.json` containing active parameters and non-secret user preferences.
- **Import Configuration**: Restores settings from a valid JSON file.
- **First-Run Setup Wizard**: Re-launches the interactive onboarding flow at any time.

---

## 4. Configuration Export/Import Schema

Exported JSON files use the standard schema:

```json
{
  "export_type": "nova_configuration",
  "version": "1.0.0",
  "app_version": "1.0.0",
  "exported_at": "2026-10-21T17:30:00.000000",
  "active_model": "qwen2.5:3b",
  "voice_settings": {
    "wake_word_enabled": true,
    "threshold": 0.5,
    "speech_rate": 1.05,
    "tts_volume": 1.0
  },
  "preferences": {
    "response_length": "concise",
    "explanation_depth": "detailed",
    "preferred_programming_language": "TypeScript"
  }
}
```

### Security Filtering During Import
When importing a configuration file, NOVA's security validator automatically drops any keys containing sensitive keywords (`token`, `secret`, `password`, `key`) to prevent configuration injection vulnerabilities.
