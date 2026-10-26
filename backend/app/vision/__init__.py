"""
NOVA v0.5 - Multimodal Visual Intelligence & Screen Awareness
"""

from .vision_schemas import (
    CaptureTarget, ImageFormat, VisionMode, RetentionPolicy,
    MonitorInfo, WindowInfo, CaptureMetadata, OcrWord, OcrLine,
    OcrRegion, OcrResult, VisionSettings, VisionStatus,
    VisualAnalysisRequest, VisualAnalysisResponse
)
from .window_manager import WindowManager
from .privacy_filter import PrivacyFilter
from .image_processor import ImageProcessor
from .screen_capture import ScreenCaptureEngine, ScreenCaptureError
from .ocr_engine import OcrEngine
from .visual_context import VisualContextBuilder
from .vision_manager import VisionManager, vision_manager

__all__ = [
    "CaptureTarget", "ImageFormat", "VisionMode", "RetentionPolicy",
    "MonitorInfo", "WindowInfo", "CaptureMetadata", "OcrWord", "OcrLine",
    "OcrRegion", "OcrResult", "VisionSettings", "VisionStatus",
    "VisualAnalysisRequest", "VisualAnalysisResponse",
    "WindowManager", "PrivacyFilter", "ImageProcessor",
    "ScreenCaptureEngine", "ScreenCaptureError", "OcrEngine",
    "VisualContextBuilder", "VisionManager", "vision_manager"
]
