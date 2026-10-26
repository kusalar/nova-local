# NOVA — Setup & Operational Guide

## Prerequisites
- **OS**: Windows 10/11
- **Python**: 3.11+ (Python 3.11.9 verified)
- **Node.js**: v20+ or v22+ (v22.17.0 verified) & npm
- **Ollama**: (Optional for local AI inference) — Download from [ollama.ai](https://ollama.ai)

---

## 1. Quick Start (Unified Launcher)

Double click or run:
```cmd
scripts\start_all.bat
```
This launches both the FastAPI backend on `http://127.0.0.1:8000` and the Vite Command Center on `http://localhost:1420`.

---

## 2. Manual Step-by-Step Launch

### Backend
1. Open PowerShell / Command Prompt in `backend`:
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Verify health endpoint:
   ```bash
   curl http://127.0.0.1:8000/api/health
   ```

### Frontend
1. Open PowerShell / Command Prompt in `apps/desktop`:
   ```bash
   cd apps/desktop
   npm install
   npm run dev
   ```
2. Open your browser or desktop window at:
   ```
   http://localhost:1420
   ```

---

## 3. Local AI Integration with Ollama

NOVA is preconfigured for lightweight, open-weight models:
1. Start Ollama:
   ```powershell
   ollama serve
   ```
2. Pull and test the recommended model (Qwen 2.5 1.5B):
   ```powershell
   ollama run qwen2.5:1.5b
   ```
   *Alternative lightweight model: `ollama run llama3.2:1b`*
3. Once running, NOVA will automatically detect the connection, show **Ollama (Local) Connected** in the LLM matrix, and route conversation queries to your local weights!

---

## 4. Running Backend Tests

```powershell
python -m pytest backend/tests -v
```
Verifies health, system telemetry, AI offline resilience, and SQLite memory persistence.
