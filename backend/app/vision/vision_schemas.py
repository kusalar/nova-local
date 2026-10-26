from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class CaptureTarget(str, Enum):
    PRIMARY = "PRIMARY"
    ACTIVE_WINDOW = "ACTIVE_WINDOW"
    ALL_MONITORS = "ALL_MONITORS"
    MONITOR_INDEX = "MONITOR_INDEX"

class ImageFormat(str, Enum):
    PNG = "PNG"
    JPEG = "JPEG"

class VisionMode(str, Enum):
    OCR_ONLY = "OCR_ONLY"
    MULTIMODAL_VLM = "MULTIMODAL_VLM"
    HYBRID = "HYBRID"

class RetentionPolicy(str, Enum):
    EPHEMERAL = "EPHEMERAL"       # Deleted immediately after analysis
    SESSION = "SESSION"           # Retained until session clear or app restart
    PERSISTENT = "PERSISTENT"     # Retained with explicit user request

class MonitorInfo(BaseModel):
    index: int
    name: str
    x: int
    y: int
    width: int
    height: int
    is_primary: bool = False
    scale_factor: float = 1.0

class WindowInfo(BaseModel):
    handle: int
    title: str
    process_name: str
    app_name: str
    left: int
    top: int
    width: int
    height: int
    is_active: bool = False
    is_minimized: bool = False
    is_sensitive: bool = False

class CaptureMetadata(BaseModel):
    capture_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    target: CaptureTarget
    format: ImageFormat = ImageFormat.PNG
    width: int
    height: int
    original_width: int
    original_height: int
    file_path: Optional[str] = None
    file_size_bytes: int = 0
    window_info: Optional[WindowInfo] = None
    monitor_info: Optional[MonitorInfo] = None
    base64_preview: Optional[str] = None

class OcrWord(BaseModel):
    text: str
    confidence: float = 1.0
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

class OcrLine(BaseModel):
    text: str
    confidence: float = 1.0
    words: List[OcrWord] = Field(default_factory=list)
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

class OcrRegion(BaseModel):
    region_id: int
    lines: List[OcrLine] = Field(default_factory=list)
    text: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

class OcrResult(BaseModel):
    total_lines: int = 0
    total_words: int = 0
    full_text: str = ""
    structured_text: str = ""
    lines: List[OcrLine] = Field(default_factory=list)
    regions: List[OcrRegion] = Field(default_factory=list)
    confidence: float = 1.0
    redacted_count: int = 0
    duration_ms: float = 0.0

class VisionSettings(BaseModel):
    enabled: bool = True
    retention_policy: RetentionPolicy = RetentionPolicy.EPHEMERAL
    auto_redact_sensitive: bool = True
    exclude_sensitive_windows: bool = True
    default_monitor: int = 0
    max_image_dimension: int = 1280
    jpeg_quality: int = 85
    vision_model_name: Optional[str] = None
    ocr_engine: str = "auto"   # "auto", "windows_ocr", "tesseract", "fallback"

class VisionStatus(BaseModel):
    supported: bool = True
    active_engine: str
    vision_model_available: bool = False
    vision_model_name: Optional[str] = None
    monitors_count: int = 1
    active_window: Optional[WindowInfo] = None
    temporary_captures_count: int = 0
    settings: VisionSettings

class VisualAnalysisRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Question or instruction about the screen")
    capture_target: CaptureTarget = CaptureTarget.PRIMARY
    monitor_index: Optional[int] = None
    use_existing_capture_id: Optional[str] = None
    project_id: Optional[str] = None
    include_ocr: bool = True

class VisualAnalysisResponse(BaseModel):
    answer: str
    capture_metadata: Optional[CaptureMetadata] = None
    ocr_result: Optional[OcrResult] = None
    active_window: Optional[WindowInfo] = None
    project_context: Optional[str] = None
    duration_ms: float = 0.0
    model_used: str = "qwen3:4b"
    vision_mode: VisionMode = VisionMode.OCR_ONLY
