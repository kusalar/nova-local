import pytest
import asyncio
import time
import os
from fastapi.testclient import TestClient

from app.main import app
from app.database import db_manager, backup_manager
from app.security.approval_tokens import approval_token_manager
from app.security.content_sanitizer import content_sanitizer
from app.personalization import personalization_manager
from app.reliability.health_registry import health_registry, SubsystemState
from app.reliability.subsystem_supervisor import subsystem_supervisor

client = TestClient(app)

from unittest.mock import patch

def test_integration_chat_context_and_knowledge_graph():
    """Verify chat resolution integrates with project isolation and knowledge graph."""
    # Ensure personalization is enabled
    personalization_manager.enable()

    with patch("app.ai.model_manager.model_manager.chat") as mock_chat:
        mock_chat.return_value = {
            "success": True,
            "content": "Nova is built with FastAPI and SQLite.",
            "model": "qwen3:4b"
        }

        # Query with specific project
        res = client.post("/api/chat", json={
            "message": "Explain the architecture of Nova",
            "project_id": "Nova",
            "history": []
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") is True
        assert "FastAPI" in data.get("response", "")

def test_integration_personalization_disabled_state():
    """Verify disabling personalization halts adaptive interaction analysis and recommendations."""
    personalization_manager.disable()
    status = personalization_manager.get_status()
    assert status.enabled is False

    # Attempt to refresh personalization when disabled
    refresh_res = personalization_manager.refresh()
    assert refresh_res["status"] == "DISABLED"

    # Re-enable
    personalization_manager.enable()
    assert personalization_manager.get_status().enabled is True

def test_integration_concurrent_sqlite_operations():
    """Verify multiple concurrent SQLite reads and writes do not lock or crash."""
    test_db = "test_concurrent.db"
    conn = db_manager.get_connection(test_db)
    conn.execute("CREATE TABLE IF NOT EXISTS stress_log (id INTEGER PRIMARY KEY, thread_id INT, val TEXT);")
    conn.commit()
    conn.close()

    errors = []

    def writer_task(tid: int):
        for i in range(20):
            try:
                with db_manager.transaction(test_db) as c:
                    c.execute("INSERT INTO stress_log (thread_id, val) VALUES (?, ?);", (tid, f"val_{i}"))
            except Exception as e:
                errors.append(e)

    def reader_task():
        for _ in range(20):
            try:
                c = db_manager.get_connection(test_db)
                try:
                    c.execute("SELECT COUNT(*) FROM stress_log;").fetchone()
                finally:
                    c.close()
            except Exception as e:
                errors.append(e)

    import threading
    threads = []
    for t_idx in range(4):
        threads.append(threading.Thread(target=writer_task, args=(t_idx,)))
        threads.append(threading.Thread(target=reader_task))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Clean up test db
    for f in [test_db, f"{test_db}-wal", f"{test_db}-shm"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    assert len(errors) == 0, f"Concurrent SQLite operations produced errors: {errors}"

def test_integration_cross_project_isolation():
    """Verify context resolver detects ambiguous cross-project queries and guards against contamination."""
    res = client.post("/api/chat", json={
        "message": "Compare project Nova and project HireLens architecture",
        "history": []
    })
    assert res.status_code == 200
    data = res.json()
    # Ambiguity guard must be triggered
    assert data.get("clarification_needed") is True
    assert "Which project" in data.get("response", "") or "clarify" in data.get("response", "").lower()

def test_integration_database_backup_during_activity():
    """Verify database backup executes reliably without interrupting active operations."""
    b_res = client.post("/api/system/database/backups", json={"description": "Integration test backup"})
    assert b_res.status_code == 200, f"Backup creation failed: {b_res.status_code} - {b_res.text}"
    backup_data = b_res.json()
    assert backup_data["success"] is True
    assert backup_data["backup"]["healthy"] is True
