# NOVA v0.2 — Offline Voice Intelligence Setup Guide

This guide details the installation, model provisioning, hardware configuration, and troubleshooting procedures for NOVA's 100% offline voice intelligence pipeline.

---

## 1. Architecture Overview

NOVA v0.2 implements a completely local, zero-cloud voice pipeline:

```
[Physical Microphone]
        │
        ▼ (16kHz 16-bit PCM Audio Stream)
[AudioManager] (Single Unified Audio Stream)
        │
        ├──► [openWakeWord] (Offline Wake Word Detection)
        │           │ (Wake Word Triggered: "Hey Jarvis" / "Hey NOVA")
        │           ▼
        └──► [Vosk] (Offline Speech-to-Text)
                    │ (Recognized Query Text)
                    ▼
             [NOVA Brain] (FastAPI + SQLite Memory + Ollama Qwen 2.5)
                    │ (Synthesized AI Response)
                    ▼
             [Piper TTS] (Offline Neural Speech Generation)
                    │ (Direct PCM Audio Streaming)
                    ▼
             [Physical Speaker] (sounddevice playback)
```

---

## 2. Dependencies Installation

All dependencies run locally on Windows without requiring cloud credentials:

```powershell
pip install sounddevice numpy vosk openwakeword piper-tts websockets
```

These are also included in `backend/requirements.txt`:
```powershell
cd backend
pip install -r requirements.txt
```

---

## 3. Speech Recognition Model (Vosk)

NOVA uses the lightweight **`vosk-model-small-en-us-0.15`** model (~40MB), specifically chosen for real-time speech transcription on CPU (Intel Core i3-1115G4).

### Automatic Provisioning
Vosk automatically downloads and caches this model to `C:\Users\<User>\.cache\vosk\vosk-model-small-en-us-0.15` on first run.

### Manual Download (Optional)
If running on an air-gapped machine:
1. Download from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip).
2. Extract to `models/vosk/vosk-model-small-en-us-0.15`.
3. In `backend/.env`, set:
   ```env
   VOSK_MODEL_PATH=models/vosk/vosk-model-small-en-us-0.15
   ```

---

## 4. Wake-Word Model Provisioning (openWakeWord)

openWakeWord uses ONNX models executing via ONNX Runtime on the CPU.

### Available Built-in Models
openWakeWord includes pre-trained models for:
- `hey_jarvis` (Default active model for NOVA JARVIS Command Center)
- `alexa`
- `hey_mycroft`
- `hey_rhasspy`

### Custom "Hey NOVA" Wake Word Model
openWakeWord does not ship with a pre-trained "Hey NOVA" model in its default package distribution. To use "Hey NOVA" specifically:
1. Use openWakeWord's synthetic data generation pipeline to train a custom model:
   ```bash
   git clone https://github.com/dscripka/openWakeWord.git
   cd openWakeWord
   # Follow openWakeWord's synthetic sample generation using Piper or Coqui TTS
   python -m openwakeword.train --target_words "hey nova" --output_dir models/
   ```
2. Export the trained model to ONNX format: `hey_nova.onnx`.
3. Place `hey_nova.onnx` into `models/wake_words/hey_nova.onnx`.
4. NOVA's `WakeWordEngine` will automatically detect `models/wake_words/hey_nova.onnx` on startup and activate "Hey NOVA" as the primary wake phrase.
5. If `hey_nova.onnx` is not present, NOVA gracefully falls back to the verified `hey_jarvis` model and displays an informational note in the settings UI.

---

## 5. Voice Synthesis Model (Piper TTS)

NOVA uses **Piper TTS** with the **`en_US-lessac-low.onnx`** model (~15MB ONNX model), offering natural, robotic-free voice synthesis with sub-100ms inference time on CPU.

### Provisioning
The model files are located in:
- `models/piper/en_US-lessac-low.onnx`
- `models/piper/en_US-lessac-low.onnx.json`

To download manually or switch to a medium quality voice:
```powershell
python -c "
import urllib.request
base = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/'
urllib.request.urlretrieve(base + 'en_US-lessac-low.onnx', 'models/piper/en_US-lessac-low.onnx')
urllib.request.urlretrieve(base + 'en_US-lessac-low.onnx.json', 'models/piper/en_US-lessac-low.onnx.json')
print('Downloaded Piper model.')
"
```

---

## 6. Audio Device Configuration

NOVA automatically detects physical microphones and speakers using `sounddevice`:

1. View connected devices in the UI:
   - Click the **Settings** icon (top right).
   - Select the **VOICE INTELLIGENCE (v0.2)** tab.
2. Select your preferred:
   - **Microphone Input Device**
   - **Speaker Output Device**
3. Configure:
   - **Wake Word Detection Threshold** (Default: 0.50).
   - **TTS Speaking Rate** (Default: 1.05x).
   - **TTS Volume** (Default: 100%).
4. Click **Save Config**.

---

## 7. Operational Workflow

1. Start NOVA with `scripts/start_all.bat`.
2. Say the wake phrase: **"Hey Jarvis"** (or **"Hey NOVA"** if custom model is provisioned), or tap the glowing microphone button in the sidebar or bottom bar.
3. Observe the HUD:
   - The central **NOVA Orb** pulses teal.
   - Status transitions to `LISTENING`.
   - The live audio waveform tracks your voice amplitude.
4. Ask your question:
   > *"What is my CPU usage?"*
5. NOVA detects the end of speech via silence detection, transitions to `THINKING`, queries local Ollama with live telemetry context, and responds verbally through your speakers using Piper TTS while streaming the text response into the chat console!
6. Tap the microphone or orb at any time to interrupt vocal speech.

---

## 8. Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| `Microphone Error` in status | Device index invalid or mic disabled in Windows | Open Windows Sound Settings, verify microphone permissions, and select device in NOVA Settings modal. |
| Wake word doesn't trigger | Ambient noise or microphone gain too low | Lower the threshold in Settings (e.g. to 0.40) or speak closer to the microphone. |
| Speech cut off too quickly | `SPEECH_SILENCE_TIMEOUT` too short | Increase silence timeout in `backend/.env` (e.g. `SPEECH_SILENCE_TIMEOUT=2.0`). |
| TTS audio sounds choppy | CPU overload | Ensure no heavy background processes; `en_US-lessac-low` uses < 15% CPU on dual-core Core i3. |
| Ollama offline error | Ollama daemon stopped | Run `ollama serve` and ensure model is loaded with `ollama run qwen2.5:1.5b`. |
