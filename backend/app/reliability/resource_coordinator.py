import asyncio
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

logger = logging.getLogger("nova.reliability.resources")

class ResourceCoordinator:
    """
    Hardware-aware resource and concurrency coordinator for NOVA v0.9.
    Constrains heavy local operations (Ollama LLM inference, OCR) to prevent
    CPU saturation and UI stuttering on Intel Core i3 / 12GB hardware.
    """

    def __init__(self):
        # Allow at most 1 heavy model generation concurrently on CPU
        self._inference_semaphore = asyncio.Semaphore(1)
        # Allow at most 1 heavy OCR operation concurrently
        self._ocr_semaphore = asyncio.Semaphore(1)
        self._active_inferences = 0
        self._active_ocr = 0
        self._queued_inferences = 0
        self.max_queued_inferences = 5

    @property
    def metrics(self) -> Dict[str, Any]:
        return {
            "active_inferences": self._active_inferences,
            "queued_inferences": self._queued_inferences,
            "max_concurrent_inferences": 1,
            "active_ocr": self._active_ocr,
            "max_concurrent_ocr": 1
        }

    @asynccontextmanager
    async def acquire_inference_slot(self, timeout: float = 30.0):
        """
        Acquire slot for local LLM inference with backpressure and timeout.
        """
        if self._queued_inferences >= self.max_queued_inferences:
            raise RuntimeError(
                "System busy: Maximum queued inference requests reached. Please try again in a moment."
            )

        self._queued_inferences += 1
        try:
            acquired = False
            try:
                await asyncio.wait_for(self._inference_semaphore.acquire(), timeout=timeout)
                acquired = True
            except asyncio.TimeoutError:
                raise TimeoutError("Inference request timed out waiting for resource slot.")

            self._active_inferences += 1
            try:
                yield
            finally:
                self._active_inferences -= 1
                if acquired:
                    self._inference_semaphore.release()
        finally:
            self._queued_inferences -= 1

    @asynccontextmanager
    async def acquire_ocr_slot(self, timeout: float = 15.0):
        """
        Acquire slot for heavy OCR processing.
        """
        try:
            await asyncio.wait_for(self._ocr_semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("OCR operation timed out waiting for available resource slot.")

        self._active_ocr += 1
        try:
            yield
        finally:
            self._active_ocr -= 1
            self._ocr_semaphore.release()

resource_coordinator = ResourceCoordinator()
