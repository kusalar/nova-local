import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.brain.state_manager import state_manager, NovaState
from app.memory.sqlite_memory import memory_bank

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data
    assert "timestamp" in data

def test_system_status():
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "optimal"
    assert "telemetry" in data
    telemetry = data["telemetry"]
    assert "cpu" in telemetry
    assert "ram" in telemetry
    assert "disk" in telemetry
    assert "system" in telemetry
    assert isinstance(telemetry["cpu"]["percent"], (int, float))
    assert isinstance(telemetry["ram"]["percent"], (int, float))

def test_ai_status():
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    data = response.json()
    assert "online" in data
    assert "provider" in data
    assert "active_model" in data
    # Should not crash whether Ollama is running or offline!
    assert isinstance(data["online"], bool)

def test_chat_graceful_handling():
    # Chat should not raise 500 even if Ollama is offline
    payload = {
        "message": "Hello NOVA, system diagnostics status?",
        "history": [],
        "session_id": "test_session"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "state" in data
    # Message should be stored in memory
    messages = memory_bank.get_messages(session_id="test_session")
    assert len(messages) >= 1

def test_activity_feed():
    response = client.get("/api/activity/recent")
    assert response.status_code == 200
    data = response.json()
    assert "activities" in data
    assert len(data["activities"]) > 0

def test_clear_history():
    # Add a message to test session
    memory_bank.add_message(role="user", content="Temporary test", session_id="purge_test")
    assert len(memory_bank.get_messages(session_id="purge_test")) == 1
    
    # Call delete endpoint
    response = client.delete("/api/chat/history?session_id=purge_test")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert len(memory_bank.get_messages(session_id="purge_test")) == 0
