import time
import os
import psutil
import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.config import settings
from app.database import db_manager

logger = logging.getLogger("nova.reliability.health")

class SubsystemState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    RECOVERING = "RECOVERING"
    ERROR = "ERROR"

class SubsystemHealth(BaseModel):
    name: str
    state: SubsystemState
    message: str
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    last_checked: str

class SystemHealthSummary(BaseModel):
    overall_status: SubsystemState
    app_name: str
    version: str
    uptime_seconds: float
    timestamp: str
    subsystems: Dict[str, SubsystemHealth]

class HealthRegistry:
    """
    Centralized health registry tracking operational readiness, degradation,
    and faults across all 10 major NOVA subsystems.
    """

    def __init__(self):
        self.start_time = time.time()
        self._cached_health: Optional[SystemHealthSummary] = None
        self._last_evaluated: float = 0.0
        self._cache_ttl: float = 2.0  # Cache health evaluations for 2 seconds to avoid excessive polling

    @property
    def uptime_seconds(self) -> float:
        return round(time.time() - self.start_time, 1)

    async def check_backend(self) -> SubsystemHealth:
        start = time.time()
        try:
            proc = psutil.Process(os.getpid())
            mem_info = proc.memory_info()
            cpu_pct = proc.cpu_percent(interval=None)
            lat = round((time.time() - start) * 1000, 2)
            return SubsystemHealth(
                name="backend",
                state=SubsystemState.HEALTHY,
                message="Core FastAPI backend operational",
                latency_ms=lat,
                details={
                    "uptime_seconds": self.uptime_seconds,
                    "ram_rss_mb": round(mem_info.rss / (1024 * 1024), 1),
                    "cpu_percent": cpu_pct,
                    "num_threads": proc.num_threads()
                },
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return SubsystemHealth(
                name="backend",
                state=SubsystemState.ERROR,
                message=f"Backend telemetry error: {str(e)}",
                last_checked=datetime.now().isoformat()
            )

    async def check_database(self) -> SubsystemHealth:
        start = time.time()
        try:
            status = db_manager.get_database_status()
            lat = round((time.time() - start) * 1000, 2)
            is_healthy = status.get("healthy", False)
            state = SubsystemState.HEALTHY if is_healthy else SubsystemState.ERROR
            msg = "SQLite database online and integrity verified" if is_healthy else "Database corruption or integrity error detected"
            return SubsystemHealth(
                name="database",
                state=state,
                message=msg,
                latency_ms=lat,
                details={
                    "total_size_kb": round(status.get("total_size_bytes", 0) / 1024, 1),
                    "journal_mode": status.get("journal_mode", "unknown"),
                    "tables_count": status.get("tables_count", 0),
                    "total_records": status.get("total_records", 0),
                    "wal_enabled": status.get("journal_mode", "").lower() == "wal"
                },
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return SubsystemHealth(
                name="database",
                state=SubsystemState.ERROR,
                message=f"Database check failed: {str(e)}",
                last_checked=datetime.now().isoformat()
            )

    async def check_ollama(self) -> SubsystemHealth:
        start = time.time()
        try:
            from app.ai.model_manager import model_manager
            report = await model_manager.health_check()
            lat = round((time.time() - start) * 1000, 2)
            online = report.get("online", False)
            has_models = report.get("model_ready", False)

            if online and has_models:
                state = SubsystemState.HEALTHY
                msg = f"Ollama operational with active model '{report.get('active_model')}'"
            elif online:
                state = SubsystemState.DEGRADED
                msg = "Ollama is online but active model is not pulled yet."
            else:
                state = SubsystemState.UNAVAILABLE
                msg = report.get("message", "Ollama daemon unreachable.")

            return SubsystemHealth(
                name="ollama",
                state=state,
                message=msg,
                latency_ms=lat,
                details={
                    "endpoint": "http://localhost:11434",
                    "active_model": report.get("active_model"),
                    "available_models_count": len(report.get("available_models", []))
                },
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return SubsystemHealth(
                name="ollama",
                state=SubsystemState.UNAVAILABLE,
                message=f"Ollama check failed: {str(e)}",
                last_checked=datetime.now().isoformat()
            )

    async def check_voice(self) -> SubsystemHealth:
        start = time.time()
        try:
            from app.voice.audio_manager import audio_manager
            is_running = audio_manager.is_running
            mode = audio_manager.pipeline_mode
            wake_ready = audio_manager.wake_word_engine is not None
            tts_ready = audio_manager.tts is not None
            lat = round((time.time() - start) * 1000, 2)

            if is_running and wake_ready and tts_ready:
                state = SubsystemState.HEALTHY
                msg = f"Voice pipeline active ({mode})"
            elif is_running:
                state = SubsystemState.DEGRADED
                msg = "Voice pipeline active with partial models"
            else:
                state = SubsystemState.DEGRADED if settings.VOICE_ENABLED else SubsystemState.HEALTHY
                msg = "Voice pipeline standby / paused"

            return SubsystemHealth(
                name="voice",
                state=state,
                message=msg,
                latency_ms=lat,
                details={
                    "is_running": is_running,
                    "pipeline_mode": mode,
                    "sample_rate": audio_manager.sample_rate,
                    "wake_word_enabled": audio_manager.wake_word_enabled,
                    "active_subscribers": len(audio_manager._ws_subscribers)
                },
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return SubsystemHealth(
                name="voice",
                state=SubsystemState.ERROR,
                message=f"Voice check failed: {str(e)}",
                last_checked=datetime.now().isoformat()
            )

    async def check_memory(self) -> SubsystemHealth:
        start = time.time()
        try:
            from app.memory.sqlite_memory import memory_bank
            from app.memory.long_term_memory import long_term_memory
            stats = memory_bank.get_stats()
            lt_stats = long_term_memory.get_memory_stats()
            lat = round((time.time() - start) * 1000, 2)
            return SubsystemHealth(
                name="memory",
                state=SubsystemState.HEALTHY,
                message="Persistent memory and semantic retrieval operational",
                latency_ms=lat,
                details={
                    "total_messages": stats.get("total_messages", 0),
                    "total_memories": lt_stats.get("total_memories", 0),
                    "total_projects": lt_stats.get("total_projects", 0),
                    "embedding_model": settings.MEMORY_EMBEDDING_MODEL
                },
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return SubsystemHealth(
                name="memory",
                state=SubsystemState.ERROR,
                message=f"Memory check failed: {str(e)}",
                last_checked=datetime.now().isoformat()
            )

    async def check_tools(self) -> SubsystemHealth:
        start = time.time()
        try:
            from app.tools.tool_registry import tool_registry
            from app.tools.permission_manager import permission_manager
            tools = tool_registry.list_tools()
            roots_count = len(permission_manager.allowed_roots)
            lat = round((time.time() - start) * 1000, 2)
            return SubsystemHealth(
                name="tools",
                state=SubsystemState.HEALTHY,
                message=f"{len(tools)} tools registered with permission sandbox",
                latency_ms=lat,
                details={
                    "registered_tools": len(tools),
                    "allowed_roots_count": roots_count,
                    "sandbox_active": True
                },
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return SubsystemHealth(
                name="tools",
                state=SubsystemState.ERROR,
                message=f"Tools check failed: {str(e)}",
                last_checked=datetime.now().isoformat()
            )

    async def check_vision(self) -> SubsystemHealth:
        start = time.time()
        try:
            from app.vision.vision_manager import vision_manager
            status = await vision_manager.get_status()
            lat = round((time.time() - start) * 1000, 2)
            ocr_ready = status.get("ocr_ready", False)
            capture_ready = status.get("capture_ready", False)

            if ocr_ready and capture_ready:
                state = SubsystemState.HEALTHY
                msg = "Screen capture and Windows OCR ready"
            elif capture_ready:
                state = SubsystemState.DEGRADED
                msg = "Screen capture ready, OCR operating in fallback mode"
            else:
                state = SubsystemState.UNAVAILABLE
                msg = "Vision subsystem unavailable"

            return SubsystemHealth(
                name="vision",
                state=state,
                message=msg,
                latency_ms=lat,
                details={
                    "ocr_ready": ocr_ready,
                    "capture_ready": capture_ready,
                    "privacy_filter_active": status.get("privacy_filter_active", True)
                },
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return SubsystemHealth(
                name="vision",
                state=SubsystemState.ERROR,
                message=f"Vision check failed: {str(e)}",
                last_checked=datetime.now().isoformat()
            )

    async def check_agents(self) -> SubsystemHealth:
        start = time.time()
        try:
            from app.agents.agent_registry import agent_registry
            from app.agents.workflow_logger import workflow_logger
            agents = agent_registry.list_agents()
            recent_wf = workflow_logger.list_workflows(limit=5)
            lat = round((time.time() - start) * 1000, 2)
            return SubsystemHealth(
                name="agents",
                state=SubsystemState.HEALTHY if len(agents) >= 5 else SubsystemState.DEGRADED,
                message=f"{len(agents)} specialized personas active; DAG scheduler ready",
                latency_ms=lat,
                details={
                    "personas_count": len(agents),
                    "recent_workflows_count": len(recent_wf)
                },
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return SubsystemHealth(
                name="agents",
                state=SubsystemState.ERROR,
                message=f"Agents check failed: {str(e)}",
                last_checked=datetime.now().isoformat()
            )

    async def check_automation(self) -> SubsystemHealth:
        start = time.time()
        try:
            from app.automation import automation_manager
            status = automation_manager.get_status()
            lat = round((time.time() - start) * 1000, 2)
            is_paused = status.is_paused
            heartbeat_alive = automation_manager.scheduler._heartbeat_task is not None and not automation_manager.scheduler._heartbeat_task.done()

            state = SubsystemState.DEGRADED if is_paused else (SubsystemState.HEALTHY if heartbeat_alive else SubsystemState.DEGRADED)
            msg = "Automations paused by user" if is_paused else ("Scheduler heartbeat active" if heartbeat_alive else "Scheduler heartbeat idle")

            return SubsystemHealth(
                name="automation",
                state=state,
                message=msg,
                latency_ms=lat,
                details={
                    "active_rules": status.active_count,
                    "paused_rules": status.paused_count,
                    "total_rules": status.total_count,
                    "is_paused": is_paused,
                    "heartbeat_alive": heartbeat_alive
                },
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return SubsystemHealth(
                name="automation",
                state=SubsystemState.ERROR,
                message=f"Automation check failed: {str(e)}",
                last_checked=datetime.now().isoformat()
            )

    async def check_personalization(self) -> SubsystemHealth:
        start = time.time()
        try:
            from app.personalization import personalization_manager
            status = personalization_manager.get_status()
            lat = round((time.time() - start) * 1000, 2)
            is_enabled = status.enabled
            state = SubsystemState.HEALTHY if is_enabled else SubsystemState.DEGRADED
            msg = "Adaptive personalization and knowledge graph online" if is_enabled else "Personalization disabled by user"

            return SubsystemHealth(
                name="personalization",
                state=state,
                message=msg,
                latency_ms=lat,
                details={
                    "enabled": is_enabled,
                    "total_preferences": status.total_preferences,
                    "explicit_preferences": status.explicit_preferences_count,
                    "graph_entities": status.graph_entities_count,
                    "graph_relations": status.graph_relations_count,
                    "active_recommendations": status.active_recommendations_count
                },
                last_checked=datetime.now().isoformat()
            )
        except Exception as e:
            return SubsystemHealth(
                name="personalization",
                state=SubsystemState.ERROR,
                message=f"Personalization check failed: {str(e)}",
                last_checked=datetime.now().isoformat()
            )

    async def get_detailed_health(self, force_refresh: bool = False) -> SystemHealthSummary:
        """
        Runs health evaluations across all 10 subsystems and aggregates overall status.
        """
        now = time.time()
        if not force_refresh and self._cached_health and (now - self._last_evaluated < self._cache_ttl):
            return self._cached_health

        subsystems: Dict[str, SubsystemHealth] = {}
        subsystems["backend"] = await self.check_backend()
        subsystems["database"] = await self.check_database()
        subsystems["ollama"] = await self.check_ollama()
        subsystems["voice"] = await self.check_voice()
        subsystems["memory"] = await self.check_memory()
        subsystems["tools"] = await self.check_tools()
        subsystems["vision"] = await self.check_vision()
        subsystems["agents"] = await self.check_agents()
        subsystems["automation"] = await self.check_automation()
        subsystems["personalization"] = await self.check_personalization()

        # Compute overall status
        states = [s.state for s in subsystems.values()]
        if SubsystemState.ERROR in states or not subsystems["database"].state == SubsystemState.HEALTHY:
            overall = SubsystemState.ERROR
        elif SubsystemState.UNAVAILABLE in states or SubsystemState.DEGRADED in states:
            overall = SubsystemState.DEGRADED
        else:
            overall = SubsystemState.HEALTHY

        summary = SystemHealthSummary(
            overall_status=overall,
            app_name=settings.APP_NAME,
            version=settings.VERSION,
            uptime_seconds=self.uptime_seconds,
            timestamp=datetime.now().isoformat(),
            subsystems=subsystems
        )

        self._cached_health = summary
        self._last_evaluated = now
        return summary

health_registry = HealthRegistry()
