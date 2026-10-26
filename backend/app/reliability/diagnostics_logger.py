import time
import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import deque

logger = logging.getLogger("nova.reliability.diagnostics")

class DiagnosticsLogger:
    """
    Observability and diagnostic aggregation for NOVA v0.9:
    - Maintains in-memory circular buffer of recent errors/warnings.
    - Exports sanitized system diagnostics stripped of private tokens, paths, and user data.
    """

    def __init__(self, max_errors: int = 50):
        self._recent_errors: deque = deque(maxlen=max_errors)

    def record_error(
        self,
        subsystem: str,
        message: str,
        level: str = "ERROR",
        details: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ):
        """Record an error event into the diagnostic ring buffer."""
        clean_msg = str(message)
        clean_details = details or {}

        # Redact any obvious tokens or secrets
        from app.tools.permission_manager import permission_manager
        clean_details = permission_manager.redact_sensitive_data(clean_details)

        entry = {
            "id": f"err_{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "subsystem": subsystem,
            "level": level,
            "message": clean_msg,
            "details": clean_details,
            "exception_type": type(exception).__name__ if exception else None
        }
        self._recent_errors.appendleft(entry)
        logger.debug(f"Diagnostic event recorded [{subsystem} {level}]: {clean_msg[:80]}")

    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return list of recent error records."""
        return list(self._recent_errors)[:limit]

    def clear_errors(self):
        """Clear error buffer."""
        self._recent_errors.clear()

    async def generate_diagnostic_export(self) -> Dict[str, Any]:
        """
        Creates an end-to-end diagnostic export for troubleshooting.
        Guaranteed to sanitize user prompts, private keys, paths, and memory contents.
        """
        from .health_registry import health_registry
        from app.database import db_manager
        from app.tools.system_tools import SystemMonitor

        health = await health_registry.get_detailed_health(force_refresh=True)
        db_stat = db_manager.get_database_status()
        telemetry = SystemMonitor.get_metrics()

        # Sanitize database paths
        sanitized_db = {
            "healthy": db_stat.get("healthy"),
            "integrity_status": db_stat.get("integrity_status"),
            "journal_mode": db_stat.get("journal_mode"),
            "tables_count": db_stat.get("tables_count"),
            "total_records": db_stat.get("total_records"),
            "size_kb": round(db_stat.get("size_bytes", 0) / 1024, 1)
        }

        # Build export dictionary
        export_data = {
            "export_version": "0.9.0",
            "generated_at": datetime.now().isoformat(),
            "uptime_seconds": health.uptime_seconds,
            "overall_status": health.overall_status.value,
            "telemetry": {
                "cpu_percent": telemetry.get("cpu", {}).get("percent"),
                "ram_percent": telemetry.get("ram", {}).get("percent"),
                "disk_percent": telemetry.get("disk", {}).get("percent"),
                "os": telemetry.get("system", {}).get("os"),
                "machine": telemetry.get("system", {}).get("machine")
            },
            "database": sanitized_db,
            "subsystems": {
                k: {
                    "name": v.name,
                    "state": v.state.value,
                    "message": v.message,
                    "latency_ms": v.latency_ms,
                    "details": v.details
                }
                for k, v in health.subsystems.items()
            },
            "recent_errors": self.get_recent_errors(limit=25)
        }

        # Final pass redaction
        from app.tools.permission_manager import permission_manager
        sanitized_export = permission_manager.redact_sensitive_data(export_data)

        return sanitized_export

diagnostics_logger = DiagnosticsLogger()
