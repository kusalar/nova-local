# NOVA v0.9 — Software Supply Chain & Dependency Audit

## 1. Overview & Scope

A complete supply chain and dependency security review was performed for NOVA v0.9, covering:
- **Backend**: Python 3.11 runtime, FastAPI, Uvicorn, Pydantic, FastEmbed, SQLite, OpenWakeWord, Vosk, Piper TTS, and Psutil.
- **Frontend**: React 18, TypeScript 5.7, Vite 5.4, Tailwind CSS 3.4, Framer Motion 11.18, and Tauri 1.6.

Target execution environment:
- Windows 11 64-bit (x86_64)
- Python 3.11.9
- Node.js runtime for desktop frontend build

---

## 2. Python Backend Dependency Review

| Package | Constrained Version | License | Security & Compatibility Assessment | Status |
| :--- | :--- | :--- | :--- | :--- |
| `fastapi` | `>=0.110.0` | MIT | Core async REST framework. Clean, no active CVEs. | **PASSED** |
| `uvicorn[standard]` | `>=0.28.0` | BSD-3-Clause | ASGI server. Stable worker lifecycle on Windows. | **PASSED** |
| `pydantic` | `>=2.6.0` | MIT | Strict schema parsing and data validation. | **PASSED** |
| `pydantic-settings`| `>=2.2.0` | MIT | Type-safe `.env` environment loading. | **PASSED** |
| `httpx` | `>=0.27.0` | BSD-3-Clause | Non-blocking async HTTP client for Ollama queries. | **PASSED** |
| `psutil` | `>=5.9.8` | BSD-3-Clause | C-extension Windows telemetry (CPU/RAM/battery/disk). | **PASSED** |
| `sounddevice` | `>=0.5.0` | MIT | PortAudio bindings for microphone and speaker streams. | **PASSED** |
| `numpy` | `>=1.26.0` | BSD-3-Clause | Audio waveform math and fast buffer transforms. | **PASSED** |
| `vosk` | `>=0.3.45` | Apache 2.0 | Offline small-vocabulary STT. Local Kaldi engine. | **PASSED** |
| `openwakeword` | `>=0.6.0` | Apache 2.0 | Offline ONNX wake word detection (`Hey Jarvis`). | **PASSED** |
| `piper-tts` | `>=1.8.0` | MIT | Local neural speech synthesis (Piper voice binaries). | **PASSED** |
| `websockets` | `>=13.0` | BSD-3-Clause | Real-time event streaming for UI live feeds. | **PASSED** |
| `fastembed` | `>=0.4.0` | Apache 2.0 | ONNX-optimized `bge-small-en-v1.5` semantic retrieval. | **PASSED** |
| `scikit-learn` | `>=1.4.0` | BSD-3-Clause | Vector similarity search and fallback clustering. | **PASSED** |

### Python Environment Verification
- Python version: `Python 3.11.9 (tags/v3.11.9:de5405b, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]`
- All packages resolve cleanly without binary collision or DLL loader issues on Windows 11.

---

## 3. Desktop Frontend Dependency Review

| Package | Installed Version | Role | Security & Compatibility Assessment | Status |
| :--- | :--- | :--- | :--- | :--- |
| `react` / `react-dom`| `18.3.1` | UI Library | Industry standard. Clean production build. | **PASSED** |
| `vite` | `5.4.14` | Bundler | Fast ESM bundling and Rollup production output. | **PASSED** |
| `typescript` | `5.7.3` | Type System | Strict static typechecking passed with 0 errors. | **PASSED** |
| `tailwindcss` | `3.4.17` | Utility CSS | Minimal generated CSS footprint (61 kB). | **PASSED** |
| `framer-motion` | `11.18.2` | Animations | HUD orbital micro-animations and transitions. | **PASSED** |
| `lucide-react` | `0.475.0` | SVG Icons | Clean vector icon set; zero runtime vulnerabilities. | **PASSED** |
| `@tauri-apps/api` | `1.6.0` | Native Bridge | Secure IPC between webview and Windows host. | **PASSED** |

### Frontend Build Metrics
- Production compilation command: `npm run build` (`tsc && vite build`)
- Transformed modules: 2,017
- Output bundle:
  - `dist/index.html`: 0.98 kB
  - `dist/assets/index-*.css`: 61.37 kB (gzip: 10.51 kB)
  - `dist/assets/index-*.js`: 644.44 kB (gzip: 160.13 kB)
- TypeScript diagnostics: 0 errors.

---

## 4. Supply Chain Security Recommendations

1. **Lockfile Enforcement**: Always commit `package-lock.json` and maintain frozen Python requirements when preparing desktop distribution packages.
2. **Offline Bundling**: Models for FastEmbed (`bge-small-en-v1.5`), Vosk (`vosk-model-small-en-us-0.15`), and Piper voice files are pre-downloaded to local cache directories to eliminate runtime CDN dependencies.
3. **No Dynamic Remote Code Execution**: No `eval()`, `exec()`, or unverified dynamic imports are used anywhere in the codebase.
