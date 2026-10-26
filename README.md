# NOVA — Neural Operational Virtual Assistant
> **JARVIS-Inspired Personal AI Desktop Assistant for Windows — v0.1 Foundation**

![NOVA Status](https://img.shields.io/badge/Status-v0.1_Foundation-00f0ff?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-0077ff?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI_Python_3.11-10b981?style=for-the-badge)
![Frontend](https://img.shields.io/badge/Frontend-React_18_TypeScript_Vite-00ffd5?style=for-the-badge)
![Local AI](https://img.shields.io/badge/Local_AI-Ollama_Qwen2.5-f59e0b?style=for-the-badge)

---

## Visual Design & Command Center HUD

Built from the ground up matching the reference HUD command center design:
- **Central Holographic AI Orb**: Multi-ring 3D wireframe spherical core with orbiting planetary rings, central energy pulsation, and ground holographic grid projection.
- **Dynamic State Engine**: Smooth animations for **IDLE**, **LISTENING**, **THINKING**, **EXECUTING**, **SPEAKING**, and **ERROR**.
- **Real-Time Hardware Telemetry**: Live CPU, RAM, Disk, and Battery gauges via non-blocking `psutil` background stream.
- **Interactive AI Chat Console**: Slide-over HUD modal with SQLite conversation history, thinking indicators, model switcher, and vocal speech synthesis.
- **Provider Status Matrix**: Live status indicator for Ollama (Local), Groq, Claude, OpenAI, and Gemini.
- **Executive Briefing**: Voice-synthesized audio telemetry report inspired by JARVIS.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Desktop Application** | React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, Lucide React, Tauri (`src-tauri`) |
| **Backend API** | Python 3.11, FastAPI, Uvicorn, Pydantic Settings, HTTPX, psutil |
| **Storage & Memory** | SQLite persistent neural memory (`nova_memory.db`) |
| **Local Inference** | Ollama REST Bridge (`http://localhost:11434`), Qwen 2.5 1.5B / Llama 3.2 1B |

---

## Getting Started

### 1. Launch with One Click
```cmd
scripts\start_all.bat
```
Launches the FastAPI backend on `http://127.0.0.1:8000` and the Command Center frontend on `http://localhost:1420`.

### 2. Connect Ollama (Local AI)
```powershell
# 1. Start Ollama
ollama serve

# 2. Pull Qwen 2.5 1.5B (or Llama 3.2 1B)
ollama run qwen2.5:1.5b
```

### 3. Run Automated Tests
```powershell
python -m pytest backend/tests -v
```

---

## Monorepo Architecture

```
NOVA/
├── apps/
│   └── desktop/                 # React + TypeScript + Vite + Tailwind + Tauri
├── backend/                     # FastAPI + psutil + Ollama Bridge + SQLite
├── docs/                        # Architecture & Setup Documentation
├── scripts/                     # Launchers (.bat & .ps1)
└── README.md
```

Detailed technical architecture can be found in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Detailed setup instructions can be found in [docs/SETUP.md](docs/SETUP.md).
