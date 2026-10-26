"""Runtime Ollama inference profile for CPU-constrained hardware.

Values are mutable via the existing settings API so they are not hardcoded
into voice, chat, or agent call sites.
"""
from __future__ import annotations

from threading import Lock
from typing import Any, Dict, Optional

from app.config import settings


class InferenceConfig:
    """Process-wide inference options (num_ctx, threads, keep_alive, etc.)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.num_ctx: int = int(settings.OLLAMA_NUM_CTX)
        self.num_predict: int = int(settings.OLLAMA_NUM_PREDICT)
        self.num_predict_voice: int = int(settings.OLLAMA_NUM_PREDICT_VOICE)
        self.num_thread: Optional[int] = settings.OLLAMA_NUM_THREAD
        self.keep_alive: str = settings.OLLAMA_KEEP_ALIVE
        self.temperature: float = float(settings.OLLAMA_TEMPERATURE)
        self.max_history_turns: int = int(settings.OLLAMA_MAX_HISTORY_TURNS)
        self.max_history_turns_voice: int = int(settings.OLLAMA_MAX_HISTORY_TURNS_VOICE)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
                "num_predict_voice": self.num_predict_voice,
                "num_thread": self.num_thread,
                "thread_mode": "auto" if self.num_thread is None else "manual",
                "keep_alive": self.keep_alive,
                "temperature": self.temperature,
                "max_history_turns": self.max_history_turns,
                "max_history_turns_voice": self.max_history_turns_voice,
                "max_concurrent_inference": 1,
            }

    def update(self, **kwargs: Any) -> Dict[str, Any]:
        with self._lock:
            if "num_ctx" in kwargs and kwargs["num_ctx"] is not None:
                self.num_ctx = max(256, min(8192, int(kwargs["num_ctx"])))
            if "num_predict" in kwargs and kwargs["num_predict"] is not None:
                self.num_predict = max(16, min(2048, int(kwargs["num_predict"])))
            if "num_predict_voice" in kwargs and kwargs["num_predict_voice"] is not None:
                self.num_predict_voice = max(16, min(512, int(kwargs["num_predict_voice"])))
            if "keep_alive" in kwargs and kwargs["keep_alive"]:
                self.keep_alive = str(kwargs["keep_alive"])
            if "temperature" in kwargs and kwargs["temperature"] is not None:
                self.temperature = max(0.0, min(1.5, float(kwargs["temperature"])))
            if "max_history_turns" in kwargs and kwargs["max_history_turns"] is not None:
                self.max_history_turns = max(0, min(20, int(kwargs["max_history_turns"])))
            if "max_history_turns_voice" in kwargs and kwargs["max_history_turns_voice"] is not None:
                self.max_history_turns_voice = max(0, min(8, int(kwargs["max_history_turns_voice"])))
            if "thread_mode" in kwargs:
                mode = str(kwargs["thread_mode"]).lower()
                if mode == "auto":
                    self.num_thread = None
            if "num_thread" in kwargs:
                raw = kwargs["num_thread"]
                if raw is None or raw == "" or str(raw).lower() == "auto":
                    self.num_thread = None
                else:
                    self.num_thread = max(1, min(8, int(raw)))
        return self.snapshot()

    def ollama_options(self, profile: str = "text") -> Dict[str, Any]:
        with self._lock:
            predict = self.num_predict_voice if profile == "voice" else self.num_predict
            options: Dict[str, Any] = {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": predict,
            }
            if self.num_thread is not None:
                options["num_thread"] = self.num_thread
            return options


inference_config = InferenceConfig()
