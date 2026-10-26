# NOVA Architecture — v0.1 Foundation

```
                                  +---------------------------------------+
                                  |     NOVA Windows Desktop App          |
                                  |     (Tauri / React / TypeScript)       |
                                  +---------------------------------------+
                                                      |
                                                      | HTTP / JSON (Port 1420 / 8000)
                                                      v
                                  +---------------------------------------+
                                  |     FastAPI Neural Core Backend       |
                                  |     (Python 3.11 / Uvicorn)           |
                                  +---------------------------------------+
                                        |                   |
                        +---------------+                   +----------------+
                        |                                                    |
                        v                                                    v
     +-----------------------------------+                +-----------------------------------+
     |        Model Manager              |                |       Telemetry & Memory Engine   |
     |  - OllamaProvider (Local Inference|                |  - psutil Real-Time Hardware      |
     |  - Qwen 2.5 1.5B / Llama 3.2 1B   |                |  - SQLite Persistent Storage      |
     |  - Safe offline diagnostics       |                |  - Multi-state Assistant FSM      |
     +-----------------------------------+                +-----------------------------------+
                        |
                        v
     +-----------------------------------+
     |      Local Ollama Daemon          |
     |      http://localhost:11434       |
     +-----------------------------------+
```

## 1. Overview
NOVA (Neural Operational Virtual Assistant) is a desktop AI assistant designed for Windows with a futuristic JARVIS-inspired command center aesthetic.

## 2. Directory Structure
```
NOVA/
├── apps/
│   └── desktop/
│       ├── src/
│       │   ├── components/
│       │   │   ├── dashboard/   # TopNav, NovaOrb, AiCoreOverview, LiveFeed, ActiveAgents, Timeline, QuickCommands, SystemMonitor, MemoryInsights, LlmStatus, BottomBar
│       │   │   ├── chat/        # ChatConsoleModal, history streams, thinking indicators
│       │   │   └── common/      # HudGauge, WaveformVisualizer, GlassCard
│       │   ├── hooks/           # useSystemStats, useAiStatus, useChat
│       │   ├── services/        # api.ts (backend bridge)
│       │   ├── types/           # Complete TypeScript interfaces
│       │   ├── styles/          # index.css with HUD panel borders, scanlines, neon glows
│       │   └── pages/           # CommandCenterPage.tsx
│       ├── src-tauri/           # Tauri Windows configuration (tauri.conf.json, Cargo.toml, main.rs)
│       ├── package.json
│       ├── vite.config.ts
│       └── tailwind.config.js
├── backend/
│   ├── app/
│   │   ├── api/                 # /api/health, /api/chat, /api/system/status, /api/ai/status
│   │   ├── ai/                  # model_provider.py, ollama_provider.py, model_manager.py
│   │   ├── brain/               # state_manager.py (IDLE, LISTENING, THINKING, EXECUTING, SPEAKING, ERROR)
│   │   ├── memory/              # sqlite_memory.py (SQLite persistent message bank)
│   │   ├── tools/               # system_tools.py (psutil non-blocking hardware telemetry)
│   │   ├── config.py            # Pydantic Settings
│   │   └── main.py              # FastAPI entrypoint with CORS
│   ├── tests/                   # Automated pytest suite
│   ├── requirements.txt
│   └── .env.example
├── docs/                        # ARCHITECTURE.md, SETUP.md
├── scripts/                     # start_backend.bat, start_frontend.bat, start_all.bat
└── README.md
```

## 3. Assistant State Machine
NOVA transitions through actual application states:
1. **IDLE**: NOVA is waiting, gentle cyan breathing pulsation and slow rotation.
2. **LISTENING**: Rapid harmonic teal pulse, voice waveform visualizer active.
3. **THINKING**: High-speed particle orbit, purple-cyan energy vortex during model inference.
4. **EXECUTING**: Focused electric-blue laser alignment rings.
5. **SPEAKING**: Rhythmic vocal waves synchronized with browser Web Speech synthesis.
6. **ERROR**: Warning amber/crimson indicator with diagnostic guidance.
