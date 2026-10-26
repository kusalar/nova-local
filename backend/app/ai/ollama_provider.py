import json
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncIterator, Callable

import httpx

from app.ai.model_provider import ModelProvider
from app.ai.inference_config import inference_config
from app.ai.inference_tracer import InferenceTrace, new_request_id, store_trace
from app.config import settings

logger = logging.getLogger("nova.ai.ollama")


class OllamaProvider(ModelProvider):
    """
    Ollama Model Provider for local offline inference.
    Connects to Ollama daemon via REST API.
    """

    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = default_model or settings.DEFAULT_MODEL
        # Connect timeout: 5.0s, Read timeout: 180s for local CPU inference
        self.timeout = httpx.Timeout(180.0, connect=5.0)
        self._cancel_event = asyncio.Event()
        self._active_request_id: Optional[str] = None
        self._call_count = 0
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return "Ollama (Local)"

    def cancel_active(self) -> Optional[str]:
        """Signal the in-flight stream to abort. Safe to call from any thread."""
        cancelled_id = self._active_request_id
        self._cancel_event.set()
        return cancelled_id

    def reset_cancel(self) -> None:
        self._cancel_event = asyncio.Event()

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        target_model: str,
        stream: bool,
        profile: str,
        temperature: Optional[float],
        keep_alive: Optional[str],
    ) -> Dict[str, Any]:
        options = inference_config.ollama_options(profile=profile)
        if temperature is not None:
            options["temperature"] = temperature
        return {
            "model": target_model,
            "messages": messages,
            "stream": stream,
            "keep_alive": keep_alive or inference_config.keep_alive,
            "options": options,
        }

    async def is_available(self) -> bool:
        """Check if Ollama service is responding at base_url."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Fetch list of pulled model names from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    return models
                return []
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive status report for Ollama service."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    has_default = any(self.default_model in m for m in models)
                    return {
                        "online": True,
                        "provider": self.name,
                        "endpoint": self.base_url,
                        "available_models": models,
                        "active_model": self.default_model,
                        "model_ready": has_default or len(models) > 0,
                        "inference": inference_config.snapshot(),
                        "message": (
                            f"Ollama online with {len(models)} model(s) available."
                            if models
                            else f"Ollama online, but no models found. Run: ollama run {self.default_model}"
                        )
                    }
        except httpx.ConnectError:
            return {
                "online": False,
                "provider": self.name,
                "endpoint": self.base_url,
                "available_models": [],
                "active_model": self.default_model,
                "model_ready": False,
                "inference": inference_config.snapshot(),
                "message": (
                    f"Ollama is offline or unreachable at {self.base_url}. "
                    "Start it by launching the Ollama application or running 'ollama serve' in your terminal."
                )
            }
        except Exception as e:
            return {
                "online": False,
                "provider": self.name,
                "endpoint": self.base_url,
                "available_models": [],
                "active_model": self.default_model,
                "model_ready": False,
                "inference": inference_config.snapshot(),
                "message": f"Ollama connection error: {str(e)}"
            }

    def _offline_error(self, target_model: str) -> Dict[str, Any]:
        return {
            "success": False,
            "error_type": "SERVICE_OFFLINE",
            "content": (
                "NOVA Neural Core cannot reach the local Ollama engine.\n\n"
                "Status: OFFLINE\n"
                f"Target Endpoint: {self.base_url}\n\n"
                "Resolution:\n"
                "1. Verify Ollama is installed.\n"
                "2. Start Ollama from Windows Start menu or run 'ollama serve' in PowerShell.\n"
                f"3. Run 'ollama run {target_model}' to ensure your neural weights are loaded."
            ),
            "model": target_model,
            "provider": self.name
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        profile: str = "text",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send chat prompt to Ollama (non-stream). Prefer chat_stream for UI/voice.
        """
        collected: List[str] = []
        final: Dict[str, Any] = {}
        async for event in self.chat_stream(
            messages,
            model=model,
            temperature=temperature,
            profile=profile,
            request_id=request_id,
        ):
            if event.get("type") == "token":
                collected.append(event.get("content", ""))
            elif event.get("type") in ("done", "error"):
                final = event
        if final.get("type") == "error":
            return {
                "success": False,
                "error_type": final.get("error_type", "API_ERROR"),
                "content": final.get("content", ""),
                "model": model or self.default_model,
                "provider": self.name,
                "request_id": final.get("request_id"),
            }
        return {
            "success": True,
            "content": "".join(collected) or final.get("content", ""),
            "model": final.get("model", model or self.default_model),
            "provider": self.name,
            "request_id": final.get("request_id"),
            "metrics": final.get("metrics", {}),
        }

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        profile: str = "text",
        request_id: Optional[str] = None,
        on_first_token: Optional[Callable[[], None]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Yield token/done/error events. One HTTP request per call."""
        target_model = model or self.default_model
        rid = request_id or new_request_id()
        trace = InferenceTrace(request_id=rid, source=profile)
        async with self._lock:
            self._call_count += 1
            call_index = self._call_count
        self.reset_cancel()
        self._active_request_id = rid
        queue_wait_ms = 0.0
        first_token = False
        prompt_chars = sum(len(m.get("content") or "") for m in messages)

        payload = self._build_payload(
            messages, target_model, True, profile, temperature, inference_config.keep_alive
        )
        logger.info(
            "ollama_request request_id=%s model=%s profile=%s msg_count=%s prompt_chars=%s options=%s keep_alive=%s call_index=%s",
            rid,
            target_model,
            profile,
            len(messages),
            prompt_chars,
            payload.get("options"),
            payload.get("keep_alive"),
            call_index,
        )

        t_http = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as res:
                    if res.status_code == 404:
                        yield {
                            "type": "error",
                            "error_type": "MODEL_NOT_FOUND",
                            "content": (
                                f"Model '{target_model}' is not installed locally in Ollama.\n\n"
                                f"To install it, open terminal and run:\n`ollama run {target_model}`\n\n"
                                f"Or pull another lightweight model such as:\n`ollama run llama3.2:1b`"
                            ),
                            "model": target_model,
                            "request_id": rid,
                        }
                        return
                    if res.status_code != 200:
                        body = await res.aread()
                        yield {
                            "type": "error",
                            "error_type": "API_ERROR",
                            "content": f"Ollama returned HTTP status {res.status_code}: {body.decode('utf-8', errors='replace')[:400]}",
                            "model": target_model,
                            "request_id": rid,
                        }
                        return

                    async for line in res.aiter_lines():
                        if self._cancel_event.is_set():
                            logger.info("ollama_cancelled request_id=%s", rid)
                            yield {
                                "type": "error",
                                "error_type": "CANCELLED",
                                "content": "",
                                "model": target_model,
                                "request_id": rid,
                            }
                            return
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        msg = data.get("message") or {}
                        piece = msg.get("content") or ""
                        if piece:
                            if not first_token:
                                first_token = True
                                ttft = round((time.perf_counter() - t_http) * 1000.0, 2)
                                trace.metrics["ttft_ms"] = ttft
                                trace.metrics["queue_wait_ms"] = queue_wait_ms
                                if on_first_token:
                                    on_first_token()
                            yield {
                                "type": "token",
                                "content": piece,
                                "request_id": rid,
                                "model": target_model,
                            }
                        if data.get("done"):
                            trace.record_tokens(
                                prompt_eval_count=data.get("prompt_eval_count"),
                                eval_count=data.get("eval_count"),
                                prompt_eval_duration_ns=data.get("prompt_eval_duration"),
                                eval_duration_ns=data.get("eval_duration"),
                                total_duration_ns=data.get("total_duration"),
                                load_duration_ns=data.get("load_duration"),
                            )
                            metrics = trace.finalize({
                                "ollama_calls": 1,
                                "profile": profile,
                                "model": target_model,
                                "prompt_chars": prompt_chars,
                                "options": payload.get("options"),
                            })
                            store_trace(metrics)
                            yield {
                                "type": "done",
                                "content": "",
                                "model": target_model,
                                "request_id": rid,
                                "metrics": metrics,
                            }
                            return
        except httpx.ConnectError:
            yield {**self._offline_error(target_model), "type": "error", "request_id": rid}
        except httpx.ReadTimeout:
            yield {
                "type": "error",
                "error_type": "TIMEOUT",
                "content": (
                    f"Inference request for model '{target_model}' timed out after 180 seconds. "
                    "Reduce num_ctx / num_predict in Settings, or keep a smaller local model loaded."
                ),
                "model": target_model,
                "request_id": rid,
            }
        except Exception as e:
            yield {
                "type": "error",
                "error_type": "UNKNOWN_ERROR",
                "content": f"Neural bridge exception: {str(e)}",
                "model": target_model,
                "request_id": rid,
            }
        finally:
            self._active_request_id = None
