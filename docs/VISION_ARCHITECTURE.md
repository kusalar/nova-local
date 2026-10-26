# NOVA v0.5 — Multimodal Visual Intelligence & Screen Awareness Architecture

## 1. Executive Summary

NOVA v0.5 introduces local, offline-first multimodal visual intelligence to the Neural Operational Virtual Assistant. Prior to v0.5, NOVA was capable of conversational reasoning (v0.1), real-time offline speech interaction (v0.2), persistent semantic project memory (v0.3), and permission-controlled desktop tool execution (v0.4).

With v0.5, NOVA gains **visual screen awareness**: the capability to understand the user's desktop display, isolate active application windows, extract structured text using local Windows OCR, cross-correlate visual content with project memory, answer visual queries, and vocalize contextual insights via Piper TTS.

```mermaid
graph TD
    A["User Directive / Voice Command"] --> B["Vision Intelligence Engine"]
    B --> C["ScreenCaptureEngine<br/>(Win32 / PIL ImageGrab)"]
    C --> D["PrivacyFilter & Sensitive Shield"]
    D --> E["ImageProcessor<br/>(Lanczos Downscale / Base64)"]
    E --> F["Local OcrEngine<br/>(Windows.Media.Ocr / Fallback)"]
    F --> G["VisualContextBuilder"]
    H["v0.3 ProjectMemoryManager"] --> G
    I["WindowManager<br/>(Win32 Foreground & Process)"] --> G
    G --> J["Concise Structured Context"]
    J --> K["Ollama Inference Model<br/>(qwen3:4b / gemma2:2b / VLM)"]
    K --> L["Voice Piper TTS"]
    K --> M["Frontend Vision Center HUD"]
```

---

## 2. Core Subsystems

### 2.1. Screen Capture Engine (`backend/app/vision/screen_capture.py`)
- **Multi-Monitor Awareness**: Enumerates physical display adapters and monitor coordinates using Win32 `EnumDisplayMonitors` and `GetMonitorInfoW`. Detects primary display, offsets, and dimensions.
- **Active Window Isolation**: Queries foreground window bounding box via `WindowManager` and extracts precise window coordinates `(left, top, right, bottom)` for targeted window captures.
- **Fail-Safe Capture Handling**: Uses `PIL.ImageGrab` with virtual desktop bounding rect support. Gracefully handles Session 0/headless execution by raising descriptive `ScreenCaptureError` instances rather than crashing.
- **Explicit Initiation**: Captures are performed **strictly upon explicit user command** or visible UI button invocation. Continuous background screen polling is strictly forbidden.

### 2.2. Window Awareness Manager (`backend/app/vision/window_manager.py`)
- **Foreground Tracking**: Resolves the active application title and window handle (`HWND`) via Win32 `GetForegroundWindow`.
- **Process Identification**: Associates window handles with process IDs using `GetWindowThreadProcessId` and maps them to clean process/application names using `psutil`.
- **Top-Level Window Enumeration**: Uses `EnumWindows` and `IsWindowVisible` to enumerate visible desktop applications while filtering out zero-size or off-screen artifacts.
- **Credential & Security Shield**: Evaluates process names and window titles against known credential vaults (`1password.exe`, `bitwarden.exe`, `keepassxc.exe`, `consent.exe`). Blocks captures of sensitive windows when protection is enabled.

### 2.3. Image Processor (`backend/app/vision/image_processor.py`)
- **Smart Downscaling**: Downscales high-resolution screenshots (4K/1440p/1080p) to a configurable maximum dimension (default: 1280px) using high-quality `LANCZOS` resampling, preserving aspect ratios and CPU efficiency.
- **Encoding & Data URLs**: Generates optimized PNG (lossless) and JPEG (85% quality) payloads and base64 preview URLs for real-time frontend rendering.
- **Ephemeral Storage Lifecycle**: Manages temporary captures in an ephemeral directory (`temp_captures/`), enforcing cleanup according to the user's retention policy.

### 2.4. Local OCR Engine (`backend/app/vision/ocr_engine.py`)
- **Native Windows Runtime OCR**: Integrates directly with `Windows.Media.Ocr.OcrEngine` using `winrt-Windows.Media.Ocr` and `winrt-Windows.Graphics.Imaging`. Runs 100% locally and offline on CPU in <200ms.
- **Structured Coordinate Extraction**: Preserves word and line bounding boxes `(x, y, width, height)` and confidence scores.
- **Heuristic Region Detection**: Segments detected text lines into visual regions/paragraphs based on vertical line spacing.
- **Asynchronous Worker Thread Isolation**: Dispatches WinRT OCR execution to a background worker thread via `asyncio.to_thread`, ensuring zero event-loop blocking during speech processing.
- **Graceful Fallback**: Automatically provides fallback metadata extraction if native Windows OCR is disabled or running in headless unit tests.

