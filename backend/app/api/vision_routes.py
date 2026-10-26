from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from app.vision.vision_schemas import (
    VisionStatus, VisionSettings, WindowInfo, CaptureMetadata,
    OcrResult, VisualAnalysisRequest, VisualAnalysisResponse,
    CaptureTarget, ImageFormat
)
from app.vision.vision_manager import vision_manager
from app.vision.screen_capture import ScreenCaptureError

router = APIRouter(prefix="/vision", tags=["Vision Intelligence"])

@router.get("/status", response_model=VisionStatus)
async def get_vision_status():
    """
    Get current multimodal vision intelligence status, monitor configuration,
    active window details, OCR engine health, and Ollama VLM availability.
    """
    try:
        return await vision_manager.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query vision status: {str(e)}")

@router.get("/windows", response_model=List[WindowInfo])
async def list_desktop_windows():
    """
    Enumerate visible desktop application windows with titles, process names,
    bounds, and sensitivity classifications.
    """
    try:
        return vision_manager.get_visible_windows()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enumerate desktop windows: {str(e)}")

@router.post("/capture", response_model=CaptureMetadata)
async def capture_screen(
    target: CaptureTarget = Query(CaptureTarget.PRIMARY, description="Capture target"),
    monitor_index: Optional[int] = Query(None, description="Monitor index if target is MONITOR_INDEX"),
    format: Optional[ImageFormat] = Query(ImageFormat.PNG, description="Image output format")
):
    """
    Explicit user-initiated desktop screenshot.
    Applies security filtering and downscaling for CPU efficiency.
    """
    try:
        return await vision_manager.capture_screen(
            target=target,
            monitor_index=monitor_index,
            format=format
        )
    except ScreenCaptureError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenshot capture failed: {str(e)}")

@router.post("/analyze", response_model=VisualAnalysisResponse)
async def analyze_visual_screen(request: VisualAnalysisRequest):
    """
    Full multimodal visual intelligence analysis pipeline:
    Captures screen/window -> Privacy filtering -> Local OCR ->
    Project memory enrichment -> Ollama inference.
    """
    try:
        return await vision_manager.analyze_screen(request)
    except ScreenCaptureError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual analysis failed: {str(e)}")

@router.post("/ocr", response_model=OcrResult)
async def extract_screen_ocr(
    capture_id: Optional[str] = Query(None, description="Existing capture ID to extract from")
):
    """
    Extract structured text, bounding boxes, paragraphs, and confidence
    scores from a screenshot using local CPU-friendly OCR.
    """
    try:
        return await vision_manager.extract_ocr(capture_id=capture_id)
    except ScreenCaptureError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")

@router.get("/settings", response_model=VisionSettings)
async def get_vision_settings():
    """
    Retrieve user vision settings, retention policies, and redaction configuration.
    """
    return vision_manager.get_settings()

@router.patch("/settings", response_model=VisionSettings)
async def update_vision_settings(updates: Dict[str, Any] = Body(...)):
    """
    Update vision intelligence settings dynamically.
    """
    try:
        return vision_manager.update_settings(updates)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid settings payload: {str(e)}")

@router.post("/clear")
async def clear_temporary_captures():
    """
    Explicitly purge all ephemeral screenshots and memory capture caches.
    """
    try:
        count = vision_manager.clear_all()
        return {"status": "success", "cleared_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear captures: {str(e)}")
