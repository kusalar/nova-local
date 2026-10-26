# NOVA v0.9 — Windows Release Readiness & Application Lifecycle Guide

## 1. Executive Summary

This document evaluates NOVA's operational readiness for desktop release on Windows 11 / Windows 10 (x86_64).

Target desktop hardware profile:
- Processor: Intel Core i3-1115G4 (2 physical cores / 4 threads, base 3.00 GHz, turbo up to 4.10 GHz)
- Memory: 12 GB DDR4
- GPU: Integrated Intel UHD Graphics
- Storage: NVMe SSD
- Operating System: Windows 11 Home / Pro

NOVA v0.9 achieves production-grade stability, resource predictability, and crash resiliency through centralized process supervision, SQLite WAL transactions, and non-blocking asynchronous architectures.

---

## 2. Application Lifecycle Architecture

### 2.1 Startup Sequencing & Readiness
NOVA utilizes a coordinated two-tier startup sequence:
1. **Backend Initialization (`app.main:lifespan` -> `SubsystemSupervisor.on_startup()`)**:
   - **Database Health**: Verifies SQLite page integrity (`PRAGMA integrity_check`).
   - **Baseline Backup**: Takes baseline database backup if no snapshot exists in the past 24 hours.
   - **Stale State Reconciliation**: Detects workflows or background tasks left in `RUNNING` state due to an unexpected previous shutdown and marks them `CANCELLED` with clean audit explanations.
   - **Approval Invalidation**: Explicitly clears any lingering voice or tool approval tokens. Pending approvals cannot persist across reboots.
   - **Ollama Connectivity Probe**: Checks `http://localhost:11434/api/tags`. If Ollama is offline or unresponsive, marks the AI subsystem `DEGRADED` rather than blocking startup.
   - **Audio Device Enumeration**: Probes default microphone and output speaker via `sounddevice`. If devices are absent (e.g. headless or disconnected), smoothly disables wake-word listening without raising unhandled exceptions.
2. **Frontend Connection & Health Hook (`useSystemStats`)**:
   - Polls `/api/system/status` every 3000ms.
   - Automatically renders connection warning banners and degraded indicator badges in the HUD top bar if the backend is temporarily unreachable.
   - Re-establishes WebSocket live feeds and synchronization upon backend reconnection.

### 2.2 Instance Exclusivity & Port Conflict Detection
- **Default Ports**:
  - Backend API: `8000` (FastAPI / Uvicorn)
  - Frontend Webview: `1420` (Vite dev) / Tauri internal IPC
  - AI Inference: `11434` (Ollama daemon)
- **Port Collision Prevention**:
  - If port `8000` is already in use by another application or previous NOVA process, startup diagnostics emit a human-readable error: `[FATAL] Port 8000 is occupied. Verify whether another NOVA instance is already running.`

### 2.3 Graceful Shutdown Sequence (`SubsystemSupervisor.on_shutdown()`)
When the user closes the application or sends a SIGINT/SIGTERM:
1. **Drain Background Operations**:
   - Cancels all registered asyncio tasks with a 5-second graceful drain timeout.
2. **Halt Audio Streams**:
   - Closes `sounddevice.InputStream` and terminates the wake-word detection loop.
   - Stops active Piper TTS playback threads immediately.
3. **Flush SQLite WAL Logs**:
   - Runs `PRAGMA wal_checkpoint(TRUNCATE)` to flush uncommitted WAL pages back into the main database file.
   - Closes open database connections cleanly.
4. **Child Process Cleanup**:
   - Terminates spawned worker subprocesses and cleans temporary OCR scratch bitmaps.

---

## 3. Resilience Against Edge Cases

| Failure Scenario | Previous Behavior | v0.9 Hardened Behavior |
| :--- | :--- | :--- |
| **Ollama Stopped Mid-Chat** | UI frozen indefinitely | Request times out safely (60s), sets subsystem to `DEGRADED`, returns structured fallback message |
| **Unplugged Microphone** | Crashing unhandled exception in audio thread | `AudioManager` catches `PortAudioError`, enters muted fallback mode, reports `VOICE: UNAVAILABLE` in UI |
| **Simultaneous DB Writes** | `sqlite3.OperationalError: database is locked` | SQLite WAL mode + `busy_timeout = 5000ms` handles concurrent transactions without error |
| **Power Loss / Crash Mid-Workflow** | Ghost workflows marked `RUNNING` forever | `SubsystemSupervisor` reconciles stale tasks on next boot to `CANCELLED` and clears approvals |
| **Adversarial Screen Text (Prompt Injection)** | Model hijacked by on-screen text | `ContentSanitizer` defangs directives and encapsulates OCR in `<untrusted_context>` |

---

## 4. Packaging & Distribution Plan

### 4.1 Architecture Strategy
NOVA is designed to package into a single Windows installer (`.msi` or NSIS `.exe`) using **Tauri**:
- **Native Host**: Rust / WebView2
- **Embedded Backend**: PyInstaller-compiled or embedded Python runtime bundle (`backend_dist/`)
- **Frontend Assets**: Pre-compiled Vite static bundle (`apps/desktop/dist/`)
- **Local AI Provider**: Prerequisites installer for Ollama with pre-pulled model (`qwen2.5:3b`)

### 4.2 Windows Release Pre-Flight Checklist
- [x] All v0.1 through v0.9 regression tests passing.
- [x] Frontend compiles cleanly via `npm run build` (`tsc && vite build`).
- [x] SQLite database WAL mode and automated backup system active.
- [x] Cryptographic single-use approval tokens implemented.
- [x] CORS locked to internal desktop origins.
- [x] Secrets and paths redacted from diagnostic exports.
- [x] System Reliability Center UI integrated into HUD sidebar.
- [x] Offline audio synthesis and recognition validated without internet access.
