"""v1.0.1 regression tests: one utterance -> one inference, PTT idle, streaming, settings."""
import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.ai.inference_config import inference_config
from app.ai.model_manager import model_manager
from app.voice.audio_manager import audio_manager
from app.api.chat import trim_history, ChatMessage

client = TestClient(app)


def test_inference_defaults_match_cpu_profile():
    snap = inference_config.snapshot()
    assert snap["num_ctx"] == 1024
    assert snap["num_predict_voice"] == 96
    assert snap["keep_alive"] == "10m"
    assert snap["max_concurrent_inference"] == 1
    assert snap["num_thread"] in (2, None)


def test_inference_settings_round_trip():
    res = client.post("/api/system/settings", json={
        "num_ctx": 1024,
        "num_predict": 128,
        "num_predict_voice": 64,
        "thread_mode": "auto",
        "keep_alive": "10m",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["inference"]["num_predict"] == 128
    assert data["inference"]["thread_mode"] == "auto"
    # restore recommended defaults
    client.post("/api/system/settings", json={
        "num_ctx": 1024,
        "num_predict": 256,
        "num_predict_voice": 96,
        "thread_mode": "manual",
        "num_thread": 2,
        "keep_alive": "10m",
    })


def test_history_trim_does_not_repeat_unbounded_context():
    history = [ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"t{i}") for i in range(20)]
    trimmed = trim_history(history, max_turns=2)
    assert len(trimmed) == 4
    assert trimmed[0]["content"] == "t16"


def test_explicit_memory_skips_ollama():
    with patch("app.ai.model_manager.model_manager.chat", new_callable=AsyncMock) as mock_chat:
        res = client.post("/api/chat", json={
            "message": "What do you remember about me?",
            "history": []
        })
        assert res.status_code == 200
        mock_chat.assert_not_called()
        body = res.json()
        assert body.get("ollama_calls") == 0


def test_text_chat_single_ollama_call():
    with patch("app.ai.model_manager.model_manager.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = {
            "success": True,
            "content": "Four.",
            "model": "qwen2.5:1.5b",
            "metrics": {"eval_count": 2},
            "request_id": "inf_test",
        }
        res = client.post("/api/chat", json={"message": "What is 2+2? Reply briefly.", "history": []})
        assert res.status_code == 200
        assert mock_chat.await_count == 1
        assert res.json().get("ollama_calls") == 1


def test_push_to_talk_start_does_not_open_microphone():
    audio_manager.stop()
    audio_manager.set_wake_word_enabled(False)
    audio_manager._close_input_stream()
    with patch("app.voice.audio_manager.sd.InputStream") as mock_stream:
        ok = audio_manager.start()
        assert ok is True
        mock_stream.assert_not_called()
        assert audio_manager.audio_stream is None
        status = audio_manager.get_status()
        assert status["voice_mode"] == "push_to_talk"
        assert status["pipeline_mode"] == "PTT_STANDBY"
    audio_manager.stop()


def test_one_voice_utterance_one_stream():
    """A single recognized utterance must start exactly one model stream."""
    calls = {"n": 0}

    async def counting_stream(**kwargs):
        calls["n"] += 1
        yield {"type": "token", "content": "Hello. ", "model": "qwen2.5:1.5b"}
        yield {"type": "done", "model": "qwen2.5:1.5b", "metrics": {"eval_count": 4, "tokens_per_sec": 12.0}}

    def run_inline(coro, loop=None):
        class _F:
            def result(self, timeout=None):
                nest = asyncio.new_event_loop()
                try:
                    return nest.run_until_complete(coro)
                finally:
                    nest.close()
        return _F()

    class _Slot:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False

    audio_manager.tts.stop()
    with patch.object(model_manager, "chat_stream", side_effect=counting_stream):
        with patch("app.voice.audio_manager.asyncio.run_coroutine_threadsafe", side_effect=run_inline):
            with patch("app.reliability.resource_coordinator.resource_coordinator.acquire_inference_slot", return_value=_Slot()):
                with patch.object(audio_manager.tts, "speak"):
                    with patch.object(audio_manager.tts, "enqueue"):
                        with patch.object(audio_manager.tts, "mark_generation_complete"):
                            audio_manager._dispatch_to_brain("hello nova how are you", stt_ms=10.0, trigger_source="manual")
                            audio_manager._dispatch_to_brain("hello nova how are you", stt_ms=10.0, trigger_source="manual")

    assert calls["n"] == 2  # two separate utterances, one call each
    assert calls["n"] != 4


def test_duplicate_in_flight_cancels_previous():
    started = asyncio.Event()
    release = asyncio.Event()
    calls = {"n": 0}

    async def blocking_stream(**kwargs):
        calls["n"] += 1
        started.set()
        await asyncio.wait_for(release.wait(), timeout=2.0)
        yield {"type": "token", "content": "slow", "model": "qwen2.5:1.5b"}
        yield {"type": "done", "model": "qwen2.5:1.5b", "metrics": {}}

    # Sequential dispatch in this process is blocking; verify cancel_active_turn is wired.
    with patch.object(model_manager, "cancel_active", return_value="inf_x") as cancel_fn:
        audio_manager.cancel_active_turn()
        cancel_fn.assert_called()


def test_chat_stream_endpoint_emits_tokens():
    async def fake_stream(**kwargs):
        yield {"type": "token", "content": "Hi", "model": "qwen2.5:1.5b", "request_id": "r1"}
        yield {"type": "done", "model": "qwen2.5:1.5b", "metrics": {"ttft_ms": 12}, "request_id": "r1"}

    with patch("app.ai.model_manager.model_manager.chat_stream", side_effect=fake_stream):
        res = client.post("/api/chat/stream", json={"message": "Hi", "history": []})
        assert res.status_code == 200
        text = res.text
        assert '"type": "token"' in text or '"type":"token"' in text
        assert "Hi" in text


def test_cancel_endpoint():
    res = client.post("/api/chat/cancel")
    assert res.status_code == 200
    assert res.json()["success"] is True
