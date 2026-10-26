import os
import json
import time
import logging
import numpy as np
from typing import Optional, Dict, Any, Generator, Callable
from app.config import settings

logger = logging.getLogger("nova.voice.stt")

class SpeechRecognizer:
    """
    Vosk-powered offline speech-to-text transcription engine.
    Processes 16kHz 16-bit mono audio streams with silence detection,
    adaptive energy gating, and structured diagnostic telemetry.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        sample_rate: int = 16000,
        silence_timeout: Optional[float] = None,
        max_timeout: Optional[float] = None,
        initial_silence_timeout: float = 3.5,
        energy_threshold: float = 0.005,
    ):
        self.sample_rate = sample_rate
        self.silence_timeout = silence_timeout or settings.SPEECH_SILENCE_TIMEOUT
        self.max_timeout = max_timeout or settings.SPEECH_MAX_TIMEOUT
        self.initial_silence_timeout = initial_silence_timeout
        self.energy_threshold = energy_threshold
        self.model_path = model_path or settings.VOSK_MODEL_PATH
        
        self.model = None
        self.recognizer = None
        self.is_initialized = False
        self.error_message: Optional[str] = None
        self.last_telemetry: Dict[str, Any] = {}
        
        self._init_vosk()

    def _init_vosk(self) -> bool:
        """Initialize Vosk model and Kaldi recognizer."""
        try:
            import vosk
            vosk.SetLogLevel(-1)

            resolved_path = self.model_path
            if resolved_path and not os.path.exists(resolved_path) and os.path.exists(os.path.join(settings.ROOT_DIR, resolved_path)):
                resolved_path = os.path.join(settings.ROOT_DIR, resolved_path)

            if resolved_path and os.path.exists(resolved_path):
                logger.info(f"[STT] Loading Vosk model from explicit path: {resolved_path}")
                self.model = vosk.Model(resolved_path)
            else:
                logger.info("[STT] Initializing Vosk en-us model...")
                self.model = vosk.Model(lang="en-us")

            self.recognizer = vosk.KaldiRecognizer(self.model, float(self.sample_rate))
            self.recognizer.SetWords(True)
            self.is_initialized = True
            self.error_message = None
            logger.info("[STT] SpeechRecognizer initialized successfully (sample_rate=%d).", self.sample_rate)
            return True
        except Exception as e:
            self.is_initialized = False
            self.error_message = f"Vosk initialization error: {str(e)}"
            logger.error("[STT] %s", self.error_message, exc_info=True)
            return False

    def reset(self) -> None:
        """Reset Kaldi recognizer state for fresh utterance."""
        if self.is_initialized and self.model:
            import vosk
            self.recognizer = vosk.KaldiRecognizer(self.model, float(self.sample_rate))
            self.recognizer.SetWords(True)

    def process_chunk(self, audio_chunk: np.ndarray) -> Dict[str, Any]:
        """
        Feed an audio frame (numpy int16 or float32) to Vosk.
        Returns:
        {
            "final": bool,
            "text": str,
            "partial": str
        }
        """
        if not self.is_initialized or self.recognizer is None:
            return {"final": False, "text": "", "partial": "", "error": "Not initialized"}

        try:
            if np.issubdtype(audio_chunk.dtype, np.floating):
                pcm_data = (np.clip(audio_chunk, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
            else:
                pcm_data = audio_chunk.astype(np.int16).tobytes()

            if self.recognizer.AcceptWaveform(pcm_data):
                res = json.loads(self.recognizer.Result())
                text = res.get("text", "").strip()
                return {"final": True, "text": text, "partial": ""}
            else:
                res = json.loads(self.recognizer.PartialResult())
                partial = res.get("partial", "").strip()
                return {"final": False, "text": "", "partial": partial}
        except Exception as e:
            logger.warning(f"[STT] Error processing audio chunk: {e}")
            return {"final": False, "text": "", "partial": "", "error": str(e)}

    def finalize(self) -> str:
        """Extract final transcription remaining in recognizer buffer."""
        if not self.is_initialized or self.recognizer is None:
            return ""
        try:
            res = json.loads(self.recognizer.FinalResult())
            text = res.get("text", "").strip()
            return text
        except Exception as e:
            logger.warning(f"[STT] Error finalizing STT: {e}")
            return ""

    def transcribe_stream_detailed(
        self,
        audio_stream_generator: Generator[np.ndarray, None, None],
        on_partial: Optional[Callable[[str], None]] = None,
        silence_threshold_energy: Optional[float] = None,
        stop_event: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Consume audio frames until utterance completion, silence timeout, or max timeout.
        Returns structured telemetry dictionary.
        """
        self.reset()
        threshold = silence_threshold_energy if silence_threshold_energy is not None else self.energy_threshold
        start_time = time.time()
        last_speech_time = None
        has_spoken = False
        full_transcription = ""
        frames_processed = 0
        bytes_processed = 0
        rms_values = []
        reason = "STREAM_EXHAUSTED"

        for frame in audio_stream_generator:
            if stop_event is not None and getattr(stop_event, "is_set", lambda: False)():
                reason = "MANUAL_STOP"
                break

            current_time = time.time()
            elapsed = current_time - start_time
            frames_processed += 1
            bytes_processed += frame.nbytes

            # Compute audio energy (RMS)
            float_frame = frame.astype(np.float32) / 32768.0 if frame.dtype == np.int16 else frame
            rms = float(np.sqrt(np.mean(float_frame ** 2))) if len(float_frame) > 0 else 0.0
            rms_values.append(rms)

            result = self.process_chunk(frame)
            partial = result.get("partial", "")

            if partial and on_partial:
                on_partial(partial)

            if rms > threshold or partial:
                if not has_spoken:
                    logger.debug("[STT] First speech energy detected (rms=%.4f, partial='%s')", rms, partial)
                has_spoken = True
                last_speech_time = current_time

            # Check if sentence endpoint detected by Vosk
            if result.get("final") and result.get("text"):
                full_transcription = result["text"]
                reason = "VOSK_ENDPOINT"
                logger.info("[STT] Vosk sentence endpoint reached: '%s'", full_transcription)
                break

            # Silence timeout after user started speaking
            if has_spoken and last_speech_time:
                silence_duration = current_time - last_speech_time
                if silence_duration >= self.silence_timeout:
                    reason = "TRAILING_SILENCE"
                    logger.info("[STT] Trailing silence timeout reached (%.2fs). Finalizing.", silence_duration)
                    break

            # Initial silence timeout (no speech within initial window)
            if not has_spoken and elapsed >= self.initial_silence_timeout:
                reason = "INITIAL_SILENCE"
                logger.info("[STT] Initial silence timeout reached (%.2fs with no voice activity).", elapsed)
                break

            # Overall max timeout
            if elapsed >= self.max_timeout:
                reason = "MAX_TIMEOUT"
                logger.info("[STT] Max speech recognition timeout reached (%.2fs).", self.max_timeout)
                break

        final_text = self.finalize()
        if final_text:
            if full_transcription:
                full_transcription = f"{full_transcription} {final_text}".strip()
            else:
                full_transcription = final_text.strip()

        duration = time.time() - start_time
        max_rms = max(rms_values) if rms_values else 0.0
        avg_rms = sum(rms_values) / len(rms_values) if rms_values else 0.0

        telemetry = {
            "text": full_transcription,
            "frames_processed": frames_processed,
            "bytes_processed": bytes_processed,
            "duration_seconds": round(duration, 3),
            "sample_rate": self.sample_rate,
            "max_rms": round(max_rms, 4),
            "avg_rms": round(avg_rms, 4),
            "has_spoken": has_spoken,
            "reason": reason,
            "error": self.error_message
        }
        self.last_telemetry = telemetry

        logger.info(
            "[STT Boundary] Completed STT: reason=%s, frames=%d, bytes=%d, dur=%.2fs, max_rms=%.4f, text='%s'",
            reason, frames_processed, bytes_processed, duration, max_rms, full_transcription
        )
        return telemetry

    def transcribe_audio_stream(
        self,
        audio_stream_generator: Generator[np.ndarray, None, None],
        on_partial: Optional[Callable[[str], None]] = None,
        silence_threshold_energy: Optional[float] = None
    ) -> str:
        """Backward-compatible wrapper returning pure transcription string."""
        telemetry = self.transcribe_stream_detailed(
            audio_stream_generator,
            on_partial=on_partial,
            silence_threshold_energy=silence_threshold_energy
        )
        return telemetry["text"]

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self.is_initialized,
            "engine": "Vosk (Local Offline)",
            "model_path": self.model_path or "vosk-model-small-en-us-0.15",
            "sample_rate": self.sample_rate,
            "silence_timeout": self.silence_timeout,
            "max_timeout": self.max_timeout,
            "initial_silence_timeout": self.initial_silence_timeout,
            "energy_threshold": self.energy_threshold,
            "error": self.error_message,
            "last_telemetry": self.last_telemetry
        }
