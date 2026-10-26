from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.tools.system_tools import SystemMonitor
from app.brain.state_manager import state_manager
from app.memory.sqlite_memory import memory_bank
from app.reliability.health_registry import health_registry
from app.reliability.diagnostics_logger import diagnostics_logger
from app.reliability.resource_coordinator import resource_coordinator
from app.database import db_manager, backup_manager

router = APIRouter(prefix="/system", tags=["System"])

class BackupCreateRequest(BaseModel):
    description: Optional[str] = Field(default=None, description="Optional label or note for this backup")

class BackupValidateRequest(BaseModel):
    backup_id: str = Field(..., description="ID of backup to validate")

class RestorePreviewRequest(BaseModel):
    backup_id: str = Field(..., description="ID of backup to preview restoration for")

class RestoreExecuteRequest(BaseModel):
    backup_id: str = Field(..., description="ID of backup to restore")
    confirmed: bool = Field(default=False, description="Must be true to authorize database replacement")

@router.get("/status")
async def get_system_status():
    """Retrieve real-time hardware telemetry and assistant health."""
    metrics = SystemMonitor.get_metrics()
    status_payload = state_manager.get_status_payload()
    memory_stats = memory_bank.get_stats()
    
    return {
        "status": "optimal",
        "telemetry": metrics,
        "assistant": status_payload,
        "memory": memory_stats
    }

# ==========================================
# NOVA v0.9 Reliability & Hardening Endpoints
# ==========================================

@router.get("/health/detailed")
async def get_detailed_health(force_refresh: bool = Query(False, description="Bypass cache and evaluate immediately")):
    """
    Subsystem Health Registry endpoint.
    Returns status (HEALTHY, DEGRADED, UNAVAILABLE, RECOVERING, ERROR) for all 10 subsystems.
    """
    try:
        summary = await health_registry.get_detailed_health(force_refresh=force_refresh)
        return summary.model_dump()
    except Exception as e:
        diagnostics_logger.record_error("system_health", str(e), exception=e)
        raise HTTPException(status_code=500, detail=f"Health evaluation error: {str(e)}")

@router.get("/diagnostics")
async def get_diagnostics():
    """Returns quick diagnostics summary across hardware, database, and background tasks."""
    telemetry = SystemMonitor.get_metrics()
    db_stat = db_manager.get_database_status()
    res_metrics = resource_coordinator.metrics
    errors = diagnostics_logger.get_recent_errors(limit=5)

    return {
        "telemetry": telemetry,
        "database": {
            "healthy": db_stat.get("healthy"),
            "integrity_status": db_stat.get("integrity_status"),
            "journal_mode": db_stat.get("journal_mode"),
            "tables_count": db_stat.get("tables_count"),
            "total_records": db_stat.get("total_records")
        },
        "concurrency": res_metrics,
        "recent_errors_count": len(errors)
    }

@router.get("/resources")
async def get_resources():
    """Returns CPU-aware concurrency limits and resource queue metrics."""
    telemetry = SystemMonitor.get_metrics()
    concurrency = resource_coordinator.metrics
    return {
        "cpu": telemetry.get("cpu"),
        "ram": telemetry.get("ram"),
        "concurrency_limits": concurrency
    }

@router.get("/errors/recent")
async def get_recent_errors(limit: int = Query(20, ge=1, le=100)):
    """Retrieve ring buffer of recent subsystem errors and recovery events."""
    return {
        "errors": diagnostics_logger.get_recent_errors(limit=limit)
    }

@router.get("/database/status")
async def get_database_status():
    """Retrieve SQLite integrity status, WAL mode, table record counts, and file sizes."""
    try:
        return db_manager.get_database_status()
    except Exception as e:
        diagnostics_logger.record_error("database", str(e), exception=e)
        raise HTTPException(status_code=500, detail=f"Failed to query database status: {str(e)}")

@router.get("/database/backups")
async def list_database_backups():
    """List all available database backups with metadata and SHA-256 hashes."""
    try:
        return backup_manager.list_backups()
    except Exception as e:
        diagnostics_logger.record_error("database_backup", str(e), exception=e)
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

@router.post("/database/backups")
async def create_database_backup(payload: Optional[BackupCreateRequest] = None):
    """Trigger manual online SQLite database backup."""
    try:
        desc = payload.description if payload else None
        meta = backup_manager.create_backup(trigger="manual", description=desc)
        return {"success": True, "backup": meta}
    except Exception as e:
        diagnostics_logger.record_error("database_backup", str(e), exception=e)
        raise HTTPException(status_code=500, detail=f"Backup creation failed: {str(e)}")

