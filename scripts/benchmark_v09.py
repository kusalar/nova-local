import time
import os
import sys
import psutil
import json
import sqlite3
from typing import Dict, Any

# Add backend to path
sys.path.insert(0, os.path.abspath("backend"))

from app.tools.system_tools import SystemMonitor
from app.memory.sqlite_memory import memory_bank
from app.memory.project_memory import project_memory
from app.voice.text_to_speech import TextToSpeech
tts_engine = TextToSpeech()
from app.agents.agent_planner import AgentPlanner
from app.database import db_manager, backup_manager
from app.reliability.health_registry import health_registry
from app.reliability.resource_coordinator import resource_coordinator
import asyncio

async def run_benchmarks() -> Dict[str, Any]:
    print("=== NOVA v0.9 PERFORMANCE BENCHMARK SUITE ===")
    results = {}

    # 1. Hardware & System Baseline
    process = psutil.Process(os.getpid())
    idle_cpu_percent = psutil.cpu_percent(interval=1.0)
    idle_ram_percent = psutil.virtual_memory().percent
    backend_rss_mb = process.memory_info().rss / (1024 * 1024)

    results["system_baseline"] = {
        "platform": sys.platform,
        "cpu_count": psutil.cpu_count(logical=True),
        "total_ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "system_cpu_idle_percent": idle_cpu_percent,
        "system_ram_used_percent": idle_ram_percent,
        "python_process_rss_mb": round(backend_rss_mb, 2)
    }
    print(f"Baseline: Process RSS: {backend_rss_mb:.1f} MB, CPU: {idle_cpu_percent}%")

    # 2. SQLite Database & Backup Performance
    t0 = time.perf_counter()
    status = db_manager.get_database_status()
    db_status_latency_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    backup_meta = backup_manager.create_backup(trigger="benchmark", description="Benchmark test backup")
    backup_latency_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    validation = backup_manager.validate_backup(backup_meta["backup_id"])
    validate_latency_ms = (time.perf_counter() - t0) * 1000

    results["database_performance"] = {
        "status_query_latency_ms": round(db_status_latency_ms, 2),
        "online_backup_latency_ms": round(backup_latency_ms, 2),
        "backup_validation_latency_ms": round(validate_latency_ms, 2),
        "backup_size_bytes": backup_meta["size_bytes"],
        "tables_count": status.get("tables_count", 0),
        "records_count": status.get("total_records", 0)
    }
    print(f"Database: Status: {db_status_latency_ms:.2f}ms, Backup: {backup_latency_ms:.2f}ms, Validate: {validate_latency_ms:.2f}ms")

    # 3. Memory Subsystem & Semantic Retrieval
    from app.memory.semantic_search import semantic_search
    t0 = time.perf_counter()
    emb = semantic_search.get_embedding("system diagnostics and hardware telemetry")
    embedding_latency_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    msgs = memory_bank.get_messages(limit=10)
    messages_query_latency_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    proj_context = project_memory.get_project_context_string("nova")
    proj_context_latency_ms = (time.perf_counter() - t0) * 1000

    results["memory_performance"] = {
        "fastembed_onnx_embedding_latency_ms": round(embedding_latency_ms, 2),
        "messages_query_latency_ms": round(messages_query_latency_ms, 2),
        "project_context_resolution_latency_ms": round(proj_context_latency_ms, 2),
        "embedding_dimensions": len(emb) if emb is not None else 0
    }
    print(f"Memory: FastEmbed Embedding: {embedding_latency_ms:.2f}ms, Messages: {messages_query_latency_ms:.2f}ms, Project Context: {proj_context_latency_ms:.2f}ms")

    # 4. Multi-Agent DAG Planning & Scheduling Overhead
    t0 = time.perf_counter()
    plan = await AgentPlanner.create_plan(
        "Inspect my NOVA project and summarize health",
        project_id="nova"
    )
    planning_overhead_ms = (time.perf_counter() - t0) * 1000

    results["agent_planning_performance"] = {
        "dag_decomposition_latency_ms": round(planning_overhead_ms, 2),
        "steps_generated": len(plan.steps),
        "requires_approval": plan.requires_approval
    }
    print(f"Agent Planning: DAG generated in {planning_overhead_ms:.2f}ms ({len(plan.steps)} steps)")

    # 5. Voice Pipeline (Piper TTS synthesis latency)
    tts_sample_text = "System diagnostics complete. All subsystems operational."
    t0 = time.perf_counter()
    audio_data = tts_engine.synthesize(tts_sample_text)
    tts_latency_ms = (time.perf_counter() - t0) * 1000

    results["voice_performance"] = {
        "tts_sample_text_length": len(tts_sample_text),
        "tts_synthesis_latency_ms": round(tts_latency_ms, 2),
        "tts_audio_samples_generated": len(audio_data) if audio_data is not None else 0
    }
    print(f"Voice: Piper TTS synthesized '{tts_sample_text[:30]}...' in {tts_latency_ms:.2f}ms")

    # 6. Centralized Health Subsystem Evaluation
    t0 = time.perf_counter()
    health_summary = await health_registry.get_detailed_health(force_refresh=True)
    health_eval_latency_ms = (time.perf_counter() - t0) * 1000

    results["reliability_subsystem_health"] = {
        "full_health_evaluation_latency_ms": round(health_eval_latency_ms, 2),
        "subsystems_evaluated": len(health_summary.subsystems),
        "overall_status": health_summary.overall_status
    }
    print(f"Reliability: 10 subsystems evaluated in {health_eval_latency_ms:.2f}ms -> Overall: {health_summary.overall_status}")

    # 7. Stress & Stability Iteration (50 SQLite read/write cycles)
    rss_before_stress = process.memory_info().rss / (1024 * 1024)
    t0 = time.perf_counter()
    for i in range(50):
        with db_manager.transaction() as conn:
            conn.execute(
                "INSERT INTO system_logs (level, event, metadata) VALUES (?, ?, ?);",
                ("INFO", "benchmark_stress", json.dumps({"cycle": i}))
            )
    stress_duration_ms = (time.perf_counter() - t0) * 1000
    rss_after_stress = process.memory_info().rss / (1024 * 1024)

    results["stress_stability_metrics"] = {
        "transactions_executed": 50,
        "total_duration_ms": round(stress_duration_ms, 2),
        "avg_transaction_latency_ms": round(stress_duration_ms / 50, 2),
        "rss_before_mb": round(rss_before_stress, 2),
        "rss_after_mb": round(rss_after_stress, 2),
        "ram_growth_mb": round(rss_after_stress - rss_before_stress, 2)
    }
    print(f"Stress Test: 50 transactions in {stress_duration_ms:.2f}ms (Avg {stress_duration_ms/50:.2f}ms). RAM growth: {rss_after_stress - rss_before_stress:.2f} MB")

    return results

if __name__ == "__main__":
    out = asyncio.run(run_benchmarks())
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("Benchmark complete. Results written to benchmark_results.json.")
