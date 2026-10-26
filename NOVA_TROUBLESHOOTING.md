# NOVA v1.0 — Troubleshooting & Diagnostic Guide

This guide provides practical solutions for common operational issues, hardware errors, and recovery procedures in NOVA v1.0.

---

## 1. Quick Diagnostic Checklist

If NOVA behaves unexpectedly, check these three indicators in the Command Center:
1. **Top Nav Backend Indicator**: Green circle = Backend online; Red circle = Backend offline.
2. **AI Core Status**: Displays whether Ollama is connected and which model is active.
3. **Voice Pipeline Widget**: Displays `ONLINE`, `LISTENING`, `SPEAKING`, or `STANDBY`.

---

## 2. Common Issues and Resolutions

### Issue 1: "Backend Disconnected" or Connection Refused on Port 8000
- **Symptom**: The desktop UI shows a red status indicator and fails to load chat or telemetry.
- **Cause**: The Python FastAPI backend is not running or crashed due to port collision.
- **Resolution**:
  1. Open a PowerShell prompt in `D:\Nova\scripts\`.
  2. Run `.\stop_all.bat` to terminate any lingering processes.
  3. Start the application again using `.\start_production.bat`.
  4. Check the backend log output for any missing Python packages.

### Issue 2: Ollama Offline or "Model Not Found"
- **Symptom**: NOVA responds with *"Ollama neural engine is offline"* or fails to generate text.
- **Cause**: The Ollama Windows daemon is stopped or the configured model is not installed.
- **Resolution**:
  1. Verify Ollama is running in your Windows taskbar.
  2. Test in Windows Terminal:
     ```bash
     ollama list
     ```
  3. If Ollama is not running, start it:
     ```bash
     ollama serve
     ```
  4. Pull the default model:
     ```bash
     ollama run qwen2.5:3b
     ```
  5. In NOVA Settings, verify the active model name matches the model listed by `ollama list`.

### Issue 3: Microphone Not Detected or Audio Device Errors
- **Symptom**: Wake word does not respond; logs indicate `PortAudio / WASAPI input error`.
- **Cause**: Windows microphone permissions are disabled or the selected audio device was unplugged.
- **Resolution**:
  1. Open Windows **Settings -> Privacy & Security -> Microphone**. Ensure **"Microphone access"** and **"Let desktop apps access your microphone"** are turned **ON**.
  2. Open NOVA **Settings -> Voice & Audio**.
  3. Change **Microphone Input Device** from your previous device to **"Default System Microphone"** or your specific active USB headset.
  4. Click **Save Config**.

### Issue 4: Wake Word Triggering Too Frequently or Not at All
- **Symptom**: False positives during ambient conversation, or failure to trigger when speaking `"Hey Jarvis"`.
- **Cause**: Wake-word threshold is too sensitive or too strict for ambient room noise.
- **Resolution**:
  1. Open **Settings -> Voice & Audio**.
  2. Adjust the **Sensitivity Threshold**:
     - **Too many false triggers**: Increase threshold to `0.65` – `0.75`.
     - **Hard to trigger**: Lower threshold to `0.35` – `0.45`.
  3. Ensure you speak clearly within 1–2 meters of the microphone.

### Issue 5: Piper Speech Synthesis Audio is Choppy or Silent
- **Symptom**: Speech takes a long time to start or audio stutters.
- **Cause**: CPU saturation during concurrent model inference and TTS synthesis.
- **Resolution**:
  1. In **Settings -> Voice & Audio**, verify **Speaker Output Device** is set to an active output.
  2. Switch to a lighter LLM (e.g. `qwen2.5:1.5b`) to free CPU cores for the Piper ONNX synthesizer.
  3. Set TTS Speech Rate to `1.0x` and verify audio level.

### Issue 6: SQLite "Database is Locked" Error
- **Symptom**: Operations fail with `sqlite3.OperationalError: database is locked`.
- **Cause**: A background task held a write transaction longer than expected.
- **Resolution**:
  - In v1.0, NOVA enforces **WAL (Write-Ahead Logging)** mode and a **5,000 ms busy_timeout**, which automatically queues concurrent writes.
  - If a lock persists:
    1. Stop NOVA using `scripts\stop_all.bat`.
    2. Ensure no zombie python processes exist in Windows Task Manager.
    3. Re-launch NOVA. SQLite will automatically recover the WAL journal cleanly.

### Issue 7: High Idle CPU Usage (> 10%)
- **Symptom**: CPU usage remains elevated even when NOVA is idle.
- **Resolution**:
  1. Open **System Reliability -> Diagnostics**.
  2. If voice monitoring is not required, click **"Focus Mode"** or toggle **"Text-Only Mode"** in Settings.
  3. This completely pauses the microphone audio capture loop, reducing idle CPU to **< 2%**.

---

## 3. Log Locations & Diagnostic Exports

- **Backend Runtime Logs**: Printed to console or logged via standard Python logging.
- **Database Backup Location**: `D:\Nova\backups/`.
- **Sanitized Diagnostic Export**:
  - Go to **System Reliability -> Diagnostics**.
  - Click **Export Diagnostics**.
  - A clean `.json` file containing anonymized subsystem metrics will be saved to your Downloads folder.
