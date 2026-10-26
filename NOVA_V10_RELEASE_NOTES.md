# NOVA v1.0 — Official Windows Desktop Release Notes

**Release Version**: 1.0.0  
**Release Channel**: Stable  
**Platform**: Windows 10 / Windows 11 (64-bit)  
**Date**: October 2026  
**Repository**: `D:\Nova`  

---

## 1. Overview

NOVA (Neural Operational Virtual Assistant) v1.0 is the first stable desktop release of our offline-first personal AI assistant for Windows. Designed to run completely on-device without mandatory cloud services or subscription APIs, NOVA brings together conversational reasoning, offline voice, persistent semantic memory, desktop operations, visual intelligence, multi-agent workflows, proactive automations, and adaptive personalization into a cohesive, dependable Windows desktop experience.

NOVA v1.0 consolidates the foundational work of milestones v0.1 through v0.9 into a polished, production-ready system tailored for daily use on standard consumer hardware.

---

## 2. What's New in v1.0

### Interactive First-Run Setup Wizard
- Introduces an intuitive 5-step HUD onboarding wizard (`OnboardingWizard.tsx`) for new installations.
- Audits system hardware compatibility (logical cores, RAM sufficiency).
- Detects local Ollama installation and presents available models with clear on-disk file size indicators.
- Guides microphone and speaker device configuration with an explicit toggle for **Text-Only Mode**.
- Explains privacy boundaries, screen masking, and single-use approval tokens.
- Re-runnable at any time from the Settings menu.

### Centralized Configuration & Settings
- Comprehensive 5-tab settings modal consolidating controls for:
  - **Voice & Audio**: Sensitivity sliders, device selectors, Piper speaking rate and volume.
  - **AI Neural Engine**: Ollama endpoint, active model selection, inference temperature, and token limits.
  - **Privacy & Security**: Adaptive personalization toggles, screen inspection permissions, and memory retention days.
  - **Persistence**: Real-time SQLite engine status, WAL journal details, and lock timeouts.
  - **Import / Export**: One-click download of sanitized configuration JSON files and instant restoration.

### Streamlined Desktop User Experience
- Redesigned left navigation sidebar with **zero milestone clutter**: removed obsolete `v0.5`, `v0.6`, etc. badges.
- Consolidated navigation to 9 dedicated, fully functional centers:
  1. **Command Center** — Holographic Orb, live activity feed, telemetry, and quick commands.
  2. **Operations & Tools** — 23 verified desktop operations with action previews and approval gates.
  3. **Vision Intelligence** — User-initiated window and display capture with local OCR.
  4. **Agents & Workflows** — DAG multi-agent planning across 5 specialized personas.
  5. **Automations & Routines** — Scheduled routines, interval checks, and event-driven automation.
  6. **Personalization** — Learned preference management, explicit overrides, and privacy clearing.
  7. **Memory & Knowledge** — Project-isolated semantic memory with local BGE vector search.
  8. **System Reliability** — Subsystem health registry, verified database backups, and diagnostics.
  9. **Live Conversations** — Interactive chat console with model selection and message history.

### Windows Packaging & Automated Installation
- Added automated one-click installer scripts (`setup_windows.bat` / `setup_windows.ps1`).
- Preserves existing databases and automatically creates pre-upgrade safety snapshots.
- Creates standard Windows shortcuts on the Desktop and Start Menu.
- Single-instance enforcement prevents duplicate backend processes and database locks.
- Provided clean process cleanup script (`stop_all.bat`) and safe uninstaller (`uninstall.ps1`).

### Comprehensive End-to-End Validation Suite
- Implemented `backend/tests/test_e2e_v10.py` covering 8 complete user journeys:
  - **Scenario A**: Everyday Conversation (Ollama reasoning + Piper TTS).
  - **Scenario B**: Project-Aware Memory & Context Isolation.
  - **Scenario C**: Desktop Operation & Single-Use Approval Tokens.
  - **Scenario D**: Screen Understanding & Credential Redaction.
  - **Scenario E**: Multi-Agent DAG Workflow Lifecycle.
  - **Scenario F**: Proactive Automation & Notification Persistence.
  - **Scenario G**: Personalization (Explicit vs. Inferred Preference Precedence).
  - **Scenario H**: Recovery, Backup Validation, and Settings Round-Trip.
- **100% Pass Rate**: All 8 scenarios passed; complete backend regression suite reports **131 passed tests (0 failures)**.

---

## 3. Integrated Subsystems Summary

| Subsystem | Underlying Technology | Operational Characteristics |
|---|---|---|
| **Conversational Intelligence** | Local Ollama (`qwen2.5:3b`, `qwen2.5:1.5b`) | 100% offline, private prompt processing. |
| **Wake-Word Detection** | openWakeWord (ONNX) | Built-in `"Hey Jarvis"` acoustic model; optional custom `"Hey NOVA"`. |
| **Speech Recognition (STT)** | Vosk (Kaldi C-API) | Offline speech-to-text without cloud streaming. |
| **Speech Synthesis (TTS)** | Piper Neural TTS (ONNX) | Natural-sounding local speech synthesis with instant barge-in support. |
| **Persistent Memory** | SQLite + FastEmbed BGE | Strict project isolation, semantic vector similarity, WAL mode. |
| **Desktop Operations** | 23 Registered Windows Tools | Gated by single-use cryptographic approval tokens. |
| **Visual Intelligence** | Windows OCR + PrivacyFilter | User-initiated, sensitive window blocking, automated credential masking. |
| **Multi-Agent Orchestration** | 5 Specialized Personas | DAG planning, dependency validation, reflection reports. |
| **Proactive Automation** | Custom Scheduler & Event Bus | Scheduled routines, reminders, persistent notifications. |
| **Personalization Engine** | Preference Engine | Explicit preference precedence, local privacy controls. |
| **Reliability & Security** | Subsystem Supervisor & BackupManager | Checksum-verified backups, pre-restore snapshots, dry-run previews. |

---

## 4. Hardware Baseline & Performance

Benchmarked on **Intel Core i3-1115G4 (2 physical cores / 4 threads @ 3.00 GHz), 12 GB RAM, Windows 11**:

- **System Idle CPU**: **3.8% – 6.2%** (down from 14.1%–19.1% baseline in v0.9).
- **Text-Only Idle CPU**: **< 2.0%**.
- **Total Application Memory**: **~1,620 MB** (including embeddings, models, and UI webview).
- **Cold Startup Latency**: **2.6 seconds**.
- **Chat Time to First Token (TTFT)**: **~820 ms** (`qwen2.5:3b`).
- **Database Concurrency**: Zero lock contention across 50 concurrent transactions.

---

## 5. Honest Wake-Word Disclosure

- **Active Built-in Wake Phrase**: `"Hey Jarvis"` (powered by the pre-trained openWakeWord acoustic model).
- **Optional Custom "Hey NOVA"**: Supported if a custom-trained model is placed in `models/wake_words/hey_nova.onnx`.
- NOVA transparently displays `"Hey Jarvis" (Built-in)` across all UI indicators and settings screens to avoid misleading users.

---

## 6. Known Limitations & Recommendations

1. **Integrated GPU Performance**: On dual-core Intel UHD graphics, running larger models (>7B parameters) will cause significant CPU throttling. Models like `qwen2.5:3b` or `qwen2.5:1.5b` are strongly recommended.
2. **First Audio Frame Warmup**: The first voice synthesis request after startup may experience a ~500 ms delay while the Piper ONNX runtime initializes into memory.
3. **Local Loopback Security**: The backend listens strictly on `127.0.0.1:8000`. Other local processes running with current user privileges could potentially interact with localhost.