### 2.5. Privacy Filter & Redactor (`backend/app/vision/privacy_filter.py`)
- **Credential Redaction**: Scans OCR text and redacts sensitive tokens using comprehensive regular expressions:
  - OpenAI API keys (`sk-...`)
  - Google Cloud / Gemini API keys (`AIza...`)
  - GitHub Personal Access Tokens (`ghp_...`)
  - AWS Access Keys (`AKIA...`)
  - Bearer Authorization headers (`Bearer ...`)
  - JWT Tokens (`ey...`)
  - Key-value secrets and passwords (`password = "..."`)
  - Credit Card numbers (formatted 13-19 digits)
  - Private Key blocks (`-----BEGIN RSA PRIVATE KEY-----`)
- **Structured Sanitization**: Redacts both raw full text and individual word nodes in `OcrResult.lines`.

### 2.6. Visual Context Builder (`backend/app/vision/visual_context.py`)
- **Compact Context Formatting**: Condenses window awareness and OCR text into a concise prompt block. Avoids token bloat by applying intelligent truncation limits (max 2,500 characters).
- **v0.3 Project Memory Integration**: Automatically scans the active window title and on-screen text for known project names or slugs in `project_memory`. If a match is found (e.g. `Nova - Visual Studio Code`), injects project tech stack, decisions, and pending tasks.

### 2.7. Central Vision Manager (`backend/app/vision/vision_manager.py`)
- **Pipeline Orchestrator**: Coordinates capture, privacy filtering, OCR extraction, context construction, and LLM chat inference.
- **VLM Detection**: Automatically queries Ollama (`/api/tags`) for installed multimodal vision models (`moondream`, `llava`, `minicpm-v`, `bakllava`). Operates seamlessly in `OCR_ONLY` mode when no VLM is installed.
- **Retention Controls**: Implements `EPHEMERAL` (purge immediately after answer), `SESSION` (retain in cache until clear), and `PERSISTENT` retention policies.

---

## 3. Hardware Target & Performance Optimization

### Target Hardware Profile
- **CPU**: Intel Core i3-1115G4 (2 cores, 4 threads, 3.0 GHz base / 4.1 GHz boost)
- **RAM**: 12 GB
- **GPU**: Integrated Intel UHD Graphics
- **OS**: Windows 11 / Windows 10 (64-bit)

### Performance Engineering Safeguards
1. **CPU-First Architecture**: Avoids heavy Python neural OCR models (PaddleOCR / EasyOCR / PyTorch) which consume >1.5GB RAM. Leverages Windows' built-in C++ WinRT OCR engine with near-zero memory footprint.
2. **Pre-OCR Image Downscaling**: Reduces OCR processing time by downscaling images before rasterization, keeping extraction times under 250ms on a 2-core i3.
3. **Non-Blocking Thread Dispatch**: All image decoding and OCR routines run in thread pools via `asyncio.to_thread`, ensuring microphone audio capture and wake-word detection are never interrupted.
4. **Prompt Compression**: Context is compressed and capped at 2,500 characters to ensure fast inference on local 2B–4B LLMs (`gemma2:2b`, `qwen3:4b`).

---

## 4. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/vision/status` | Returns vision status, display count, active window, OCR engine, and VLM readiness. |
| `GET` | `/api/vision/windows` | Enumerates visible desktop application windows with process details and bounds. |
| `POST` | `/api/vision/capture` | Initiates an explicit screenshot of primary screen, specific monitor, or active window. |
| `POST` | `/api/vision/analyze` | Full Visual Q&A pipeline (Capture -> Redact -> OCR -> Correlate Memory -> LLM). |
| `POST` | `/api/vision/ocr` | Performs local OCR extraction on a new or existing capture. |
| `GET` | `/api/vision/settings` | Retrieves user privacy settings, retention policies, and scaling limits. |
| `PATCH` | `/api/vision/settings` | Updates runtime vision parameters. |
| `POST` | `/api/vision/clear` | Purges all temporary screenshots and cached visual metadata from disk. |
