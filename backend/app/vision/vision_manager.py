import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image

from .vision_schemas import (
    VisionSettings, VisionStatus, VisionMode, RetentionPolicy,
    CaptureTarget, ImageFormat, CaptureMetadata, OcrResult,
    VisualAnalysisRequest, VisualAnalysisResponse, WindowInfo
)
from .window_manager import WindowManager
from .image_processor import ImageProcessor
from .screen_capture import ScreenCaptureEngine, ScreenCaptureError
from .ocr_engine import OcrEngine
from .privacy_filter import PrivacyFilter
from .visual_context import VisualContextBuilder
from app.ai.model_manager import model_manager

logger = logging.getLogger("nova.vision.manager")

KNOWN_VLM_KEYWORDS = ["vision", "llava", "moondream", "minicpm-v", "bakllava", "cogvlm"]

class VisionManager:
    """
    Central orchestrator for NOVA Multimodal Visual Intelligence.
    Coordinates window awareness, screen capture, privacy redaction,
    local OCR extraction, project memory correlation, and LLM inference.
    """

    def __init__(self):
        self.settings = VisionSettings()
        self.image_processor = ImageProcessor()
        self.capture_engine = ScreenCaptureEngine(image_processor=self.image_processor)
        self.ocr_engine = OcrEngine(auto_redact=self.settings.auto_redact_sensitive)
        self._cache: Dict[str, Tuple[CaptureMetadata, Image.Image, Optional[OcrResult]]] = {}

    def get_settings(self) -> VisionSettings:
        return self.settings

    def update_settings(self, updates: Dict[str, Any]) -> VisionSettings:
        for k, v in updates.items():
            if hasattr(self.settings, k) and v is not None:
                setattr(self.settings, k, v)
        self.ocr_engine.auto_redact = self.settings.auto_redact_sensitive
        return self.settings

    async def get_status(self) -> VisionStatus:
        """
        Inspects system state, active window, display monitors, and Ollama VLM availability.
        """
        monitors = self.capture_engine.get_monitors()
        active_window = WindowManager.get_active_window()
        temp_count = self.image_processor.get_temporary_captures_count()

        # Check for local vision models in Ollama
        vlm_available = False
        detected_vlm = None
        try:
            available_models = await model_manager.active_provider.list_models()
            for m in available_models:
                m_lower = m.lower()
                if any(kw in m_lower for kw in KNOWN_VLM_KEYWORDS):
                    vlm_available = True
                    detected_vlm = m
                    break
        except Exception as e:
            logger.warning(f"Could not inspect Ollama models for VLM: {e}")

        # Active OCR engine description
        engine_str = self.ocr_engine.engine_name

        return VisionStatus(
            supported=True,
            active_engine=engine_str,
            vision_model_available=vlm_available,
            vision_model_name=self.settings.vision_model_name or detected_vlm,
            monitors_count=len(monitors),
            active_window=active_window,
            temporary_captures_count=temp_count,
            settings=self.settings
        )

    def get_visible_windows(self) -> List[WindowInfo]:
        """
        Enumerates all visible top-level desktop windows.
        """
        return WindowManager.list_visible_windows()

    async def capture_screen(
        self,
        target: CaptureTarget = CaptureTarget.PRIMARY,
        monitor_index: Optional[int] = None,
        format: Optional[ImageFormat] = None
    ) -> CaptureMetadata:
        """
        Performs explicit, user-initiated screen capture with security filtering.
        """
        if not self.settings.enabled:
            raise ScreenCaptureError("Vision intelligence is currently disabled in settings.")

        fmt = format or ImageFormat.PNG
        metadata, img = self.capture_engine.capture_screen(
            target=target,
            monitor_index=monitor_index if monitor_index is not None else self.settings.default_monitor,
            format=fmt,
            quality=self.settings.jpeg_quality,
            max_dimension=self.settings.max_image_dimension,
            exclude_sensitive_windows=self.settings.exclude_sensitive_windows
        )

        self._cache[metadata.capture_id] = (metadata, img, None)
        return metadata

    async def extract_ocr(self, capture_id: Optional[str] = None, image: Optional[Image.Image] = None) -> OcrResult:
        """
        Runs local OCR on either an existing capture or a provided PIL Image.
        """
        target_img = image
        if not target_img and capture_id and capture_id in self._cache:
            target_img = self._cache[capture_id][1]

        if not target_img:
            # Capture fresh primary screen if none specified
            meta, target_img = self.capture_engine.capture_screen(
                target=CaptureTarget.PRIMARY,
                format=ImageFormat.PNG,
                quality=self.settings.jpeg_quality,
                max_dimension=self.settings.max_image_dimension,
                exclude_sensitive_windows=self.settings.exclude_sensitive_windows
            )
            capture_id = meta.capture_id
            self._cache[capture_id] = (meta, target_img, None)

        ocr_res = await self.ocr_engine.extract_text(
            target_img,
            auto_redact=self.settings.auto_redact_sensitive
        )

        if capture_id and capture_id in self._cache:
            meta, img, _ = self._cache[capture_id]
            self._cache[capture_id] = (meta, img, ocr_res)

        return ocr_res

    async def analyze_screen(self, request: VisualAnalysisRequest) -> VisualAnalysisResponse:
        """
        Full Visual Q&A pipeline:
        1. Capture screen or retrieve cached capture.
        2. Verify privacy and sensitivity boundaries.
        3. Run local OCR.
        4. Construct structured visual context + project memory correlation.
        5. Query Ollama inference model.
        6. Apply retention policy (cleanup if EPHEMERAL).
        """
        start_time = time.perf_counter()

        if not self.settings.enabled:
            raise ScreenCaptureError("Vision intelligence is currently disabled in settings.")

        # Step 1: Capture or fetch existing capture
        metadata: Optional[CaptureMetadata] = None
        img: Optional[Image.Image] = None
        ocr_result: Optional[OcrResult] = None

        if request.use_existing_capture_id and request.use_existing_capture_id in self._cache:
            metadata, img, ocr_result = self._cache[request.use_existing_capture_id]
        else:
            meta, raw_img = self.capture_engine.capture_screen(
                target=request.capture_target,
                monitor_index=request.monitor_index if request.monitor_index is not None else self.settings.default_monitor,
                format=ImageFormat.PNG,
                quality=self.settings.jpeg_quality,
                max_dimension=self.settings.max_image_dimension,
                exclude_sensitive_windows=self.settings.exclude_sensitive_windows
            )
            metadata = meta
            img = raw_img
            self._cache[meta.capture_id] = (meta, img, None)

        # Step 2: Active Window Information
        active_window = metadata.window_info or WindowManager.get_active_window()

        # Step 3: Run OCR if requested
        if request.include_ocr:
            if not ocr_result:
                ocr_result = await self.ocr_engine.extract_text(
                    img,
                    auto_redact=self.settings.auto_redact_sensitive
                )
                if metadata:
                    self._cache[metadata.capture_id] = (metadata, img, ocr_result)

        # Step 4: Build Visual Context & Correlate Project Memory
        visual_context, resolved_project, project_context_str = VisualContextBuilder.build_context_prompt(
            window_info=active_window,
            ocr_result=ocr_result,
            project_id=request.project_id
        )

        # Step 5: Formulate LLM query
        system_prompt = (
            "You are NOVA, an offline AI assistant with visual screen awareness. "
            "You have access to structured information about the user's active window, "
            "locally extracted OCR text from their screen, and relevant project memory. "
            "Answer the user's question accurately, concisely, and directly based on this context. "
            "If an error message is visible, explain the cause and how to fix it. "
            "Keep answers clear, grounded, and concise."
        )

        user_content = f"{visual_context}\n\nUSER QUESTION: {request.prompt}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        chat_response = await model_manager.chat(
            messages=messages,
            model=model_manager.active_model
        )
        answer = chat_response.get("content", "I was unable to analyze the screen content.")

        # Step 6: Enforce retention policy
        if self.settings.retention_policy == RetentionPolicy.EPHEMERAL:
            self.image_processor.clear_temporary_files()
            if metadata and metadata.capture_id in self._cache:
                del self._cache[metadata.capture_id]

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return VisualAnalysisResponse(
            answer=answer,
            capture_metadata=metadata,
            ocr_result=ocr_result,
            active_window=active_window,
            project_context=project_context_str if project_context_str else None,
            duration_ms=round(duration_ms, 2),
            model_used=model_manager.active_model,
            vision_mode=VisionMode.OCR_ONLY
        )

    def clear_all(self) -> int:
        """
        Clears all in-memory capture caches and ephemeral screenshot files.
        """
        self._cache.clear()
        return self.image_processor.clear_temporary_files()

# Global singleton
vision_manager = VisionManager()
