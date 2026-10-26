import os
import re
import time
import queue
import logging
import threading
import numpy as np
import sounddevice as sd
from typing import Optional, Dict, Any, Callable
from app.config import settings

logger = logging.getLogger("nova.voice.tts")

class TextToSpeech:
    """
    Offline Piper TTS engine for high-fidelity local speech synthesis.
    Integrates directly with sounddevice for interruptible audio playback.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        config_path: Optional[str] = None,
        speech_rate: Optional[float] = None,
        volume: Optional[float] = None,
        output_device: Optional[int] = None
    ):
        self.model_path = model_path or settings.PIPER_MODEL_PATH
        self.config_path = config_path or settings.PIPER_CONFIG_PATH
        self.speech_rate = speech_rate if speech_rate is not None else settings.TTS_SPEECH_RATE
        self.volume = volume if volume is not None else settings.TTS_VOLUME
        self.output_device = output_device if output_device is not None else settings.AUDIO_OUTPUT_DEVICE
        
        self.voice = None
        self.is_initialized = False
        self.error_message: Optional[str] = None
        
        self.is_speaking = False
        self._stop_event = threading.Event()
        self._playback_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._speech_queue: queue.Queue = queue.Queue()
        self._queue_thread: Optional[threading.Thread] = None
        self._queue_idle = threading.Event()
        self._queue_idle.set()
        self._queue_on_finished: Optional[Callable[[], None]] = None
        
        self._init_piper()

    def _init_piper(self) -> bool:
        """Load Piper ONNX voice model."""
        try:
            from piper.voice import PiperVoice

            # Resolve path if relative
            resolved_model = self.model_path
            if not os.path.exists(resolved_model) and os.path.exists(os.path.join(settings.ROOT_DIR, self.model_path)):
                resolved_model = os.path.join(settings.ROOT_DIR, self.model_path)

            if not os.path.exists(resolved_model):
                self.error_message = f"Piper voice model not found at {self.model_path}"
                logger.error(self.error_message)
                self.is_initialized = False
                return False

            resolved_cfg = self.config_path
            if resolved_cfg and not os.path.exists(resolved_cfg) and os.path.exists(os.path.join(settings.ROOT_DIR, self.config_path)):
                resolved_cfg = os.path.join(settings.ROOT_DIR, self.config_path)

            cfg = resolved_cfg if (resolved_cfg and os.path.exists(resolved_cfg)) else None
            logger.info(f"Loading Piper voice from {resolved_model}")
            self.voice = PiperVoice.load(resolved_model, config_path=cfg)
            self.is_initialized = True
            self.error_message = None
            logger.info("TextToSpeech (Piper) initialized successfully.")
            return True
        except Exception as e:
            self.is_initialized = False
            self.error_message = f"Piper TTS initialization failed: {str(e)}"
            logger.error(self.error_message)
            return False

    def clean_text_for_speech(self, text: str) -> str:
        """Sanitize markdown, code blocks, URLs, and HUD symbols for speech."""
        # Remove markdown code blocks
        clean = re.sub(r"```[\s\S]*?```", " Code block omitted. ", text)
        # Remove inline backticks
        clean = re.sub(r"`([^`]+)`", r"\1", clean)
        # Remove URLs
        clean = re.sub(r"https?://\S+", " web link ", clean)
        # Remove bold, italics, headers, bullet stars
        clean = re.sub(r"[*#_~>]", "", clean)
        # Remove excessive whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def synthesize(self, text: str) -> Optional[np.ndarray]:
        """
        Synthesize text into a single float32 or int16 numpy audio array.
        Returns combined audio array or None if synthesis fails.
        """
        if not self.is_initialized or self.voice is None:
            logger.warning("TTS not initialized, cannot synthesize.")
            return None

        clean_text = self.clean_text_for_speech(text)
        if not clean_text:
            return None

        try:
            chunks = list(self.voice.synthesize(clean_text))
            if not chunks:
                return None

            arrays = [c.audio_int16_array for c in chunks if c.audio_int16_array is not None]
            if not arrays:
                return None

            combined = np.concatenate(arrays)
            sample_rate = chunks[0].sample_rate

            # Apply volume adjustments if needed
            if self.volume != 1.0:
                float_audio = combined.astype(np.float32) * float(self.volume)
                combined = np.clip(float_audio, -32768, 32767).astype(np.int16)

            return combined
        except Exception as e:
            logger.error(f"Error during Piper speech synthesis: {e}")
            return None

    def enqueue(self, text: str, on_finished: Optional[Callable[[], None]] = None) -> None:
        """Queue a sentence-sized chunk without cutting off the previous chunk."""
        clean = self.clean_text_for_speech(text)
        if not clean:
            return
        if on_finished:
            self._queue_on_finished = on_finished
        self._speech_queue.put(clean)
        self._queue_idle.clear()
        if self._queue_thread is None or not self._queue_thread.is_alive():
            self._queue_thread = threading.Thread(target=self._drain_queue, daemon=True)
            self._queue_thread.start()

    def mark_generation_complete(self) -> None:
        """Signal that no further chunks will be enqueued for this utterance."""
        self._speech_queue.put(None)

    def _drain_queue(self) -> None:
        self.is_speaking = True
        self._stop_event.clear()
        try:
            while not self._stop_event.is_set():
                try:
                    item = self._speech_queue.get(timeout=0.4)
                except queue.Empty:
                    if self._queue_idle.is_set():
                        break
                    continue
                if item is None:
                    break
                self._play_text_chunks(item)
        finally:
            try:
                sd.stop()
            except Exception:
                pass
            self.is_speaking = False
            self._queue_idle.set()
            cb = self._queue_on_finished
            self._queue_on_finished = None
            if cb and not self._stop_event.is_set():
                cb()

    def _play_text_chunks(self, clean: str) -> None:
        if not self.is_initialized or self.voice is None:
            return
        try:
            chunks = self.voice.synthesize(clean)
            for chunk in chunks:
                if self._stop_event.is_set():
                    break
                audio_arr = chunk.audio_int16_array
                if audio_arr is None or len(audio_arr) == 0:
                    continue
                if self.volume != 1.0:
                    audio_arr = np.clip(audio_arr.astype(np.float32) * self.volume, -32768, 32767).astype(np.int16)
                sd.play(audio_arr, samplerate=chunk.sample_rate, device=self.output_device)
                chunk_duration = len(audio_arr) / chunk.sample_rate
                start_chunk = time.time()
                while time.time() - start_chunk < chunk_duration:
                    if self._stop_event.is_set():
                        sd.stop()
                        break
                    time.sleep(0.04)
        except Exception as e:
            logger.error(f"Audio playback error: {e}")

    def speak(
        self,
        text: str,
        on_started: Optional[Callable[[], None]] = None,
        on_finished: Optional[Callable[[], None]] = None,
        block: bool = False
    ) -> bool:
        """
        Asynchronously or synchronously speak text using sounddevice.
        Supports interruption via stop().
        """
        self.stop()  # Interrupt any previous speech

        def _run_playback():
            with self._lock:
                self.is_speaking = True
                self._stop_event.clear()

            clean = self.clean_text_for_speech(text)
            if not clean:
                self.is_speaking = False
                return

            try:
                if on_started:
                    on_started()
                self._play_text_chunks(clean)
            except Exception as e:
                logger.error(f"Audio playback error: {e}")
            finally:
                sd.stop()
                self.is_speaking = False
                if on_finished and not self._stop_event.is_set():
                    on_finished()

        if block:
            _run_playback()
            return True
        else:
            self._playback_thread = threading.Thread(target=_run_playback, daemon=True)
            self._playback_thread.start()
            return True

    def stop(self) -> None:
        """Interrupt and halt any active audio playback immediately."""
        self._stop_event.set()
        try:
            while True:
                self._speech_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            sd.stop()
        except Exception:
            pass
        self.is_speaking = False
        self._queue_idle.set()
        self._queue_on_finished = None

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self.is_initialized,
            "engine": "Piper TTS (Local Offline)",
            "model_path": self.model_path,
            "is_speaking": self.is_speaking,
            "speech_rate": self.speech_rate,
            "volume": self.volume,
            "output_device": self.output_device,
            "error": self.error_message
        }
