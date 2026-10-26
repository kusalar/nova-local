# NOVA v0.9 — Hardware Performance & Latency Benchmark Report

## 1. Test Environment & Methodology

All measurements were captured directly on the local deployment machine running Windows 11 with the background desktop frontend and Ollama server active.

### 1.1 Hardware Specifications
- **Processor**: Intel Core i3-1115G4 @ 3.00 GHz (2 physical cores / 4 threads, 6 MB Smart Cache)
- **Memory**: 11.75 GB Total Physical RAM (DDR4)
- **Graphics**: Integrated Intel UHD Graphics (CPU shared memory)
- **Storage**: NVMe Solid State Drive
- **Operating System**: Windows 11 Home 64-bit (Build 26100)
- **Python Runtime**: Python 3.11.9 (64-bit, AMD64 MSC v.1938)
- **Desktop Runtime**: React 18, Vite 5.4, Tauri 1.6

### 1.2 Benchmark Methodology
Benchmarks were executed using `scripts/benchmark_v09.py` measuring actual wall-clock elapsed time via `time.perf_counter()` and process telemetry via `psutil`. No artificial mocks, simulated delays, or synthetic figures were used.

---

## 2. Benchmark Results & Operational Latency

### 2.1 Baseline Resource Consumption

| Metric | Measured Value | Operational Assessment |
| :--- | :--- | :--- |
| **Backend Process RSS** | `282.91 MB` | Modest memory footprint for full neural core, SQLite, and audio pipeline |
| **System Idle CPU Load** | `14.1% – 19.1%` | Stable idle state without runaway polling loops |
| **Frontend Memory Footprint**| `~85 MB` | Vite / Tauri webview memory allocation |
| **Total RAM Utilization** | `86.7%` | Operating within the 12 GB physical envelope |

### 2.2 Database Operations & Backup Performance

| Database Operation | Measured Latency | Throughput / Overhead |
| :--- | :--- | :--- |
| **Status & Integrity Query** | `5.26 ms` | Queries WAL size, page count, and table record counts |
| **Online Non-blocking Backup** | `92.04 ms` | Copies full 471 kB database to backup directory via SQLite backup API |
| **SHA-256 Checksum Validation**| `1.87 ms` | Validates hash match and verifies backup database integrity |
| **50 Transaction Stress Burst** | `840.55 ms` | **16.81 ms average per transaction** under sequential write stress |
| **RAM Growth after 50 Writes** | `+0.14 MB` | Negligible heap growth; zero memory leak in transaction loop |

### 2.3 Semantic Memory & Retrieval Latency

| Operation | Measured Latency | Details |
| :--- | :--- | :--- |
| **FastEmbed Vector Generation**| `9.13 ms` | Dense 384-dimensional embedding generated on CPU via ONNX Runtime |
| **Message History Query** | `1.57 ms` | SQLite indexed query returning latest session records |
| **Project Context Resolution** | `0.61 ms` | Resolves active project tech stack, recent milestones, and decisions |

### 2.4 Multi-Agent Planning & Orchestration

| Operation | Measured Latency | Details |
| :--- | :--- | :--- |
| **DAG Decomposition & Safety Check** | `0.86 ms` | Deterministic template decomposition, dependency validation, and permission checks |

### 2.5 Voice Pipeline & Local Synthesis

| Operation | Measured Latency | Details |
| :--- | :--- | :--- |
| **Piper TTS Neural Speech Synthesis** | `237.32 ms` | Synthesizes 56 characters (60,928 audio samples) offline |
| **Wake Word Detection Interval** | `~20 ms / chunk` | OpenWakeWord ONNX evaluation per 1280-sample audio buffer |

### 2.6 Full Subsystem Health Audit

| Operation | Measured Latency | Details |
| :--- | :--- | :--- |
| **10-Subsystem Comprehensive Audit** | `8.31 s` | Performs real network probe to Ollama, audio device check, filesystem checks, and database PRAGMAs |

---

## 3. Hardware Governor & Concurrency Limits

On dual-core i3 hardware, executing simultaneous heavy inference operations causes severe CPU saturation and audio stuttering. NOVA v0.9 enforces strict hardware-aware concurrency limits via `ResourceCoordinator`:
- **`max_concurrent_inferences = 1`**: Queues incoming inference requests to prevent CPU thrashing.
- **`max_concurrent_ocr = 1`**: Serializes full-display OCR operations.
- **Inference Timeouts**: 60-second execution deadline with automatic release of semaphores on cancel or error.

---

## 4. Stability & Extended Operation Findings

- **RAM Stability**: Sequential operations show minimal RAM accumulation (+0.14 MB over 50 transaction bursts).
- **WAL Auto-Checkpoint**: Under default SQLite settings, Write-Ahead Log is periodically flushed, preventing the `-wal` file from unbounded growth.
- **WebSocket Polling Suppression**: The System Reliability Center polls at a conservative 15-second interval and automatically suspends polling when the window is hidden (`document.visibilityState !== 'visible'`).
