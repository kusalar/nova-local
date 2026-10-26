# NOVA v1.0 — Windows Installation & Setup Guide

## 1. System Requirements

NOVA (Neural Operational Virtual Assistant) v1.0 is designed to operate 100% locally on standard consumer PC hardware without external cloud APIs.

### Minimum & Target Specifications
- **Operating System**: Windows 10 (21H2+) or Windows 11 (64-bit).
- **Processor**: Intel Core i3-1115G4 (2 physical cores / 4 threads @ 3.00 GHz) or AMD Ryzen 3 4300U equivalent.
- **Memory (RAM)**: 12 GB RAM minimum recommended (8 GB absolute minimum in text-only mode).
- **Storage**: 10 GB available SSD space (for OS runtime, Ollama model weights, embeddings, and voice caches).
- **Audio**: Standard Windows-compatible microphone and audio output (speakers or headphones). Optional for text-only mode.

---

## 2. Prerequisites

Before installing NOVA, ensure the following tools are installed on your Windows PC:

1. **Python 3.10 or 3.11 (64-bit)**
   - Download from [python.org](https://www.python.org/downloads/).
   - **Crucial**: Check the box **"Add Python to PATH"** during installation.
2. **Node.js 18 or 20 LTS**
   - Download from [nodejs.org](https://nodejs.org/).
   - Includes `npm` package manager.
3. **Ollama for Windows**
   - Download from [ollama.com/download](https://ollama.com/download).
   - Install and launch Ollama. It will run in the Windows notification tray on `http://localhost:11434`.

---

## 3. Automated One-Click Installation

The automated setup script installs backend dependencies, builds the frontend desktop bundle, creates safety backups of any existing database, and registers Windows Desktop and Start Menu shortcuts.

### Option A: Double-Click Installer
1. Navigate to the `D:\Nova\scripts\` folder in Windows Explorer.
2. Double-click **`setup_windows.bat`**.
3. A terminal window will open and perform all 6 installation steps automatically:
   - Verifying Python, Node.js, and Ollama.
   - Creating safety backups if upgrading from a previous milestone.
   - Installing Python dependencies (`pip install -r backend/requirements.txt`).
   - Compiling the production desktop interface with Vite.
   - Creating **NOVA.lnk** shortcuts on your Desktop and in your Start Menu.

### Option B: PowerShell Installation
Open PowerShell in the `D:\Nova` directory and run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\scripts\setup_windows.ps1
```

---

## 4. Local Model Setup (Offline Neural Engine)

NOVA performs all reasoning locally using Ollama. Pull your desired models offline:

### Recommended Model (12 GB RAM)
```bash
ollama run qwen2.5:3b
```
- **Size**: ~1.9 GB on disk.
- **Context Window**: 32k tokens.
- **Performance**: High reasoning capability with sub-second response times on Intel Core i3.

### Ultra-Lightweight Alternative (8 GB RAM)
```bash
ollama run qwen2.5:1.5b
```
- **Size**: ~980 MB on disk.
- **Performance**: Fast, responsive, minimal memory footprint.

---

## 5. Offline Voice Assets (STT / TTS)

NOVA includes pre-configured offline voice models:
- **Wake Word Detection**: Built-in openWakeWord detects `"Hey Jarvis"` with low CPU overhead.
  - Optional: Custom `"Hey NOVA"` model can be placed at `models/wake_words/hey_nova.onnx`.
- **Speech Recognition (STT)**: Vosk Kaldi offline language model located in `models/vosk-model-small-en-us-0.15/`.
- **Speech Synthesis (TTS)**: Piper Neural TTS ONNX model located in `models/piper/en_US-lessac-medium.onnx`.

*Note: If you do not have a microphone or prefer silent operation, you can choose **"Text-Only Mode"** in the first-run wizard or in Settings.*

---

## 6. Launching NOVA

You can launch NOVA using any of the following methods:
1. **Desktop Shortcut**: Double-click the **NOVA** icon on your Windows Desktop.
2. **Start Menu**: Open the Windows Start Menu, type `NOVA`, and press Enter.
3. **Command Line**: Double-click `D:\Nova\scripts\start_production.bat`.

### Single-Instance Protection
NOVA enforces single-instance protection. If NOVA is already active, launching it again will focus your existing session at `http://localhost:1420` rather than creating duplicate processes or database locks.

---

## 7. First-Run Setup Wizard

On your first launch, NOVA will automatically present the **First-Run Setup Wizard**:
1. **Compatibility Check**: Audits CPU cores, RAM, and database status.
2. **Model Selection**: Detects locally installed Ollama models and lets you choose your default.
3. **Voice Configuration**: Tests microphone and speaker devices. Provides an explicit toggle for Text-Only Mode.
4. **Privacy & Security**: Explains confirmation gates for file/application operations and screen masking.
5. **Readiness Summary**: Final verification before entering the Command Center.

You can re-launch this wizard at any time via **Settings -> Import/Export -> Launch Setup Wizard**.

---

## 8. Stopping & Uninstalling NOVA

### Stopping the Application
To stop NOVA cleanly and prevent orphaned background listeners:
- Press **Ctrl+C** in the launcher console window, OR
- Double-click `D:\Nova\scripts\stop_all.bat`.

### Uninstallation
To remove shortcuts and clean up NOVA without losing your memories:
1. Open PowerShell in `D:\Nova`.
2. Run `.\scripts\uninstall.ps1`.
3. The uninstaller will ask:
   ```
   Do you want to KEEP your conversational memories, preferences, and backups? (Y/N) [Default: Y]
   ```
   - Pressing **Y** preserves your `nova_memory.db` and `backups/` directory so you can upgrade or reinstall later without data loss.
   - Typing **DELETE** permanently erases user data if you want a complete wipe.
