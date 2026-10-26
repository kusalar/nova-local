# NOVA v1.0 — Pre-Release Audit & Final Stabilization Blueprint

**Milestone:** NOVA v1.0 Production Release Candidate  
**Date:** October 2026  
**Repository:** `D:\Nova`  
**Target Environment:** Intel Core i3-1115G4 (2 physical cores / 4 threads @ 3.00 GHz), 12 GB RAM, Integrated Intel UHD Graphics, Windows 11 64-bit  

---

## 1. Executive Summary

Over milestones v0.1 through v0.9, NOVA has evolved into an offline-first, JARVIS-inspired Windows desktop virtual assistant. The core engines—conversational reasoning, offline voice, persistent memory, desktop operations, visual OCR intelligence, multi-agent workflows, proactive automations, personalization engine, and reliability/security infrastructure—are implemented and validated (123 backend regression tests passing, 0 failures).

**v1.0 is strictly a consolidation, packaging, validation, and documentation release.** No new experimental feature expansions are introduced. Instead, this release resolves usability rough edges, streamlines HUD navigation, provides a first-run setup wizard, establishes a practical Windows packaging/installer strategy, consolidates centralized settings, and documents the system for everyday local use.

---

## 2. Repository & Subsystem Pre-Release Findings

### 2.1 Navigation & User Interface Rough Edges
1. **Redundant Sidebar Navigation**:
   - `LeftSidebar.tsx` listed 14 items, including separate entries for `tasks` and `tools-skills` (both rendered `OperationsCenter`), `workflows` and `agents` (both rendered `AgentCommandCenter`), and `calendar` and `knowledge-base` (which lacked dedicated screens and defaulted to the main HUD).
   - Milestone badges (`badge: 'v0.5'`, `'v0.6'`, `'v0.7'`, `'v0.8'`, `'v0.9'`) clutter the production interface and give the application an unfinished prototype appearance.
2. **First-Run Onboarding Gap**:
   - A fresh install currently drops the user directly into the Command Center without guiding them through model verification, voice device selection, text-only mode preferences, or privacy options.
3. **Settings Consolidation**:
   - `SettingsModal.tsx` only configured voice and AI endpoint. It lacked controls for memory retention, automation behavior, screen privacy filters, background resource throttles, and configuration export/import.
4. **Wake-Word Honesty**:
   - UI references to `Hey NOVA` must be clearly qualified: the built-in, verified openWakeWord model is `"Hey Jarvis"`. A custom `hey_nova.onnx` model can be dropped into `models/wake_words/`, but the UI must transparently state whether the built-in fallback is active.

### 2.2 Backend Architecture & API Consistency
1. **Version Alignment**:
   - `backend/app/config.py` is at `0.9.0`. Needs update to `1.0.0`.
   - `apps/desktop/package.json` and `apps/desktop/src-tauri/tauri.conf.json` are at `0.1.0`. Needs update to `1.0.0`.
   - `start_all.bat` still advertises `NOVA v0.1`.
2. **Onboarding Status Endpoint**:
   - Lacks a unified `GET /api/system/onboarding/status` and `POST /api/system/onboarding/complete` API for first-run setup checks.
3. **Centralized Configuration Export/Import**:
   - Lacks structured non-secret export/import endpoints (`GET /api/system/settings/export`, `POST /api/system/settings/import`) for cross-machine preference migration.

### 2.3 Packaging & Deployment Strategy
1. **Tauri Environment**:
   - Tauri configuration exists in `apps/desktop/src-tauri/`.
   - Local system environment lacks Rust `cargo` in PATH, preventing ad-hoc compilation of the Rust Tauri binary on this machine.
2. **Production Runtime Strategy Selection**:
   - **Chosen Strategy**: *Managed Local Python Environment with Production Batch/PowerShell Orchestrator and Pre-Packaged Webview Bundle*.
   - **Rationale**: Building a self-contained PyInstaller binary on Windows for complex C-extensions (`sounddevice`, `numpy`, `onnxruntime`, `vosk`) frequently introduces runtime DLL extraction failures on end-user machines. A managed environment approach with automated setup (`setup_windows.bat`/`setup_windows.ps1`), pre-flight verification, and desktop shortcuts provides 100% reliability, allows effortless upgrades, and guarantees that user databases in `%APPDATA%\NOVA` or `D:\Nova` remain untouched during reinstallations.

---

## 3. Implementation Plan for v1.0 Release Candidate

1. **Version Synchronization**: Bump all configuration files (`config.py`, `package.json`, `tauri.conf.json`) to `1.0.0`.
2. **First-Run Setup Wizard**:
   - Backend: `/api/system/onboarding/status` and `/api/system/onboarding/complete`.
   - Frontend: `apps/desktop/src/components/onboarding/OnboardingWizard.tsx` covering welcome, system check, Ollama check, voice selection, privacy summary, and launch.
3. **Streamlined Production Navigation**:
   - Consolidate `LeftSidebar.tsx` to 9 dedicated screens: Command Center, Vision, Agents, Automations, Personalization, Operations, Memory, System Reliability, and Conversations.
   - Remove obsolete milestone badges; ensure zero broken routes.
4. **Centralized Settings & Configuration Console**:
   - Expand `SettingsModal.tsx` with dedicated tabs: AI Core, Voice & Audio, Memory & Privacy, Automations, and Import/Export Preferences.
5. **Wake-Word Honesty & Voice Polish**:
   - Display active wake-phrase cleanly (`"Hey Jarvis"` built-in; `"Hey NOVA"` custom optional).
6. **Windows Production Deployment Scripts & Shortcuts**:
   - `scripts/setup_windows.ps1` & `scripts/setup_windows.bat`: One-click setup, validation, and shortcut creation.
   - `scripts/start_production.bat`: Single unified production launcher.
   - `scripts/uninstall.ps1`: Safe uninstaller that respects and preserves user databases.
7. **End-to-End Validation Suite (`backend/tests/test_e2e_v10.py`)**:
   - Scenarios A through H covering complete user journeys.
8. **Final Test & Build Verification**:
   - Full pytest execution and production frontend build.
9. **Release Documentation Suite**:
   - All 9 required guides.