@router.post("/database/backups/validate")
async def validate_database_backup(payload: BackupValidateRequest):
    """Verify backup file existence, SQLite integrity, and SHA-256 checksum."""
    try:
        res = backup_manager.validate_backup(payload.backup_id)
        return res
    except Exception as e:
        diagnostics_logger.record_error("database_backup", str(e), exception=e)
        raise HTTPException(status_code=500, detail=f"Backup validation error: {str(e)}")

@router.post("/database/restore/preview")
async def preview_database_restore(payload: RestorePreviewRequest):
    """Generate dry-run comparison between current database state and backup."""
    try:
        preview = backup_manager.restore_preview(payload.backup_id)
        if not preview.get("can_restore"):
            raise HTTPException(status_code=400, detail=preview.get("error", "Cannot restore backup"))
        return preview
    except HTTPException:
        raise
    except Exception as e:
        diagnostics_logger.record_error("database_restore", str(e), exception=e)
        raise HTTPException(status_code=500, detail=f"Restore preview error: {str(e)}")

@router.post("/database/restore/execute")
async def execute_database_restore(payload: RestoreExecuteRequest):
    """
    Execute transactional database restore.
    Requires confirmed=True. A safety snapshot of current database is created automatically.
    """
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Restoration requires explicit confirmation (confirmed=true).")

    try:
        res = backup_manager.restore_backup(payload.backup_id, confirmed=True)
        return res
    except Exception as e:
        diagnostics_logger.record_error("database_restore", str(e), exception=e)
        raise HTTPException(status_code=500, detail=f"Database restore failed: {str(e)}")

@router.post("/diagnostics/export")
async def export_sanitized_diagnostics():
    """
    Generates sanitized diagnostic export.
    All user tokens, prompt texts, and private filesystem paths are redacted.
    """
    try:
        export_data = await diagnostics_logger.generate_diagnostic_export()
        return export_data
    except Exception as e:
        diagnostics_logger.record_error("diagnostics_export", str(e), exception=e)
        raise HTTPException(status_code=500, detail=f"Failed generating diagnostic export: {str(e)}")

# ==================== v1.0 ONBOARDING & SETTINGS ====================

class OnboardingCompleteRequest(BaseModel):
    selected_model: Optional[str] = None
    voice_enabled: bool = True
    wake_word_enabled: bool = False
    input_device: Optional[int] = None
    output_device: Optional[int] = None
    auto_extract_memory: bool = True
    personalization_enabled: bool = True

class SettingsImportRequest(BaseModel):
    preferences: Dict[str, Any] = Field(default_factory=dict)
    active_model: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    inference: Optional[Dict[str, Any]] = None

class SettingsUpdateRequest(BaseModel):
    active_model: Optional[str] = None
    temperature: Optional[float] = None
    num_ctx: Optional[int] = None
    num_predict: Optional[int] = None
    num_predict_voice: Optional[int] = None
    num_thread: Optional[int] = None
    thread_mode: Optional[str] = None
    keep_alive: Optional[str] = None
    max_history_turns: Optional[int] = None
    max_history_turns_voice: Optional[int] = None
    wake_word_enabled: Optional[bool] = None
    voice_mode: Optional[str] = None

