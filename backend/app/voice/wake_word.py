import os
import logging
import numpy as np
from typing import Optional, Callable, Dict, Any, List
from app.config import settings

logger = logging.getLogger("nova.voice.wakeword")

class WakeWordEngine:
    """
    OpenWakeWord-powered offline wake-word detector.
    Monitors 16kHz PCM audio buffers for wake phrase activation.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        threshold: Optional[float] = None,
        custom_model_path: Optional[str] = None
    ):
        self.threshold = threshold if threshold is not None else settings.WAKE_WORD_THRESHOLD
        self.custom_model_path = custom_model_path or settings.CUSTOM_WAKE_WORD_PATH
        self.model_name = model_name or settings.WAKE_WORD_MODEL
        
        self.oww_model = None
        self.is_custom_model = False
        self.active_wake_phrase = "Hey Jarvis"
        self.active_model_key = ""
        self.is_initialized = False
        self.error_message: Optional[str] = None
        
        self._init_model()

    def _init_model(self) -> bool:
        """Initialize openWakeWord model instance."""
        try:
            import openwakeword
            from openwakeword.model import Model

            # Check if custom hey_nova model exists
            if self.custom_model_path and os.path.exists(self.custom_model_path):
                logger.info(f"Loading custom wake word model from {self.custom_model_path}")
                self.oww_model = Model(wakeword_models=[self.custom_model_path], inference_framework="onnx")
                self.is_custom_model = True
                self.active_wake_phrase = "Hey NOVA"
                # Use filename stem as key
                self.active_model_key = os.path.splitext(os.path.basename(self.custom_model_path))[0]
            else:
                # Load built-in model (e.g. hey_jarvis)
                target = self.model_name
                logger.info(
                    f"Custom model '{self.custom_model_path}' not found. "
                    f"Loading verified openWakeWord built-in model '{target}'."
                )
                self.oww_model = Model(wakeword_models=[target], inference_framework="onnx")
                self.is_custom_model = False
                self.active_wake_phrase = "Hey Jarvis" if "jarvis" in target else target.replace("_", " ").title()
                self.active_model_key = target

            self.is_initialized = True
            self.error_message = None
            logger.info(f"WakeWordEngine initialized successfully with key '{self.active_model_key}'")
            return True

        except Exception as e:
            self.is_initialized = False
            self.error_message = f"Failed to initialize openWakeWord: {str(e)}"
            logger.error(self.error_message)
            return False

    def predict(self, audio_frame: np.ndarray) -> Dict[str, float]:
        """
        Process 16-bit 16kHz audio chunk through openWakeWord.
        Expects 1280 samples (80ms). Audio is converted to int16 if needed.
        Returns dictionary of model predictions: {model_name: score}.
        """
        if not self.is_initialized or self.oww_model is None:
            return {}

        try:
            # Ensure int16 numpy array
            if audio_frame.dtype != np.int16:
                if np.issubdtype(audio_frame.dtype, np.floating):
                    audio_frame = (audio_frame * 32767).astype(np.int16)
                else:
                    audio_frame = audio_frame.astype(np.int16)

            predictions = self.oww_model.predict(audio_frame)
            return predictions
        except Exception as e:
            logger.warning(f"Wake word inference error: {e}")
            return {}

    def is_wake_word_triggered(self, audio_frame: np.ndarray) -> bool:
        """Evaluates whether current frame triggers wake word above threshold."""
        predictions = self.predict(audio_frame)
        for model_key, score in predictions.items():
            if score >= self.threshold:
                logger.info(f"Wake word triggered! [{model_key}] Score: {score:.3f} >= {self.threshold}")
                return True
        return False

    def reset(self) -> None:
        """Reset internal openWakeWord temporal buffer."""
        if self.oww_model is not None:
            try:
                self.oww_model.reset()
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        """Returns diagnostic status of wake word engine."""
        return {
            "initialized": self.is_initialized,
            "active_model_key": self.active_model_key,
            "wake_phrase": self.active_wake_phrase,
            "is_custom_model": self.is_custom_model,
            "custom_model_path": self.custom_model_path,
            "threshold": self.threshold,
            "error": self.error_message,
            "note": (
                "Verified custom Hey NOVA ONNX model active."
                if self.is_custom_model
                else "Built-in model active ('Hey Jarvis'). Train/provision 'models/wake_words/hey_nova.onnx' for custom 'Hey NOVA' wake phrase."
            )
        }
