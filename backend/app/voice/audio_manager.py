import time
import sys
import queue
import asyncio
import logging
import threading
import numpy as np
import scipy.signal
import sounddevice as sd
from typing import Optional, Dict, Any, List, Set, Tuple
from datetime import datetime

from app.config import settings
from app.voice.wake_word import WakeWordEngine
from app.voice.speech_recognition import SpeechRecognizer
from app.voice.text_to_speech import TextToSpeech
from app.voice.windows_audio import (
    check_windows_microphone_permission,
    get_default_capture_mute_and_volume,
    unmute_default_capture,
)
from app.brain.state_manager import state_manager, NovaState
from app.ai.model_manager import model_manager
from app.ai.inference_config import inference_config
from app.ai.inference_tracer import InferenceTrace, new_request_id, store_trace
from app.memory.sqlite_memory import memory_bank
from app.memory.memory_manager import memory_manager
from app.tools.system_tools import SystemMonitor
from app.tools.task_planner import task_planner
from app.tools.execution_manager import execution_manager
from app.tools.execution_logger import execution_logger
from app.tools.tool_schemas import TaskStatus
from app.vision.vision_manager import vision_manager
from app.vision.vision_schemas import VisualAnalysisRequest, CaptureTarget
from app.agents.agent_orchestrator import agent_orchestrator

logger = logging.getLogger("nova.voice.audio_manager")