@router.get("/onboarding/status")
async def get_onboarding_status():
    """Check first-run onboarding state, hardware compatibility, and service readiness."""
    import sys
    import psutil
    from app.config import settings
    from app.personalization.preference_engine import preference_engine
    from app.ai.model_manager import model_manager
    from app.voice.audio_manager import audio_manager

    pref = preference_engine.get_preference("onboarding_completed")
    is_first_run = pref is None or pref.value != "true"

    ai_status = await model_manager.get_status()
    audio_info = audio_manager.get_audio_devices() if hasattr(audio_manager, "get_audio_devices") else {"inputs": [], "outputs": []}
    voice_status = audio_manager.get_status()

    mem = psutil.virtual_memory()
    total_ram = round(mem.total / (1024**3), 1)
    avail_ram = round(mem.available / (1024**3), 1)
    cpu_logical = psutil.cpu_count(logical=True) or 4
    cpu_physical = psutil.cpu_count(logical=False) or 2
    models_list = ai_status.get("available_models", [])

    return {
        "is_first_run": is_first_run,
        "version": settings.VERSION,
        "hardware": {
            "platform": sys.platform,
            "cpu_cores": cpu_logical,
            "cpu_count": cpu_logical,
            "physical_cores": cpu_physical,
            "total_ram_gb": total_ram,
            "ram_total_gb": total_ram,
            "available_ram_gb": avail_ram,
            "ram_available_gb": avail_ram,
            "compatible": total_ram >= 7.0,
            "is_ram_adequate": total_ram >= 7.0,
            "target_specs": "Intel Core i3-1115G4 / 12 GB RAM / Windows 11"
        },
        "ollama": {
            "online": ai_status.get("online", False),
            "endpoint": settings.OLLAMA_BASE_URL,
            "available_models": models_list,
            "models": models_list,
            "has_models": len(models_list) > 0,
            "active_model": ai_status.get("active_model", settings.DEFAULT_MODEL)
        },
        "voice": {
            "enabled": settings.VOICE_ENABLED,
            "wake_phrase": voice_status.get("wake_word", {}).get("wake_phrase", "Hey Jarvis"),
            "is_custom_wake_word": voice_status.get("wake_word", {}).get("is_custom", False),
            "input_devices": audio_info.get("inputs", []),
            "output_devices": audio_info.get("outputs", []),
            "tts_available": voice_status.get("tts", {}).get("initialized", False)
        },
        "privacy": {
            "local_only": True,
            "single_use_tokens": True,
            "redaction_active": True
        },
        "database": {
            "path": settings.DATABASE_PATH,
            "status": "ready"
        }
    }

@router.post("/onboarding/complete")
async def complete_onboarding(payload: OnboardingCompleteRequest):
    """Saves first-run setup choices and marks onboarding as completed."""
    from app.personalization.preference_engine import preference_engine
    from app.personalization.personalization_schemas import PreferenceCreate, PreferenceCategory
    from app.ai.model_manager import model_manager
    from app.voice.audio_manager import audio_manager

    if payload.selected_model:
        model_manager.set_active_model(payload.selected_model)

    audio_manager.set_wake_word_enabled(payload.wake_word_enabled)
    if payload.input_device is not None or payload.output_device is not None:
        audio_manager.set_audio_devices(payload.input_device, payload.output_device)

    preference_engine.set_preference(PreferenceCreate(
        category=PreferenceCategory.GENERAL,
        key="onboarding_completed",
        value="true",
        is_explicit=True,
        source="onboarding_wizard"
    ))

    if payload.selected_model:
        preference_engine.set_preference(PreferenceCreate(
            category=PreferenceCategory.GENERAL,
            key="preferred_model",
            value=payload.selected_model,
            is_explicit=True,
            source="onboarding_wizard"
        ))

    return {
        "success": True,
        "message": "NOVA v1.0 initial setup completed successfully."
    }

@router.get("/settings")
async def get_system_settings():
    """Retrieve unified configuration across all NOVA v1.0 subsystems."""
    from app.config import settings
    from app.voice.audio_manager import audio_manager
    from app.ai.model_manager import model_manager
    from app.ai.inference_config import inference_config

    v_status = audio_manager.get_status()
    devices = audio_manager.get_audio_devices() if hasattr(audio_manager, "get_audio_devices") else {"inputs": [], "outputs": []}
    ai_status = await model_manager.get_status()

    return {
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "ai": {
            "endpoint": settings.OLLAMA_BASE_URL,
            "ollama_endpoint": settings.OLLAMA_BASE_URL,
            "active_model": ai_status.get("active_model", settings.DEFAULT_MODEL),
            "available_models": ai_status.get("available_models", []),
            "fallback_models": settings.FALLBACK_MODELS,
            "inference": inference_config.snapshot(),
        },
        "voice": {
            "enabled": settings.VOICE_ENABLED,
            "wake_word_enabled": audio_manager.wake_word_enabled,
            "wake_phrase": v_status.get("wake_word", {}).get("wake_phrase", "Hey Jarvis"),
            "is_custom_wake_word": v_status.get("wake_word", {}).get("is_custom", False),
            "wake_word_threshold": v_status.get("wake_word", {}).get("threshold", 0.5),
            "input_device": audio_manager.input_device,
            "output_device": audio_manager.output_device,
            "speech_rate": v_status.get("tts", {}).get("speech_rate", 1.05),
            "tts_volume": v_status.get("tts", {}).get("volume", 1.0),
            "devices": devices
        },
        "memory": {
            "embedding_model": settings.MEMORY_EMBEDDING_MODEL,
            "similarity_threshold": settings.MEMORY_SIMILARITY_THRESHOLD,
            "auto_extract": settings.AUTO_EXTRACT_MEMORY,
            "database_path": settings.DATABASE_PATH
        },
        "database": {
            "backup_dir": settings.BACKUP_DIR,
            "backup_retention_max": settings.BACKUP_RETENTION_MAX
        }
    }

