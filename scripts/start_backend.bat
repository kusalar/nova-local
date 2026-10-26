@echo off
title NOVA AI Core — Backend Service
cd /d "%~dp0\..\backend"
echo [NOVA] Starting FastAPI AI Core on http://127.0.0.1:8000 ...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
