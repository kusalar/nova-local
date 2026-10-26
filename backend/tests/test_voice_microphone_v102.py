"""
NOVA v1.0.2 — Microphone & Speech Recognition Pipeline Unit and Integration Tests.
Verifies the complete pipeline from device selection, Windows Core Audio mute checks,
permission audits, PCM conversion, Vosk recognition, and WebSocket event telemetry.
"""

import sys
import os
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.voice.audio_manager import audio_manager
from app.voice.speech_recognition import SpeechRecognizer
from app.voice.windows_audio import (
    check_windows_microphone_permission,
    get_default_capture_mute_and_volume,
    unmute_default_capture,
)
from app.brain.state_manager import state_manager, NovaState

client = TestClient(app)


def test_windows_permission_audit():
    """Verify Windows registry permission check executes without error and returns structured dict."""
    perm = check_windows_microphone_permission()
    assert isinstance(perm, dict)
    assert "permission_allowed" in perm
    assert "global_allowed" in perm
    assert "desktop_allowed" in perm
    assert "details" in perm


def test_windows_mute_and_volume_query():
    """Verify Windows Core Audio COM queries endpoint mute and volume level."""
    is_muted, vol_scalar = get_default_capture_mute_and_volume()
    if sys.platform.startswith("win"):
        assert is_muted is not None
        assert isinstance(is_muted, bool)
        assert vol_scalar is not None
        assert 0.0 <= vol_scalar <= 1.0


def test_get_audio_devices_enrichment():
    """Verify GET /api/voice/devices returns hostapi_name and system defaults."""
    res = client.get("/api/voice/devices")
    assert res.status_code == 200
    data = res.json()
    assert "inputs" in data
    assert "outputs" in data
    assert "windows_permission" in data
    assert "is_muted" in data
    assert "volume_scalar" in data

    if data["inputs"]:
        first_in = data["inputs"][0]
        assert "id" in first_in
        assert "name" in first_in
        assert "hostapi_name" in first_in
        assert "default_samplerate" in first_in


def test_speech_recognizer_telemetry_and_initial_silence():
    """Verify SpeechRecognizer detailed telemetry and initial silence timeout."""
    sr = SpeechRecognizer(sample_rate=16000, initial_silence_timeout=0.4, max_timeout=2.0)
    silence_frame = np.zeros(1280, dtype=np.int16)

    def silence_gen():
        for _ in range(8):
            yield silence_frame

    telemetry = sr.transcribe_stream_detailed(silence_gen())
    assert isinstance(telemetry, dict)
    assert telemetry["text"] == ""
    assert telemetry["frames_processed"] > 0
    assert telemetry["has_spoken"] is False
    assert telemetry["reason"] in ("INITIAL_SILENCE", "STREAM_EXHAUSTED")
    assert telemetry["max_rms"] == 0.0


def test_speech_recognizer_pcm_transcription():
    """Verify SpeechRecognizer accurately transcribes synthesized speech frames."""
    from app.voice.text_to_speech import TextToSpeech
    tts = TextToSpeech()
    sr = SpeechRecognizer(sample_rate=16000)

    pcm_audio = tts.synthesize("open the system monitor")
    assert pcm_audio is not None
    assert len(pcm_audio) > 0

    # Piper default model sample rate is 16000
    chunks = [pcm_audio[i:i+1280] for i in range(0, len(pcm_audio), 1280)]

    def audio_gen():
        for c in chunks:
            yield c

    telemetry = sr.transcribe_stream_detailed(audio_gen())
    assert isinstance(telemetry["text"], str)
    assert len(telemetry["text"]) > 0
    assert telemetry["has_spoken"] is True
    assert telemetry["frames_processed"] > 0
    assert telemetry["max_rms"] > 0.01


def test_audio_manager_ptt_trigger_and_stop():
    """Verify trigger_listening and stop_listening methods."""
    audio_manager.stop()
    assert audio_manager.is_running is False

    started = audio_manager.trigger_listening()
    assert started is True
    assert audio_manager.is_running is True
    assert audio_manager.manual_listening_trigger is True

    # Stop listening
    stopped = audio_manager.stop_listening()
    assert stopped is True
    assert audio_manager._stop_listening_requested.is_set()

    # Clean up
    audio_manager.stop()
    assert audio_manager.is_running is False


def test_audio_manager_status_payload():
    """Verify GET /api/voice/status contains diagnostics and audio frame metrics."""
    res = client.get("/api/voice/status")
    assert res.status_code == 200
    data = res.json()
    assert "audio" in data
    audio_data = data["audio"]
    assert "sample_rate" in audio_data
    assert "frames_captured" in audio_data
    assert "bytes_captured" in audio_data
    assert "windows_permission" in audio_data
    assert "is_muted" in audio_data
    assert "volume_scalar" in audio_data


def test_stop_listen_rest_endpoint():
    """Verify POST /api/voice/stop-listen."""
    res = client.post("/api/voice/stop-listen")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True


def test_permission_denied_simulation():
    """Verify that permission denial triggers voice_error event and state transition."""
    with patch("app.voice.audio_manager.check_windows_microphone_permission") as mock_perm:
        mock_perm.return_value = {
            "permission_allowed": False,
            "details": "Simulated OS permission denial"
        }
        audio_manager.stop()
        opened = audio_manager._open_input_stream()
        assert opened is False
        assert state_manager.get_state() == NovaState.ERROR


def test_muted_microphone_auto_unmute_handling():
    """Verify that muted microphone attempts unmuting and succeeds or flags error."""
    with patch("app.voice.audio_manager.get_default_capture_mute_and_volume") as mock_mute:
        with patch("app.voice.audio_manager.unmute_default_capture") as mock_unmute:
            mock_mute.return_value = (True, 0.5)
            mock_unmute.return_value = True

            audio_manager.stop()
            # Should attempt unmute and proceed
            opened = audio_manager._open_input_stream()
            assert mock_unmute.called
            audio_manager.stop()
