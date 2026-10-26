import os
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.voice.wake_word import WakeWordEngine
from app.voice.speech_recognition import SpeechRecognizer
from app.voice.text_to_speech import TextToSpeech
from app.voice.audio_manager import audio_manager
from app.brain.state_manager import state_manager, NovaState

client = TestClient(app)

def test_wake_word_initialization():
    """Verify openWakeWord initializes properly with verified model."""
    engine = WakeWordEngine()
    assert engine.is_initialized is True
    assert engine.oww_model is not None
    status = engine.get_status()
    assert "active_model_key" in status
    assert "threshold" in status
    assert status["initialized"] is True

def test_wake_word_predict_dummy_audio():
    """Verify wake word engine processes 16kHz audio buffers without error."""
    engine = WakeWordEngine()
    dummy_audio = np.zeros(1280, dtype=np.int16)
    preds = engine.predict(dummy_audio)
    assert isinstance(preds, dict)
    # Zero silence should not trigger wake word
    assert engine.is_wake_word_triggered(dummy_audio) is False

def test_speech_recognizer_initialization():
    """Verify Vosk initializes with offline language model."""
    recognizer = SpeechRecognizer(sample_rate=16000)
    assert recognizer.is_initialized is True
    assert recognizer.model is not None
    status = recognizer.get_status()
    assert status["engine"] == "Vosk (Local Offline)"

def test_speech_recognizer_empty_transcription():
    """Verify silence / empty audio returns empty string gracefully."""
    recognizer = SpeechRecognizer(sample_rate=16000)
    silence_frame = np.zeros(1600, dtype=np.int16)
    
    def dummy_stream():
        for _ in range(3):
            yield silence_frame

    text = recognizer.transcribe_audio_stream(dummy_stream())
    assert text == ""

def test_tts_initialization():
    """Verify Piper TTS initializes with local ONNX model."""
    tts = TextToSpeech()
    assert tts.is_initialized is True
    assert tts.voice is not None
    status = tts.get_status()
    assert status["engine"] == "Piper TTS (Local Offline)"

def test_tts_synthesize_array():
    """Verify text generates valid PCM audio numpy array."""
    tts = TextToSpeech()
    audio = tts.synthesize("NOVA online.")
    assert audio is not None
    assert isinstance(audio, np.ndarray)
    assert len(audio) > 0

def test_tts_interrupted_playback():
    """Verify TTS stop() interrupts active playback state."""
    tts = TextToSpeech()
    # Trigger non-blocking speech
    tts.speak("Long testing utterance for interruption verification in NOVA assistant.", block=False)
    # Interrupt immediately
    tts.stop()
    assert tts.is_speaking is False

def test_voice_rest_status_endpoint():
    """Verify GET /api/voice/status returns full diagnostic payload."""
    res = client.get("/api/voice/status")
    assert res.status_code == 200
    data = res.json()
    assert "wake_word" in data
    assert "speech_recognition" in data
    assert "tts" in data
    assert "audio" in data

def test_voice_rest_devices_endpoint():
    """Verify GET /api/voice/devices returns available physical audio devices."""
    res = client.get("/api/voice/devices")
    assert res.status_code == 200
    data = res.json()
    assert "inputs" in data
    assert "outputs" in data

def test_voice_settings_update():
    """Verify POST /api/voice/settings updates parameters."""
    payload = {
        "wake_word_threshold": 0.55,
        "tts_speech_rate": 1.1,
        "tts_volume": 0.95
    }
    res = client.post("/api/voice/settings", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

def test_voice_trigger_listen():
    """Verify POST /api/voice/trigger-listen initiates listening state."""
    res = client.post("/api/voice/trigger-listen")
    assert res.status_code == 200
    assert res.json()["success"] is True

def test_audio_manager_mocked_microphone_error():
    """Verify audio manager handles microphone unavailability gracefully without crashing."""
    mgr = audio_manager
    mgr.stop()
    mgr.wake_word_enabled = True
    with patch("app.voice.audio_manager.sd.InputStream", side_effect=RuntimeError("Microphone device not found")):
        success = mgr.start()
        # Should not crash and should return False
        assert success is False
        assert mgr.is_running is False
    # Restore clean state
    mgr.wake_word_enabled = False
    mgr.stop()

def test_existing_chat_endpoint_compatibility():
    """Verify existing text chat still works cleanly with voice pipeline loaded."""
    res = client.post("/api/chat", json={"message": "System status check", "history": []})
    assert res.status_code == 200
    assert "response" in res.json()
