"""Structured inference timing without logging private prompts or audio."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nova.ai.trace")


def new_request_id() -> str:
    return f"inf_{uuid.uuid4().hex[:12]}"


class InferenceTrace:
    """Per-request timing and token accounting for the voice/text pipeline."""

    def __init__(self, request_id: Optional[str] = None, source: str = "text") -> None:
        self.request_id = request_id or new_request_id()
        self.source = source
        self.t0 = time.perf_counter()
        self.marks: Dict[str, float] = {}
        self.metrics: Dict[str, Any] = {
            "request_id": self.request_id,
            "source": source,
        }

    def mark(self, name: str) -> None:
        self.marks[name] = time.perf_counter()

    def elapsed_ms(self, start: Optional[str] = None, end: Optional[str] = None) -> float:
        t_start = self.t0 if start is None else self.marks.get(start, self.t0)
        t_end = time.perf_counter() if end is None else self.marks.get(end, time.perf_counter())
        return round((t_end - t_start) * 1000.0, 2)

    def record_tokens(
        self,
        prompt_eval_count: Optional[int] = None,
        eval_count: Optional[int] = None,
        prompt_eval_duration_ns: Optional[int] = None,
        eval_duration_ns: Optional[int] = None,
        total_duration_ns: Optional[int] = None,
        load_duration_ns: Optional[int] = None,
    ) -> None:
        self.metrics["prompt_eval_count"] = prompt_eval_count
        self.metrics["eval_count"] = eval_count
        tokens_per_sec = None
        if eval_count and eval_duration_ns:
            tokens_per_sec = round(eval_count / (eval_duration_ns / 1e9), 3)
        self.metrics["tokens_per_sec"] = tokens_per_sec
        if prompt_eval_duration_ns:
            self.metrics["prompt_eval_ms"] = round(prompt_eval_duration_ns / 1e6, 2)
        if eval_duration_ns:
            self.metrics["eval_ms"] = round(eval_duration_ns / 1e6, 2)
        if total_duration_ns:
            self.metrics["ollama_total_ms"] = round(total_duration_ns / 1e6, 2)
        if load_duration_ns:
            self.metrics["load_ms"] = round(load_duration_ns / 1e6, 2)
            self.metrics["model_was_loaded"] = load_duration_ns < 500_000_000

    def finalize(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = dict(self.metrics)
        payload["total_ms"] = self.elapsed_ms()
        if extra:
            payload.update(extra)
        logger.info(
            "inference_trace request_id=%s source=%s total_ms=%s ttft_ms=%s eval_count=%s tok_s=%s ollama_calls=%s",
            payload.get("request_id"),
            payload.get("source"),
            payload.get("total_ms"),
            payload.get("ttft_ms"),
            payload.get("eval_count"),
            payload.get("tokens_per_sec"),
            payload.get("ollama_calls", 1),
        )
        return payload


_recent: List[Dict[str, Any]] = []
_RECENT_MAX = 40


def store_trace(payload: Dict[str, Any]) -> None:
    _recent.append(payload)
    if len(_recent) > _RECENT_MAX:
        del _recent[0 : len(_recent) - _RECENT_MAX]


def recent_traces(limit: int = 10) -> List[Dict[str, Any]]:
    return list(_recent[-limit:])