class AudioManager:
    """
    Central audio orchestration engine for NOVA v0.2.
    Coordinates microphone capture, wake-word detection, speech recognition,
    speech synthesis, assistant state machine, and WebSocket telemetry.
    """

    def __init__(self):
        self.wake_word_engine = WakeWordEngine()
        self.speech_recognizer = SpeechRecognizer(sample_rate=settings.AUDIO_SAMPLE_RATE)
        self.tts = TextToSpeech()
        
        self.sample_rate = settings.AUDIO_SAMPLE_RATE
        self.frame_size = 1280  # 80ms at 16kHz, native for openWakeWord
        self.input_device = settings.AUDIO_INPUT_DEVICE
        self.output_device = settings.AUDIO_OUTPUT_DEVICE
        
        # Audio stream and threading
        self.audio_stream: Optional[sd.InputStream] = None
        self.audio_queue = queue.Queue(maxsize=100)
        self.is_running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # Voice pipeline state: "WAKE_WORD", "PTT_STANDBY", "LISTENING_SPEECH", "THINKING", "SPEAKING", "PAUSED"
        self.pipeline_mode = "PTT_STANDBY"
        self.wake_word_enabled = False
        self.manual_listening_trigger = False
        self._utterance_lock = threading.Lock()
        self._active_utterance_id: Optional[str] = None
        self._cancel_requested = threading.Event()
        self._stop_listening_requested = threading.Event()
        self._tts_text_buffer = ""
        self._listen_started_at = 0.0
        self._capture_opened_at = 0.0
        self._wake_detected_at = 0.0

        # v1.0.2 Audio stream diagnostics & resampling
        self._frames_captured_count = 0
        self._bytes_captured_count = 0
        self._selected_device_name = "Default"
        self._selected_device_index: Optional[int] = None
        self._needs_resampling = False
        self._resample_native_rate = 16000
        self._resample_native_channels = 1
        self._last_stt_telemetry: Dict[str, Any] = {}
        
        # Active WebSocket subscribers
        self._ws_subscribers: Set[Any] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # v0.4 Voice Task Approvals
        self.pending_voice_task_id: Optional[str] = None
        self.pending_voice_task_expiry: float = 0.0

        # v0.6 Voice Workflow Approvals
        self.pending_voice_workflow_id: Optional[str] = None
        self.pending_voice_workflow_step_id: Optional[int] = None
        self.pending_voice_workflow_expiry: float = 0.0

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def add_ws_subscriber(self, ws: Any):
        self._ws_subscribers.add(ws)

    def remove_ws_subscriber(self, ws: Any):
        self._ws_subscribers.discard(ws)

    def broadcast_ws_event(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """Thread-safe event broadcast to all connected WebSocket clients."""
        payload = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        if not self._ws_subscribers or not self._loop:
            return

        async def _send():
            disconnected = []
            for ws in list(self._ws_subscribers):
                try:
                    await ws.send_json(payload)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                self._ws_subscribers.discard(ws)

        try:
            asyncio.run_coroutine_threadsafe(_send(), self._loop)
        except Exception as e:
            logger.debug(f"Could not broadcast WS event: {e}")

    def get_audio_devices(self) -> Dict[str, Any]:
        """Query available physical input and output sound devices with host API names and Windows privacy info."""
        input_devs = []
        output_devs = []
        default_in = None
        default_out = None
        try:
            defaults = sd.default.device
            default_in = defaults[0] if defaults and len(defaults) > 0 else None
            default_out = defaults[1] if defaults and len(defaults) > 1 else None
        except Exception:
            pass

        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
            for idx, d in enumerate(devices):
                api_id = d.get("hostapi", 0)
                api_name = hostapis[api_id].get("name", f"API {api_id}") if api_id < len(hostapis) else f"API {api_id}"
                dev_info = {
                    "id": idx,
                    "name": d.get("name", "Unknown"),
                    "hostapi": api_id,
                    "hostapi_name": api_name,
                    "max_inputs": d.get("max_input_channels", 0),
                    "max_outputs": d.get("max_output_channels", 0),
                    "default_samplerate": d.get("default_samplerate"),
                    "is_default_input": idx == default_in,
                    "is_default_output": idx == default_out,
                }
                if dev_info["max_inputs"] > 0:
                    input_devs.append(dev_info)
                if dev_info["max_outputs"] > 0:
                    output_devs.append(dev_info)
        except Exception as e:
            logger.error(f"[Audio] Error querying audio devices: {e}")

        perm_info = check_windows_microphone_permission()
        is_muted, vol_scalar = get_default_capture_mute_and_volume()

        return {
            "inputs": input_devs,
            "outputs": output_devs,
            "default_input": default_in,
            "default_output": default_out,
            "windows_permission": perm_info,
            "is_muted": is_muted,
            "volume_scalar": vol_scalar,
        }

    def _audio_callback(self, indata, frames, time_info, status):
        """Sounddevice stream callback running in audio thread with frame counting and optional downmix/resample."""
        if status:
            logger.warning(f"[Audio Boundary] Stream status warning: {status}")
        if self.is_running and not self._stop_event.is_set():
            self._frames_captured_count += 1
            self._bytes_captured_count += indata.nbytes

            # Downmix multi-channel to mono
            if indata.ndim > 1 and indata.shape[1] > 1:
                mono = indata.mean(axis=1).astype(np.int16)
            elif indata.ndim > 1:
                mono = indata[:, 0].copy()
            else:
                mono = indata.copy()

            # Resample if device native rate != target 16000
            if getattr(self, "_needs_resampling", False) and getattr(self, "_resample_native_rate", 16000) != self.sample_rate:
                try:
                    target_len = int(len(mono) * self.sample_rate / self._resample_native_rate)
                    frame_16k = scipy.signal.resample(mono, target_len).astype(np.int16)
                except Exception:
                    frame_16k = mono
            else:
                frame_16k = mono

            try:
                self.audio_queue.put_nowait(frame_16k)
            except queue.Full:
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(frame_16k)
                except Exception:
                    pass

    def start(self) -> bool:
        """Launch background audio processing loop."""
        with self._lock:
            if self.is_running:
                logger.info("AudioManager is already running.")
                return True

            self._stop_event.clear()
            self.manual_listening_trigger = False
            # Drain queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except Exception:
                    break

            try:
                self.is_running = True
                self._stop_event.clear()
                if self.wake_word_enabled:
                    opened = self._open_input_stream()
                    if not opened:
                        self.is_running = False
                        return False
                    self.pipeline_mode = "WAKE_WORD"
                else:
                    self.pipeline_mode = "PTT_STANDBY"

                self._worker_thread = threading.Thread(target=self._processing_loop, daemon=True)
                self._worker_thread.start()

                logger.info(
                    "AudioManager started (mode=%s, wake_word=%s).",
                    self.pipeline_mode,
                    self.wake_word_enabled,
                )
                self.broadcast_ws_event("voice_status", {
                    "running": True,
                    "mode": self.pipeline_mode,
                    "wake_word_enabled": self.wake_word_enabled,
                })
                return True

            except Exception as e:
                self.is_running = False
                err_msg = f"Failed to open microphone: {str(e)}"
                logger.error(err_msg)
                self.broadcast_ws_event("voice_error", {"message": err_msg})
                state_manager.set_state(NovaState.ERROR, "MICROPHONE ERROR")
                return False

    def stop(self) -> bool:
        """Gracefully stop microphone capture and background loop."""
        with self._lock:
            if not self.is_running:
                return True

            self.is_running = False
            self._stop_event.set()
            self.manual_listening_trigger = False
            
            # Stop TTS playback if any
            self.tts.stop()

            self._close_input_stream()

            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=2.0)
            self._worker_thread = None

            state_manager.set_state(NovaState.IDLE, "NOVA SYSTEM ONLINE")
            self.broadcast_ws_event("voice_status", {"running": False, "mode": "STOPPED"})
            logger.info("AudioManager stopped successfully.")
            return True

    def _find_best_input_device(self) -> int:
        """
        Dynamically probe candidate input audio devices to find the one with active acoustic signal.
        Filters out virtual mappers (e.g. 'Microsoft Sound Mapper') and probes physical microphones.
        """
        try:
            devs = sd.query_devices()
            input_dev_indices = [idx for idx, d in enumerate(devs) if d.get("max_input_channels", 0) > 0]
            if not input_dev_indices:
                return 0

            # 1. Filter out virtual mappers
            def is_virtual(name: str) -> bool:
                low = name.lower()
                return "mapper" in low or "primary sound" in low

            candidates = [idx for idx in input_dev_indices if not is_virtual(devs[idx].get("name", ""))]
            if not candidates:
                candidates = input_dev_indices

            # Sort candidates: prefer physical microphones / arrays, deprioritize speakers / stereo mix
            def score_name(idx: int) -> int:
                low = devs[idx].get("name", "").lower()
                score = 0
                if "microphone" in low or "mic" in low or "array" in low:
                    score += 10
                if "speaker" in low or "stereo mix" in low:
                    score -= 10
                return score

            candidates.sort(key=score_name, reverse=True)

            # Probe candidates for acoustic liveness (80ms each)
            best_dev = None
            best_rms = 0.0

            for c in candidates:
                d = devs[c]
                sr = int(d.get("default_samplerate", 16000))
                ch = min(2, d.get("max_input_channels", 1))
                try:
                    rec = sd.rec(int(sr * 0.08), samplerate=sr, channels=ch, dtype="int16", device=c)
                    sd.wait()
                    rms = float(np.sqrt(np.mean(rec.astype(float) ** 2)))
                    if rms > 5.0 and rms > best_rms:
                        best_rms = rms
                        best_dev = c
                        if rms > 20.0:
                            break
                except Exception:
                    continue

            if best_dev is not None:
                logger.info(
                    "[Audio Boundary] Auto-detected active acoustic device [%d] '%s' (RMS=%.2f).",
                    best_dev, devs[best_dev].get("name", ""), best_rms
                )
                return best_dev

            # Fallback to system default or first candidate
            try:
                defaults = sd.default.device
                if defaults and len(defaults) > 0 and defaults[0] in input_dev_indices and not is_virtual(devs[defaults[0]].get("name", "")):
                    return defaults[0]
            except Exception:
                pass

            return candidates[0] if candidates else input_dev_indices[0]
        except Exception as e:
            logger.warning(f"[Audio Boundary] Error finding best input device: {e}")
            return 0

    def _open_input_stream(self) -> bool:
        """Open the microphone capture stream with permission, mute check, and adaptive resampling."""
        if self.audio_stream is not None:
            return True

        # 1. Check Windows Privacy Permissions
        perm = check_windows_microphone_permission()
        if not perm.get("permission_allowed", True):
            err_msg = perm.get("details", "Microphone permission is denied in Windows Settings.")
            logger.error(f"[Audio Boundary] Microphone permission denied: {err_msg}")
            self.broadcast_ws_event("voice_error", {
                "code": "PERMISSION_DENIED",
                "message": err_msg
            })
            state_manager.set_state(NovaState.ERROR, "MIC PERMISSION DENIED")
            return False

        # 2. Check Windows System Mute Status
        is_muted, vol = get_default_capture_mute_and_volume()
        if is_muted:
            logger.warning("[Audio Boundary] Default capture device is MUTED in Windows OS. Attempting automatic unmuting...")
            unmuted = unmute_default_capture()
            if unmuted:
                logger.info("[Audio Boundary] Successfully unmuted Windows microphone capture endpoint.")
                self.broadcast_ws_event("voice_notice", {
                    "message": "Microphone was muted in Windows and was automatically unmuted."
                })
            else:
                err_msg = "Microphone is muted in Windows sound settings. Please unmute your microphone in the Windows taskbar/Settings."
                logger.error(f"[Audio Boundary] Hardware mic is muted: {err_msg}")
                self.broadcast_ws_event("voice_error", {
                    "code": "MICROPHONE_MUTED",
                    "message": err_msg
                })
                state_manager.set_state(NovaState.ERROR, "MICROPHONE MUTED")
                return False

        try:
            devs = sd.query_devices()
            input_dev_indices = [idx for idx, d in enumerate(devs) if d.get("max_input_channels", 0) > 0]
            if not input_dev_indices:
                err_msg = "No audio input devices detected on this system."
                logger.error(f"[Audio Boundary] {err_msg}")
                self.broadcast_ws_event("voice_error", {
                    "code": "NO_MICROPHONE_DETECTED",
                    "message": err_msg
                })
                state_manager.set_state(NovaState.ERROR, "NO MICROPHONE")
                return False

            target_dev = self.input_device
            if target_dev is None or target_dev >= len(devs) or devs[target_dev].get("max_input_channels", 0) <= 0:
                target_dev = self._find_best_input_device()

            self._selected_device_index = target_dev
            target_info = devs[target_dev] if target_dev is not None and target_dev < len(devs) else {}
            self._selected_device_name = target_info.get("name", "Unknown Input Device")

            # Check if 16kHz 1-channel is supported natively
            needs_resampling = False
            native_rate = self.sample_rate
            native_channels = 1

            try:
                sd.check_input_settings(
                    device=target_dev,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="int16"
                )
            except Exception as e_check:
                logger.info(f"[Audio Boundary] Direct 16kHz not supported on device [{target_dev}] ({e_check}). Falling back to native device samplerate.")
                native_rate = int(target_info.get("default_samplerate", 44100))
                native_channels = min(2, max(1, target_info.get("max_input_channels", 1)))
                needs_resampling = True

            self._needs_resampling = needs_resampling
            self._resample_native_rate = native_rate
            self._resample_native_channels = native_channels

            blocksize = int(native_rate * 0.08)  # 80ms block
            self.audio_stream = sd.InputStream(
                samplerate=native_rate,
                channels=native_channels,
                dtype="int16",
                blocksize=blocksize,
                device=target_dev,
                callback=self._audio_callback,
            )
            self.audio_stream.start()
            self._capture_opened_at = time.perf_counter()
            self._frames_captured_count = 0
            self._bytes_captured_count = 0

            logger.info(
                "[Audio Boundary] Audio input stream started: device=[%s] '%s', native_rate=%d, channels=%d, blocksize=%d, target_rate=%d, resampling=%s",
                target_dev, self._selected_device_name, native_rate, native_channels, blocksize, self.sample_rate, needs_resampling
            )
            return True

        except Exception as e:
            self.audio_stream = None
            err_msg = f"Failed to open microphone: {str(e)}"
            logger.error(f"[Audio Boundary] {err_msg}", exc_info=True)
            self.broadcast_ws_event("voice_error", {
                "code": "AUDIO_CAPTURE_FAILED",
                "message": err_msg
            })
            state_manager.set_state(NovaState.ERROR, "MICROPHONE ERROR")
            return False

    def _close_input_stream(self) -> None:
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except Exception as e:
                logger.warning(f"Error closing audio stream: {e}")
            self.audio_stream = None

    def set_audio_devices(self, input_device: Optional[int] = None, output_device: Optional[int] = None) -> None:
        if input_device is not None:
            self.input_device = input_device
        if output_device is not None:
            self.output_device = output_device
            self.tts.output_device = output_device
        if self.is_running and self.wake_word_enabled and input_device is not None:
            self._close_input_stream()
            self._open_input_stream()

    def set_speech_rate(self, rate: float) -> None:
        self.tts.speech_rate = rate

    def set_wake_word_enabled(self, enabled: bool) -> None:
        """Enable optional continuous wake-word mode, or PTT (mic closed when idle)."""
        self.wake_word_enabled = bool(enabled)
        if not self.is_running:
            return
        if self.wake_word_enabled:
            self._open_input_stream()
            self.pipeline_mode = "WAKE_WORD"
        else:
            if self.pipeline_mode in ("WAKE_WORD", "PTT_STANDBY"):
                self._close_input_stream()
                self.pipeline_mode = "PTT_STANDBY"
        self.broadcast_ws_event("voice_status", {
            "running": self.is_running,
            "mode": self.pipeline_mode,
            "wake_word_enabled": self.wake_word_enabled,
        })

    def cancel_active_turn(self) -> None:
        """Interrupt TTS and in-flight Ollama generation for the current utterance."""
        self._cancel_requested.set()
        self.tts.stop()
        model_manager.cancel_active()
        self.pipeline_mode = "WAKE_WORD" if self.wake_word_enabled else "PTT_STANDBY"
        state_manager.set_state(NovaState.IDLE, "NOVA SYSTEM ONLINE")
        self.broadcast_ws_event("inference_cancelled", {})

    def stop_listening(self) -> bool:
        """Signal active speech recognition to finalize and stop immediately."""
        self._stop_listening_requested.set()
        logger.info("[Audio Boundary] stop_listening called.")
        return True

    def trigger_listening(self) -> bool:
        """Manually trigger listening state (push-to-talk / UI mic tap)."""
        self._stop_listening_requested.clear()
        if not self.is_running:
            started = self.start()
            if not started:
                return False

        if self.pipeline_mode in ("THINKING", "SPEAKING") or self.tts.is_speaking:
            self.cancel_active_turn()

        self.manual_listening_trigger = True
        return True

    def _processing_loop(self):
        """Dedicated background audio processing loop."""
        logger.info("Audio processing worker loop initiated.")

        while self.is_running and not self._stop_event.is_set():
            try:
                # Handle manual listening trigger from UI (push-to-talk)
                if self.manual_listening_trigger:
                    self.manual_listening_trigger = False
                    if not self._open_input_stream():
                        continue
                    self._handle_active_speech_recognition(trigger_source="manual")
                    if not self.wake_word_enabled:
                        self._close_input_stream()
                        self.pipeline_mode = "PTT_STANDBY"
                    continue

                # Get audio frame from queue
                try:
                    frame = self.audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                # Calculate live audio RMS level for visualizer
                float_frame = frame.astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(float_frame ** 2))) if len(float_frame) > 0 else 0.0

                # Periodic audio level telemetry
                if rms > 0.003:
                    self.broadcast_ws_event("audio_level", {"rms": round(rms, 4)})

                # 1. WAKE-WORD DETECTION PHASE (Gated by acoustic energy to keep CPU near 0% when idle)
                if self.wake_word_enabled and self.pipeline_mode == "WAKE_WORD":
                    if rms > 0.002:
                        if self.wake_word_engine.is_wake_word_triggered(frame):
                            self.broadcast_ws_event("wake_word_detected", {
                                "model": self.wake_word_engine.active_model_key,
                                "phrase": self.wake_word_engine.active_wake_phrase
                            })
                            self._wake_detected_at = time.perf_counter()
                            self._handle_active_speech_recognition(trigger_source="wake_word")

            except Exception as e:
                logger.error(f"Error in audio processing loop: {e}", exc_info=True)
                time.sleep(0.1)

        logger.info("Audio processing worker loop terminated.")

    def _idle_mode(self) -> str:
        return "WAKE_WORD" if self.wake_word_enabled else "PTT_STANDBY"

    def _handle_active_speech_recognition(self, trigger_source: str = "wake_word"):
        """Run Vosk speech recognition on incoming audio stream with live telemetry."""
        self.pipeline_mode = "LISTENING_SPEECH"
        state_manager.set_state(NovaState.LISTENING, "AWAITING VOCAL DIRECTIVE")
        listen_t0 = time.perf_counter()
        self._listen_started_at = listen_t0
        self._stop_listening_requested.clear()

        logger.info("[Audio Boundary] Listening started (trigger=%s, device='%s').", trigger_source, self._selected_device_name)
        self.broadcast_ws_event("listening_started", {
            "trigger": trigger_source,
            "mode": "wake_word" if trigger_source == "wake_word" else "push_to_talk",
            "device": self._selected_device_name,
        })
        
        # Reset engines
        self.wake_word_engine.reset()
        self.speech_recognizer.reset()

        frame_count = 0

        def _audio_generator():
            nonlocal frame_count
            while self.is_running and not self._stop_event.is_set():
                if self._stop_listening_requested.is_set():
                    logger.info("[Audio Boundary] Stop listening requested during speech capture.")
                    break
                try:
                    f = self.audio_queue.get(timeout=0.25)
                    frame_count += 1
                    # Broadcast live RMS every frame so frontend waveform pulses with speech
                    float_f = f.astype(np.float32) / 32768.0
                    rms = float(np.sqrt(np.mean(float_f ** 2))) if len(float_f) > 0 else 0.0
                    if frame_count % 2 == 0:
                        self.broadcast_ws_event("audio_level", {"rms": round(rms, 4)})
                    yield f
                except queue.Empty:
                    continue

        def _on_partial(partial_text: str):
            logger.debug("[STT Boundary] Partial transcription: '%s'", partial_text)
            self.broadcast_ws_event("partial_speech", {"partial": partial_text})

        stt_t0 = time.perf_counter()
        telemetry = self.speech_recognizer.transcribe_stream_detailed(
            _audio_generator(),
            on_partial=_on_partial,
            stop_event=self._stop_listening_requested
        )
        self._last_stt_telemetry = telemetry

        recognized_text = telemetry.get("text", "").strip()
        stt_ms = round((time.perf_counter() - stt_t0) * 1000.0, 2)
        listen_ms = round((time.perf_counter() - listen_t0) * 1000.0, 2)

        self.broadcast_ws_event("listening_stopped", {
            "stt_ms": stt_ms,
            "listen_ms": listen_ms,
            "frames": telemetry.get("frames_processed", 0),
            "bytes": telemetry.get("bytes_processed", 0),
            "max_rms": telemetry.get("max_rms", 0.0),
            "reason": telemetry.get("reason", "UNKNOWN"),
        })

        if not recognized_text:
            reason = telemetry.get("reason", "NO_SPEECH")
            logger.info("[STT Boundary] No speech detected (reason=%s, max_rms=%.4f).", reason, telemetry.get("max_rms", 0.0))
            self.broadcast_ws_event("no_speech_detected", {
                "message": "No speech detected. Please tap and speak clearly.",
                "reason": reason,
                "max_rms": telemetry.get("max_rms", 0.0),
            })
            state_manager.set_state(NovaState.IDLE, "NOVA SYSTEM ONLINE")
            self.pipeline_mode = self._idle_mode()
            return

        logger.info("[STT Boundary] Speech recognized: '%s' (%s chars, stt_ms=%s, max_rms=%.4f)", recognized_text, len(recognized_text), stt_ms, telemetry.get("max_rms", 0.0))
        self.broadcast_ws_event("speech_recognized", {
            "text": recognized_text,
            "stt_ms": stt_ms,
            "frames": telemetry.get("frames_processed", 0),
            "max_rms": telemetry.get("max_rms", 0.0),
        })

        self._dispatch_to_brain(
            recognized_text,
            stt_ms=stt_ms,
            trigger_source=trigger_source,
        )

    def _dispatch_to_brain(
        self,
        user_query: str,
        stt_ms: float = 0.0,
        trigger_source: str = "manual",
    ):
        """Pass recognized speech query to NOVA Brain and synthesize speech response."""
        utterance_id = new_request_id()
        with self._utterance_lock:
            if self._active_utterance_id and self.pipeline_mode == "THINKING":
                self.cancel_active_turn()
            self._active_utterance_id = utterance_id
        self._cancel_requested.clear()
        trace = InferenceTrace(request_id=utterance_id, source="voice")
        trace.metrics["stt_ms"] = stt_ms
        trace.metrics["trigger"] = trigger_source
        try:
            self.pipeline_mode = "THINKING"
            state_manager.set_state(NovaState.THINKING, "PROCESSING NEURAL INFERENCE")
            self.broadcast_ws_event("thinking_started", {
                "prompt": user_query,
                "request_id": utterance_id,
            })

            # Log to memory bank (both voice session and default chat session for UI visibility)
            memory_bank.add_message(role="user", content=user_query, session_id="voice")
            memory_bank.add_message(role="user", content=user_query, session_id="default")

            # 1. Check for pending voice approval if active (v0.4)
            now = time.time()
            if self.pending_voice_task_id and now < self.pending_voice_task_expiry:
                task_id = self.pending_voice_task_id
                lower_q = user_query.lower().strip()
                if any(word in lower_q for word in ["yes", "proceed", "confirm", "approve", "go ahead", "do it", "sure", "ok", "okay"]):
                    self.pending_voice_task_id = None
                    if self._loop and self._loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            execution_manager.approve_and_execute(task_id),
                            self._loop
                        )
                        task_res = future.result(timeout=30)
                    else:
                        task_res = asyncio.run(execution_manager.approve_and_execute(task_id))
                    
                    status_text = "Operation confirmed and executed successfully." if task_res and task_res.status == TaskStatus.COMPLETED else "Operation completed with warnings."
                    self._speak_response(status_text, "tools-core", user_query)
                    return
                elif any(word in lower_q for word in ["no", "cancel", "abort", "reject", "don't", "stop", "nevermind"]):
                    self.pending_voice_task_id = None
                    execution_manager.reject_task(task_id)
                    self._speak_response("Operation cancelled.", "tools-core", user_query)
                    return
            
            if self.pending_voice_task_id and now >= self.pending_voice_task_expiry:
                self.pending_voice_task_id = None

            # 1.5 Check for pending voice workflow approvals (v0.6)
            if self.pending_voice_workflow_id and now < self.pending_voice_workflow_expiry:
                wf_id = self.pending_voice_workflow_id
                st_id = self.pending_voice_workflow_step_id
                lower_q = user_query.lower().strip()
                if any(word in lower_q for word in ["yes", "proceed", "confirm", "approve", "go ahead", "do it", "sure", "ok", "okay"]):
                    self.pending_voice_workflow_id = None
                    self.pending_voice_workflow_step_id = None
                    if self._loop and self._loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            agent_orchestrator.approve_step(wf_id, st_id),
                            self._loop
                        )
                        future.result(timeout=60)
                    else:
                        asyncio.run(agent_orchestrator.approve_step(wf_id, st_id))
                    
                    self._speak_response("Workflow step confirmed and resumed.", "agent-orchestrator", user_query)
                    return
                elif any(word in lower_q for word in ["no", "cancel", "abort", "reject", "don't", "stop", "nevermind"]):
                    self.pending_voice_workflow_id = None
                    self.pending_voice_workflow_step_id = None
                    if self._loop and self._loop.is_running():
                        asyncio.run_coroutine_threadsafe(agent_orchestrator.reject_step(wf_id, st_id), self._loop)
                    else:
                        asyncio.run(agent_orchestrator.reject_step(wf_id, st_id))
                    self._speak_response("Workflow step rejected and halted.", "agent-orchestrator", user_query)
                    return

            if self.pending_voice_workflow_id and now >= self.pending_voice_workflow_expiry:
                self.pending_voice_workflow_id = None
                self.pending_voice_workflow_step_id = None

            # 1.6 Check for personalization & adaptive intelligence directives (v0.8)
            pers_handled, pers_resp = self.handle_voice_personalization_command(user_query)
            if pers_handled:
                self._speak_response(pers_resp, "personalization-engine", user_query)
                return

            # 1.7 Check for proactive automation & reminder directives (v0.7)
            auto_handled, auto_resp = self.handle_voice_automation_command(user_query)
            if auto_handled:
                self._speak_response(auto_resp, "automation-manager", user_query)
                return

            # 1.8 Check for high-level agentic workflow directives (v0.6)
            lower_q = user_query.lower().strip()
            agentic_triggers = [
                "inspect the project", "inspect my project", "inspect my nova project",
                "plan my work", "run tests", "run the tests",
                "stop the current workflow", "stop workflow", "cancel workflow",
            ]
            if any(trig in lower_q for trig in agentic_triggers):
                try:
                    if self._loop and self._loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            agent_orchestrator.handle_voice_agentic_command(user_query),
                            self._loop
                        )
                        cmd_res = future.result(timeout=45)
                    else:
                        cmd_res = asyncio.run(agent_orchestrator.handle_voice_agentic_command(user_query))

                    if cmd_res.get("action") == "pending_approval":
                        self.pending_voice_workflow_id = cmd_res.get("workflow_id")
                        plan_obj = cmd_res.get("plan")
                        self.pending_voice_workflow_step_id = plan_obj.pending_approval_step_id if plan_obj else None
                        self.pending_voice_workflow_expiry = time.time() + 45.0

                    self._speak_response(cmd_res.get("spoken_response", "Workflow directive acknowledged."), "agent-orchestrator", user_query)
                    return
                except Exception as ex:
                    logger.error(f"Voice agentic workflow dispatch error: {ex}")
                    self._speak_response(f"I encountered an error planning that workflow: {str(ex)}", "agent-orchestrator", user_query)
                    return

            # 2. Check for direct desktop operation directives (v0.4)
            detected_plan = task_planner._deterministic_plan(f"vtask_{int(time.time())}", user_query)
            if detected_plan and len(detected_plan.steps) > 0:
                detected_plan = task_planner._validate_and_sanitize_plan(detected_plan)
                if detected_plan.requires_confirmation:
                    self.pending_voice_task_id = detected_plan.task_id
                    self.pending_voice_task_expiry = time.time() + 45.0
                    execution_logger.save_task(detected_plan)
                    spoken_msg = f"I have prepared an operation to {detected_plan.description}. This action requires confirmation. Would you like me to proceed?"
                    self._speak_response(spoken_msg, "tools-planner", user_query)
                    return
                else:
                    if self._loop and self._loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            execution_manager.execute_task(detected_plan),
                            self._loop
                        )
                        task_res = future.result(timeout=30)
                    else:
                        task_res = asyncio.run(execution_manager.execute_task(detected_plan))
                    
                    spoken_msg = f"Task completed: {detected_plan.description}."
                    if len(detected_plan.steps) == 1 and detected_plan.steps[0].result:
                        res_dict = detected_plan.steps[0].result
                        if "message" in res_dict:
                            spoken_msg = res_dict["message"]
                        elif detected_plan.steps[0].tool_id == "system_cpu_ram":
                            cpu_val = res_dict.get("cpu", {}).get("percent", 0)
                            ram_val = res_dict.get("ram", {}).get("percent", 0)
                            spoken_msg = f"Current CPU utilization is {cpu_val} percent, and RAM usage is {ram_val} percent."
                        elif detected_plan.steps[0].tool_id == "system_battery_info":
                            pct = res_dict.get("percent", 100)
                            st = res_dict.get("status", "Plugged in")
                            spoken_msg = f"Battery level is {pct} percent, status is {st}."
                    
                    self._speak_response(spoken_msg, "tools-executor", user_query)
                    return

            # 2.5 Check for visual intelligence screen queries (v0.5)
            lower_q = user_query.lower()
            visual_triggers = [
                "look at my screen", "look at the screen", "what is on my screen",
                "what's on my screen", "read the error", "read the error message",
                "explain what i'm seeing", "explain what i am seeing",
                "summarize this page", "summarize the page", "summarize this screen",
                "what application is open", "what app is open", "what window is open",
                "what is currently open", "what does this dialog say", "what does this say"
            ]
            if any(vt in lower_q for vt in visual_triggers):
                target = CaptureTarget.ACTIVE_WINDOW if any(w in lower_q for w in ["application", "app", "window", "dialog"]) else CaptureTarget.PRIMARY
                req = VisualAnalysisRequest(prompt=user_query, capture_target=target)
                try:
                    if self._loop and self._loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            vision_manager.analyze_screen(req),
                            self._loop
                        )
                        v_res = future.result(timeout=45)
                    else:
                        v_res = asyncio.run(vision_manager.analyze_screen(req))

                    self.broadcast_ws_event("visual_analysis_completed", {
                        "answer": v_res.answer,
                        "target": target.value
                    })
                    self._speak_response(v_res.answer, "vision-core", user_query)
                    return
                except Exception as ex:
                    logger.error(f"Visual voice command analysis failed: {ex}")
                    self._speak_response(f"I was unable to analyze your screen: {str(ex)}", "vision-core", user_query)
                    return

            # 3. Check for immediate explicit memory query/command
            explicit_memory_answer = memory_manager.handle_explicit_memory_query(user_query)
            if explicit_memory_answer:
                response_text = explicit_memory_answer
                model_used = "memory-core"
                trace.metrics["ollama_calls"] = 0
                self._speak_response(response_text, model_used, user_query, defer_extract=True)
                return

            prompt_t0 = time.perf_counter()
            system_context_addition = ""
            lower_q = user_query.lower()
            if any(term in lower_q for term in ["cpu", "ram", "memory", "battery", "system", "disk", "hardware"]):
                telemetry = SystemMonitor.get_metrics()
                cpu_p = telemetry.get("cpu", {}).get("percent", 0)
                ram_p = telemetry.get("ram", {}).get("percent", 0)
                ram_used = telemetry.get("ram", {}).get("used_gb", 0)
                ram_total = telemetry.get("ram", {}).get("total_gb", 0)
                battery = telemetry.get("battery", {})
                battery_str = f"{battery.get('percent', 100)}% ({battery.get('status', 'A/C')})"
                system_context_addition = (
                    f"\n[Real-Time System Telemetry]: CPU: {cpu_p}%, "
                    f"RAM: {ram_p}% ({ram_used} GB / {ram_total} GB), Battery: {battery_str}. "
                    "Quote these exact live metrics in your response."
                )

            memory_context, _proj = memory_manager.build_augmented_context(
                user_query=user_query,
                session_id="voice",
                compact=True,
                max_items=2,
            )
            voice_system = (
                f"{settings.SYSTEM_PROMPT} "
                "Spoken replies must be 1-3 short sentences. No markdown or code."
                f"{(' ' + memory_context) if memory_context else ''}"
                f"{system_context_addition}"
            )
            messages = [
                {"role": "system", "content": voice_system},
                {"role": "user", "content": user_query},
            ]
            trace.metrics["prompt_construct_ms"] = round((time.perf_counter() - prompt_t0) * 1000.0, 2)

            first_token_ms = None
            first_audio_ms = None
            t_infer = time.perf_counter()
            self._tts_text_buffer = ""
            collected: list = []
            model_used = settings.DEFAULT_MODEL
            metrics: dict = {}

            async def _run_stream():
                nonlocal first_token_ms, first_audio_ms, model_used, metrics
                from app.reliability.resource_coordinator import resource_coordinator
                async with resource_coordinator.acquire_inference_slot(timeout=180.0):
                    async for event in model_manager.chat_stream(
                        messages=messages,
                        profile="voice",
                        request_id=utterance_id,
                    ):
                        if self._cancel_requested.is_set():
                            model_manager.cancel_active()
                            return
                        if event.get("type") == "token":
                            piece = event.get("content") or ""
                            if piece:
                                collected.append(piece)
                                if first_token_ms is None:
                                    first_token_ms = round((time.perf_counter() - t_infer) * 1000.0, 2)
                                    self.pipeline_mode = "SPEAKING"
                                    state_manager.set_state(NovaState.SPEAKING, "TRANSMITTING RESPONSE")
                                    self.broadcast_ws_event("speaking_started", {
                                        "text": piece,
                                        "model": event.get("model") or model_used,
                                        "request_id": utterance_id,
                                        "ttft_ms": first_token_ms,
                                        "partial": True,
                                    })
                                    self.broadcast_ws_event("token_delta", {
                                        "request_id": utterance_id,
                                        "content": piece,
                                        "ttft_ms": first_token_ms,
                                    })
                                else:
                                    self.broadcast_ws_event("token_delta", {
                                        "request_id": utterance_id,
                                        "content": piece,
                                    })
                                started_audio = self._feed_tts_sentences(piece)
                                if started_audio and first_audio_ms is None:
                                    first_audio_ms = round((time.perf_counter() - t_infer) * 1000.0, 2)
                        elif event.get("type") == "done":
                            model_used = event.get("model") or model_used
                            metrics = event.get("metrics") or {}
                        elif event.get("type") == "error":
                            if event.get("error_type") == "CANCELLED":
                                return
                            collected.append(event.get("content") or "")
                            model_used = event.get("model") or model_used

            if self._loop and self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(_run_stream(), self._loop)
                future.result(timeout=180)
            else:
                asyncio.run(_run_stream())

            if self._cancel_requested.is_set():
                return

            response_text = "".join(collected).strip() or "Neural inference unavailable."
            leftover = self._tts_text_buffer.strip()
            self._tts_text_buffer = ""
            if leftover:
                self.tts.enqueue(leftover)
            self.tts.mark_generation_complete()

            trace.metrics["ttft_ms"] = first_token_ms
            trace.metrics["time_to_first_audio_ms"] = first_audio_ms
            trace.metrics["ollama_calls"] = 1
            trace.metrics.update({k: v for k, v in metrics.items() if k not in trace.metrics})
            payload = trace.finalize({"eval_count": metrics.get("eval_count"), "tokens_per_sec": metrics.get("tokens_per_sec")})
            store_trace(payload)

            def _after_speech():
                try:
                    memory_manager.process_turn_and_extract(user_query, session_id="voice")
                except Exception as err:
                    logger.warning(f"Voice background memory extraction error: {err}")
                memory_bank.add_message(
                    role="assistant",
                    content=response_text,
                    session_id="voice",
                    model=model_used,
                )
                memory_bank.add_message(
                    role="assistant",
                    content=response_text,
                    session_id="default",
                    model=model_used,
                )
                self.broadcast_ws_event("speaking_finished", {"metrics": payload})
                state_manager.set_state(NovaState.IDLE, "NOVA SYSTEM ONLINE")
                self.pipeline_mode = self._idle_mode()
                with self._utterance_lock:
                    if self._active_utterance_id == utterance_id:
                        self._active_utterance_id = None

            if not self.tts.is_speaking:
                self.broadcast_ws_event("speaking_started", {
                    "text": response_text,
                    "model": model_used,
                    "request_id": utterance_id,
                    "metrics": payload,
                })
                self.tts.speak(text=response_text, on_finished=_after_speech, block=False)
            else:
                self.tts._queue_on_finished = _after_speech
                self.broadcast_ws_event("speaking_started", {
                    "text": response_text,
                    "model": model_used,
                    "request_id": utterance_id,
                    "metrics": payload,
                })

        except Exception as e:
            logger.error(f"Error querying AI Brain for voice query: {e}")
            error_msg = f"NOVA neural core encountered an exception: {str(e)}"
            state_manager.set_state(NovaState.ERROR, "NEURAL PROCESSING ERROR")
            self.broadcast_ws_event("voice_error", {"message": error_msg})
            self.tts.speak(
                text=error_msg,
                on_finished=lambda: state_manager.set_state(NovaState.IDLE, "NOVA SYSTEM ONLINE")
            )
            self.pipeline_mode = self._idle_mode()
            with self._utterance_lock:
                self._active_utterance_id = None

    def _feed_tts_sentences(self, piece: str) -> bool:
        """Enqueue complete sentences as they stream. Returns True if audio was started."""
        if not piece:
            return False
        self._tts_text_buffer += piece
        started = False
        while True:
            idx = -1
            for sep in (". ", "! ", "? ", ".\n", "!\n", "?\n"):
                found = self._tts_text_buffer.find(sep)
                if found != -1 and (idx == -1 or found < idx):
                    idx = found + len(sep)
            if idx == -1:
                break
            sentence = self._tts_text_buffer[:idx].strip()
            self._tts_text_buffer = self._tts_text_buffer[idx:]
            if sentence:
                self.tts.enqueue(sentence)
                started = True
        return started

    def _speak_response(self, response_text: str, model_used: str, user_query: str, defer_extract: bool = False):
        """Synthesize response with Piper TTS, record in persistent memory, and broadcast events."""
        memory_bank.add_message(
            role="assistant",
            content=response_text,
            session_id="voice",
            model=model_used
        )
        memory_bank.add_message(
            role="assistant",
            content=response_text,
            session_id="default",
            model=model_used
        )

        self.pipeline_mode = "SPEAKING"
        state_manager.set_state(NovaState.SPEAKING, "TRANSMITTING RESPONSE")
        self.broadcast_ws_event("speaking_started", {
            "text": response_text,
            "model": model_used
        })

        def _on_speaking_finished():
            if defer_extract:
                try:
                    memory_manager.process_turn_and_extract(user_query, session_id="voice")
                except Exception as err:
                    logger.warning(f"Voice background memory extraction error: {err}")
            self.broadcast_ws_event("speaking_finished", {})
            state_manager.set_state(NovaState.IDLE, "NOVA SYSTEM ONLINE")
            self.pipeline_mode = self._idle_mode()
            with self._utterance_lock:
                self._active_utterance_id = None

        self.tts.speak(
            text=response_text,
            on_finished=_on_speaking_finished,
            block=False
        )

    def get_status(self) -> Dict[str, Any]:
        """Comprehensive voice pipeline status report."""
        perm_info = check_windows_microphone_permission()
        is_muted, vol_scalar = get_default_capture_mute_and_volume()
        return {
            "running": self.is_running,
            "pipeline_mode": self.pipeline_mode,
            "wake_word_enabled": self.wake_word_enabled,
            "voice_mode": "wake_word" if self.wake_word_enabled else "push_to_talk",
            "wake_word": self.wake_word_engine.get_status(),
            "speech_recognition": self.speech_recognizer.get_status(),
            "tts": self.tts.get_status(),
            "audio": {
                "sample_rate": self.sample_rate,
                "input_device": self.input_device,
                "selected_device_name": getattr(self, "_selected_device_name", "Default"),
                "selected_device_index": getattr(self, "_selected_device_index", None),
                "output_device": self.output_device,
                "frames_captured": getattr(self, "_frames_captured_count", 0),
                "bytes_captured": getattr(self, "_bytes_captured_count", 0),
                "windows_permission": perm_info,
                "is_muted": is_muted,
                "volume_scalar": vol_scalar,
            }
        }

    def handle_voice_personalization_command(self, user_query: str) -> Tuple[bool, str]:
        """Handles v0.8 Personalization & Adaptive Intelligence voice directives."""
        try:
            from app.personalization import personalization_manager
            return personalization_manager.handle_voice_personalization_command(user_query)
        except Exception as e:
            logger.error(f"Voice personalization dispatch error: {e}")
            return False, ""

    def handle_voice_automation_command(self, user_query: str) -> Tuple[bool, str]:
        """Handles v0.7 Proactive Automation and Reminder voice directives."""
        import re
        lower_q = user_query.lower().strip()
        cleaned_q = re.sub(r"^(hey\s+nova\b[,:]?\s*|nova\b[,:]?\s*)", "", lower_q).strip()

        try:
            from app.automation import (
                automation_manager, AutomationCreate, TriggerConfig, ScheduleConfig,
                TriggerType, ScheduleType, AutomationActionType, AutonomyLevel, ReminderCreate
            )

            # 1. Global pause / resume
            if any(w in cleaned_q for w in ["pause all automations", "pause automations", "pause my automations"]):
                automation_manager.pause_all()
                return True, "All automations have been paused."
            if any(w in cleaned_q for w in ["resume my automations", "resume all automations", "resume automations"]):
                automation_manager.resume_all()
                return True, "All automations have been resumed."

            # 2. Status inquiry
            if any(w in cleaned_q for w in ["what automations are running", "which automations are running", "list automations", "status of automations"]):
                st = automation_manager.get_status()
                paused_str = "Global pause is active. " if st.is_paused else ""
                return True, f"{paused_str}You have {st.active_count} active automation routines, with {st.running_workflows_count} running workflows and {st.pending_reminders_count} pending reminders."

            # 3. Pending tasks inquiry
            if any(w in cleaned_q for w in ["what tasks are still pending", "what tasks are pending", "pending tasks", "list my reminders", "pending reminders"]):
                reminders = automation_manager.list_reminders(pending_only=True)
                if not reminders:
                    return True, "You have no pending tasks or reminders scheduled."
                items_str = ", ".join([r.text for r in reminders[:3]])
                count = len(reminders)
                extra = f" and {count - 3} more" if count > 3 else ""
                return True, f"You have {count} pending tasks: {items_str}{extra}."

            # 4. Create Daily Briefing
            if "daily briefing" in cleaned_q:
                time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", cleaned_q)
                time_str = "08:00"
                if time_match:
                    hr = int(time_match.group(1))
                    mn = int(time_match.group(2)) if time_match.group(2) else 0
                    ampm = time_match.group(3)
                    if ampm == "pm" and hr < 12:
                        hr += 12
                    elif ampm == "am" and hr == 12:
                        hr = 0
                    time_str = f"{hr:02d}:{mn:02d}"

                rule = automation_manager.create_automation(AutomationCreate(
                    name="Daily Morning Briefing",
                    description=f"Automated daily briefing at {time_str}",
                    action_type=AutomationActionType.DAILY_BRIEFING,
                    trigger_config=TriggerConfig(
                        trigger_type=TriggerType.SCHEDULE,
                        schedule=ScheduleConfig(
                            schedule_type=ScheduleType.DAILY,
                            time_of_day=time_str
                        )
                    ),
                    action_payload={"speak_aloud": True}
                ))
                return True, f"Daily briefing routine created and scheduled for {time_str}."

            # 5. Project Health Check
            if ("check my" in cleaned_q or "check project" in cleaned_q) and ("health" in cleaned_q or "project" in cleaned_q) and "saturday" in cleaned_q:
                rule = automation_manager.create_automation(AutomationCreate(
                    name="Weekly Project Health Check",
                    description="Checks project workspace and tests every Saturday at 10 AM",
                    action_type=AutomationActionType.PROJECT_HEALTH,
                    trigger_config=TriggerConfig(
                        trigger_type=TriggerType.SCHEDULE,
                        schedule=ScheduleConfig(
                            schedule_type=ScheduleType.WEEKLY,
                            time_of_day="10:00",
                            days_of_week=[5]
                        ),
                        project_id="nova"
                    ),
                    action_payload={"run_tests": True}
                ))
                return True, "Scheduled weekly health check for your NOVA project every Saturday at 10:00 AM."

            # 6. Reminders
            if "remind me" in cleaned_q:
                rem_text = re.sub(r"^.*?remind me\s+(to\s+|tomorrow\s+to\s+|every\s+\w+\s+to\s+)?", "", cleaned_q, flags=re.IGNORECASE).strip()
                if not rem_text:
                    rem_text = cleaned_q
                due_iso = None
                if "tomorrow" in cleaned_q:
                    from datetime import datetime, timedelta
                    due_iso = (datetime.utcnow() + timedelta(days=1)).isoformat()
                
                automation_manager.add_reminder(ReminderCreate(
                    text=rem_text.capitalize(),
                    due_at=due_iso
                ))
                return True, f"Reminder set: {rem_text.capitalize()}."

        except Exception as e:
            logger.error(f"Error handling voice automation command: {e}")
            return True, f"Could not complete automation directive: {e}"

        return False, ""

    def handle_voice_agentic_command(self, user_query: str) -> Tuple[bool, str]:
        """Direct helper to evaluate and handle natural-language voice agentic commands."""
        lower_q = user_query.lower().strip()
        agentic_triggers = [
            "inspect the project", "inspect my project", "inspect my nova project",
            "plan my work", "run tests", "run the tests",
            "stop the current workflow", "stop workflow", "cancel workflow",
        ]
        if any(trig in lower_q for trig in agentic_triggers):
            try:
                from app.agents.agent_orchestrator import agent_orchestrator
                import asyncio
                if self._loop and self._loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        agent_orchestrator.handle_voice_agentic_command(user_query),
                        self._loop
                    )
                    res = future.result(timeout=45)
                else:
                    res = asyncio.run(agent_orchestrator.handle_voice_agentic_command(user_query))
                return True, res.get("spoken_response", "Workflow command processed.")
            except Exception as e:
                return True, f"Error processing workflow command: {e}"
        return False, ""

# Global singleton instance
audio_manager = AudioManager()
