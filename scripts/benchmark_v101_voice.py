"""Controlled A/B/C/D latency measurements for NOVA v1.0.1.

A. Direct Ollama request without NOVA
B. NOVA text-only request
C. NOVA voice dispatch (push-to-talk path, STT mocked)
D. Idle resource sample: PTT standby vs wake-word capture

Does not log prompt text. Uses a short public arithmetic prompt.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

PROMPT = "Reply with one short sentence: what is 2 plus 2?"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
NOVA = os.environ.get("NOVA_API", "http://127.0.0.1:8000").rstrip("/")
MODEL = os.environ.get("NOVA_BENCH_MODEL", "qwen2.5:1.5b")
RESULTS_PATH = ROOT / "benchmark_v101_results.json"


def sample_resources(proc: psutil.Process | None = None) -> dict:
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.4)
    ollama_cpu = None
    ollama_rss_mb = None
    for p in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
        try:
            name = (p.info.get("name") or "").lower()
            if "ollama" in name:
                ollama_cpu = p.cpu_percent(interval=0.2)
                rss = p.info.get("memory_info")
                ollama_rss_mb = round(rss.rss / (1024 * 1024), 1) if rss else None
                break
        except (psutil.Error, Exception):
            continue
    return {
        "system_cpu_percent": cpu,
        "system_ram_percent": ram.percent,
        "system_ram_used_gb": round(ram.used / (1024 ** 3), 2),
        "ollama_cpu_percent": ollama_cpu,
        "ollama_rss_mb": ollama_rss_mb,
    }


def bench_direct_ollama(num_thread: int | None, tag: str) -> dict:
    options = {"num_ctx": 1024, "num_predict": 96, "temperature": 0.2}
    if num_thread is not None:
        options["num_thread"] = num_thread
    payload = {
        "model": MODEL,
        "stream": True,
        "keep_alive": "10m",
        "options": options,
        "messages": [
            {"role": "system", "content": "You are NOVA. Reply in one short sentence."},
            {"role": "user", "content": PROMPT},
        ],
    }
    t0 = time.perf_counter()
    ttft = None
    eval_count = None
    eval_duration = None
    prompt_eval_count = None
    prompt_eval_duration = None
    total_duration = None
    load_duration = None
    tokens = 0
    try:
        with httpx.Client(timeout=180.0) as client:
            with client.stream("POST", f"{OLLAMA}/api/chat", json=payload) as res:
                res.raise_for_status()
                for line in res.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    msg = data.get("message") or {}
                    if msg.get("content") and ttft is None:
                        ttft = (time.perf_counter() - t0) * 1000.0
                    if data.get("done"):
                        eval_count = data.get("eval_count")
                        eval_duration = data.get("eval_duration")
                        prompt_eval_count = data.get("prompt_eval_count")
                        prompt_eval_duration = data.get("prompt_eval_duration")
                        total_duration = data.get("total_duration")
                        load_duration = data.get("load_duration")
                        tokens = eval_count or 0
    except Exception as e:
        return {"tag": tag, "ok": False, "error": str(e), "model": MODEL, "options": options}

    tok_s = None
    if eval_count and eval_duration:
        tok_s = eval_count / (eval_duration / 1e9)
    return {
        "tag": tag,
        "ok": True,
        "path": "direct_ollama",
        "model": MODEL,
        "options": options,
        "keep_alive": "10m",
        "ttft_ms": round(ttft, 2) if ttft is not None else None,
        "total_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "eval_count": eval_count,
        "prompt_eval_count": prompt_eval_count,
        "tokens_per_sec": round(tok_s, 3) if tok_s else None,
        "prompt_eval_ms": round(prompt_eval_duration / 1e6, 2) if prompt_eval_duration else None,
        "eval_ms": round(eval_duration / 1e6, 2) if eval_duration else None,
        "ollama_total_ms": round(total_duration / 1e6, 2) if total_duration else None,
        "load_ms": round(load_duration / 1e6, 2) if load_duration else None,
        "model_was_loaded": (load_duration is not None and load_duration < 500_000_000),
        "ollama_requests": 1,
        "resources_after": sample_resources(),
    }


def bench_nova_text() -> dict:
    t0 = time.perf_counter()
    ttft = None
    assembled_len = 0
    metrics = {}
    ollama_calls = None
    try:
        with httpx.Client(timeout=180.0) as client:
            with client.stream(
                "POST",
                f"{NOVA}/api/chat/stream",
                json={"message": PROMPT, "history": [], "profile": "text"},
            ) as res:
                res.raise_for_status()
                for line in res.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get("type") == "token" and event.get("content") and ttft is None:
                        ttft = (time.perf_counter() - t0) * 1000.0
                    if event.get("type") == "token":
                        assembled_len += len(event.get("content") or "")
                    if event.get("metrics"):
                        metrics = event["metrics"]
                    if event.get("type") == "done":
                        ollama_calls = 1
    except Exception as e:
        return {"path": "nova_text", "ok": False, "error": str(e), "model": MODEL}

    return {
        "path": "nova_text",
        "ok": True,
        "model": MODEL,
        "ttft_ms": round(ttft, 2) if ttft is not None else None,
        "total_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "response_chars": assembled_len,
        "ollama_requests": ollama_calls or 1,
        "metrics": metrics,
        "resources_after": sample_resources(),
    }


def bench_nova_voice_dispatch() -> dict:
    """In-process PTT path with STT skipped (recognized text injected)."""
    os.chdir(ROOT / "backend")
    from app.voice.audio_manager import audio_manager
    from app.ai.inference_tracer import recent_traces

    t0 = time.perf_counter()
    try:
        audio_manager.tts.speak = lambda *a, **k: True
        audio_manager.tts.enqueue = lambda *a, **k: None
        audio_manager.tts.mark_generation_complete = lambda *a, **k: None
        audio_manager._dispatch_to_brain(PROMPT, stt_ms=0.0, trigger_source="manual")
    except Exception as e:
        return {"path": "nova_voice_ptt", "ok": False, "error": str(e)}
    traces = recent_traces(1)
    return {
        "path": "nova_voice_ptt",
        "ok": True,
        "total_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "trace": traces[-1] if traces else None,
        "resources_after": sample_resources(),
    }


def bench_idle_modes() -> dict:
    from app.voice.audio_manager import audio_manager

    audio_manager.stop()
    audio_manager.wake_word_enabled = False
    audio_manager.start()
    time.sleep(1.2)
    ptt = sample_resources()
    ptt["mic_open"] = audio_manager.audio_stream is not None
    audio_manager.stop()

    audio_manager.wake_word_enabled = True
    started = audio_manager.start()
    time.sleep(1.2)
    ww = sample_resources()
    ww["mic_open"] = audio_manager.audio_stream is not None
    ww["start_ok"] = started
    audio_manager.stop()
    audio_manager.wake_word_enabled = False
    return {"push_to_talk_idle": ptt, "wake_word_idle": ww}


def main() -> None:
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "prompt_chars": len(PROMPT),
        "hardware_note": "Intel Core i3-1115G4 class target; values are from this run only.",
    }
    print("Sampling idle resources...")
    results["idle_before"] = sample_resources()

    print("A1. Direct Ollama num_thread=2 ...")
    results["A_direct_thread2"] = bench_direct_ollama(2, "direct_thread2")
    print(results["A_direct_thread2"])

    print("A2. Direct Ollama automatic threads (omit num_thread) ...")
    results["A_direct_auto"] = bench_direct_ollama(None, "direct_auto")
    print(results["A_direct_auto"])

    print("B. NOVA text stream ...")
    results["B_nova_text"] = bench_nova_text()
    print(results["B_nova_text"])

    print("C. NOVA voice PTT dispatch (in-process) ...")
    try:
        results["C_nova_voice_ptt"] = bench_nova_voice_dispatch()
    except Exception as e:
        results["C_nova_voice_ptt"] = {"ok": False, "error": str(e)}
    print(results["C_nova_voice_ptt"])

    print("D. Idle PTT vs wake-word ...")
    try:
        results["D_idle_modes"] = bench_idle_modes()
    except Exception as e:
        results["D_idle_modes"] = {"ok": False, "error": str(e)}
    print(results["D_idle_modes"])

    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