@router.post("/settings")
async def update_system_settings(payload: SettingsUpdateRequest):
    """Update inference profile and voice mode through the unified settings API."""
    from app.ai.model_manager import model_manager
    from app.ai.inference_config import inference_config
    from app.voice.audio_manager import audio_manager

    if payload.active_model:
        model_manager.set_active_model(payload.active_model)

    inf = inference_config.update(
        temperature=payload.temperature,
        num_ctx=payload.num_ctx,
        num_predict=payload.num_predict,
        num_predict_voice=payload.num_predict_voice,
        num_thread=payload.num_thread,
        thread_mode=payload.thread_mode,
        keep_alive=payload.keep_alive,
        max_history_turns=payload.max_history_turns,
        max_history_turns_voice=payload.max_history_turns_voice,
    )

    if payload.voice_mode is not None:
        audio_manager.set_wake_word_enabled(payload.voice_mode.strip().lower() == "wake_word")
    elif payload.wake_word_enabled is not None:
        audio_manager.set_wake_word_enabled(payload.wake_word_enabled)

    return {
        "success": True,
        "inference": inf,
        "active_model": model_manager.active_model,
        "voice_mode": "wake_word" if audio_manager.wake_word_enabled else "push_to_talk",
        "wake_word_enabled": audio_manager.wake_word_enabled,
    }

@router.get("/settings/export")
async def export_settings():
    """Export clean, non-secret user preferences and operational configuration as JSON."""
    from app.personalization.preference_engine import preference_engine
    from app.config import settings
    from app.ai.model_manager import model_manager
    from app.voice.audio_manager import audio_manager

    ai_status = await model_manager.get_status()
    v_status = audio_manager.get_status()
    all_prefs = preference_engine.list_preferences()

    clean_prefs = {
        p.key: p.value for p in all_prefs if not any(k in p.key.lower() for k in ["token", "secret", "password", "key"])
    }

    return {
        "export_type": "nova_configuration",
        "version": settings.VERSION,
        "app_version": settings.VERSION,
        "exported_at": str(datetime.now().isoformat()),
        "active_model": ai_status.get("active_model", settings.DEFAULT_MODEL),
        "voice_settings": {
            "wake_word_enabled": audio_manager.wake_word_enabled,
            "threshold": v_status.get("wake_word", {}).get("threshold", 0.5),
            "speech_rate": v_status.get("tts", {}).get("speech_rate", 1.05),
            "tts_volume": v_status.get("tts", {}).get("volume", 1.0)
        },
        "preferences": clean_prefs
    }

@router.post("/settings/import")
async def import_settings(payload: SettingsImportRequest):
    """Import non-secret user preferences and update active configuration."""
    from app.personalization.preference_engine import preference_engine
    from app.personalization.personalization_schemas import PreferenceCreate, PreferenceCategory
    from app.ai.model_manager import model_manager
    from app.voice.audio_manager import audio_manager

    imported_count = 0
    if payload.active_model:
        model_manager.set_active_model(payload.active_model)

    if payload.inference:
        from app.ai.inference_config import inference_config
        inference_config.update(**payload.inference)

    if payload.voice_settings:
        if "wake_word_enabled" in payload.voice_settings:
            audio_manager.set_wake_word_enabled(bool(payload.voice_settings["wake_word_enabled"]))
        if "voice_mode" in payload.voice_settings:
            audio_manager.set_wake_word_enabled(str(payload.voice_settings["voice_mode"]).lower() == "wake_word")
        if "tts_speech_rate" in payload.voice_settings:
            audio_manager.set_speech_rate(float(payload.voice_settings["tts_speech_rate"]))

    for k, v in payload.preferences.items():
        # Guard against importing secret keys
        if any(sec in k.lower() for sec in ["secret", "password", "token"]):
            continue
        preference_engine.set_preference(PreferenceCreate(
            category=PreferenceCategory.GENERAL,
            key=k,
            value=str(v),
            is_explicit=True,
            source="imported_config"
        ))
        imported_count += 1

    return {
        "success": True,
        "imported_preferences_count": imported_count,
        "message": f"Successfully imported {imported_count} preferences."
    }

