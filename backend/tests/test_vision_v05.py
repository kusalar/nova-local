import pytest
import io
import os
import unittest.mock as mock
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

from app.main import app
from app.vision.vision_schemas import (
    CaptureTarget, ImageFormat, VisionMode, RetentionPolicy,
    WindowInfo, MonitorInfo, VisualAnalysisRequest
)
from app.vision.image_processor import ImageProcessor
from app.vision.privacy_filter import PrivacyFilter
from app.vision.window_manager import WindowManager
from app.vision.screen_capture import ScreenCaptureEngine, ScreenCaptureError
from app.vision.ocr_engine import OcrEngine
from app.vision.visual_context import VisualContextBuilder
from app.vision.vision_manager import VisionManager, vision_manager
from app.ai.model_manager import model_manager
from app.memory.project_memory import project_memory
from app.memory.memory_models import ProjectCreate

client = TestClient(app)

def create_synthetic_test_image(text: str = "NOVA SYSTEM DIAGNOSTICS: OK", width: int = 400, height: int = 100) -> Image.Image:
    """Helper creating a synthetic test image with crisp black-on-white text."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), text, fill=(0, 0, 0))
    return img

# ==========================================
# 1. Image Processor & Resizing Tests
# ==========================================

def test_image_resizing_aspect_ratio():
    processor = ImageProcessor()
    # High-resolution synthetic image 2400x1200 (2:1 aspect ratio)
    large_img = Image.new("RGB", (2400, 1200), color=(100, 100, 100))
    resized, orig_dim = processor.resize_for_efficiency(large_img, max_dimension=1200)

    assert orig_dim == (2400, 1200)
    assert resized.width == 1200
    assert resized.height == 600
    assert resized.width <= 1200
    assert resized.height <= 1200

def test_image_base64_conversion():
    processor = ImageProcessor()
    test_img = create_synthetic_test_image("BASE64 ENCODING TEST", 200, 50)
    
    b64_str = processor.image_to_base64(test_img, format=ImageFormat.PNG)
    assert b64_str.startswith("data:image/png;base64,")

    decoded_img = processor.base64_to_image(b64_str)
    assert decoded_img.size == test_img.size

def test_ephemeral_storage_and_cleanup(tmp_path):
    processor = ImageProcessor(temp_dir=tmp_path)
    test_img = create_synthetic_test_image("STORAGE TEST", 300, 80)

    meta, _ = processor.save_ephemeral(test_img, target=CaptureTarget.PRIMARY)
    assert os.path.exists(meta.file_path)
    assert processor.get_temporary_captures_count() == 1

    cleared = processor.clear_temporary_files()
    assert cleared == 1
    assert processor.get_temporary_captures_count() == 0
    assert not os.path.exists(meta.file_path)

# ==========================================
# 2. Privacy Filter & Redaction Tests
# ==========================================

def test_sensitive_credentials_redaction():
    dirty_text = (
        "Connected with OpenAI key sk-abcdef1234567890abcdef1234567890 and "
        "Google API key AIzaSyD1234567890123456789012345678901 and "
        "GitHub token ghp_1234567890abcdef1234567890abcdef1234. "
        "Authorization: Bearer secret_access_token_12345678. "
        "Master password: password='SuperSecretPassword123!' "
        "Card: 4532-1234-5678-9010."
    )

    redacted, count = PrivacyFilter.redact_text(dirty_text)
    assert count >= 5
    assert "sk-" not in redacted or "[REDACTED" in redacted
    assert "AIza" not in redacted or "[REDACTED" in redacted
    assert "ghp_" not in redacted or "[REDACTED" in redacted
    assert "SuperSecretPassword123!" not in redacted
    assert "4532-1234-5678-9010" not in redacted

def test_sensitive_window_detection():
    # Sensitive password managers and authenticators
    assert PrivacyFilter.is_window_sensitive("1Password - Vault Locked", "1password.exe") is True
    assert PrivacyFilter.is_window_sensitive("Bitwarden Password Manager", "bitwarden.exe") is True
    assert PrivacyFilter.is_window_sensitive("KeePassXC - Master Key Prompt", "keepassxc.exe") is True
    assert PrivacyFilter.is_window_sensitive("Windows Security Consent", "consent.exe") is True

    # Standard windows
    assert PrivacyFilter.is_window_sensitive("Command Center - Visual Studio Code", "code.exe") is False
    assert PrivacyFilter.is_window_sensitive("Google Chrome - React Docs", "chrome.exe") is False
    assert PrivacyFilter.is_window_sensitive("Notepad", "notepad.exe") is False

# ==========================================
# 3. Window Awareness Tests
# ==========================================

def test_window_manager_methods():
    active = WindowManager.get_active_window()
    # On desktop environments, active window may be None or WindowInfo
    if active is not None:
        assert isinstance(active, WindowInfo)
        assert hasattr(active, "handle")
        assert hasattr(active, "process_name")
        assert hasattr(active, "title")

    windows = WindowManager.list_visible_windows()
    assert isinstance(windows, list)
    for w in windows:
        assert isinstance(w, WindowInfo)
        assert w.width >= 0
        assert w.height >= 0

# ==========================================
# 4. Screen Capture Engine (Mocked Synthetic)
# ==========================================

def test_screen_capture_mock_primary():
    synthetic_screen = create_synthetic_test_image("DESKTOP MOCK SCREEN", 1920, 1080)
    engine = ScreenCaptureEngine()

    with mock.patch("PIL.ImageGrab.grab", return_value=synthetic_screen):
        meta, img = engine.capture_screen(target=CaptureTarget.PRIMARY)
        assert meta.original_width == 1920
        assert meta.original_height == 1080
        assert img.width <= 1280
        assert meta.target == CaptureTarget.PRIMARY

def test_screen_capture_blocks_sensitive_window():
    engine = ScreenCaptureEngine()
    sensitive_win = WindowInfo(
        handle=12345,
        title="Bitwarden Password Vault",
        process_name="bitwarden.exe",
        app_name="Bitwarden",
        left=100, top=100, width=800, height=600,
        is_active=True, is_minimized=False, is_sensitive=True
    )

    with mock.patch.object(WindowManager, "get_active_window", return_value=sensitive_win):
        with pytest.raises(ScreenCaptureError) as exc_info:
            engine.capture_screen(target=CaptureTarget.ACTIVE_WINDOW, exclude_sensitive_windows=True)
        assert "sensitive" in str(exc_info.value).lower()

# ==========================================
# 5. Local OCR Engine Tests
# ==========================================

@pytest.mark.asyncio
async def test_ocr_extraction_synthetic_image():
    ocr_engine = OcrEngine(auto_redact=True)
    synthetic_img = create_synthetic_test_image("NOVA OCR SUCCESS: ALL CHECKS PASSED", 400, 100)

    ocr_result = await ocr_engine.extract_text(synthetic_img)
    assert ocr_result is not None
    assert ocr_result.duration_ms >= 0
    assert isinstance(ocr_result.full_text, str)
    assert isinstance(ocr_result.lines, list)

@pytest.mark.asyncio
async def test_ocr_redaction_integration():
    ocr_engine = OcrEngine(auto_redact=True)
    # Synthetic image simulating exposed API key on screen
    secret_text = "API_KEY = sk-123456789012345678901234567890"
    synthetic_img = create_synthetic_test_image(secret_text, 500, 100)

    ocr_result = await ocr_engine.extract_text(synthetic_img)
    # Either recognized text is sanitized or redacted
    if "sk-" in ocr_result.full_text:
        assert "[REDACTED" in ocr_result.full_text or ocr_result.redacted_count > 0

# ==========================================
# 6. Visual Context & Project Memory Tests
# ==========================================

def test_visual_context_project_correlation():
    # Setup test project
    project_memory.get_or_create_project(
        project_name="Nova Assistant",
        tech_stack=["FastAPI", "React", "Tauri", "Python"]
    )

    win = WindowInfo(
        handle=1001,
        title="CommandCenterPage.tsx - Nova Assistant - Visual Studio Code",
        process_name="code.exe",
        app_name="Visual Studio Code",
        left=0, top=0, width=1920, height=1080,
        is_active=True, is_minimized=False, is_sensitive=False
    )

    context_str, resolved_proj, proj_str = VisualContextBuilder.build_context_prompt(
        window_info=win,
        ocr_result=None
    )

    assert "Visual Studio Code" in context_str
    assert "Nova Assistant" in context_str or resolved_proj is not None

# ==========================================
# 7. Vision Manager & Settings Tests
# ==========================================

@pytest.mark.asyncio
async def test_vision_manager_status():
    status = await vision_manager.get_status()
    assert status.supported is True
    assert status.monitors_count >= 1
    assert status.settings.enabled is True
    assert isinstance(status.temporary_captures_count, int)

def test_vision_manager_settings_update():
    new_settings = {
        "retention_policy": RetentionPolicy.SESSION,
        "max_image_dimension": 1600,
        "auto_redact_sensitive": True
    }
    updated = vision_manager.update_settings(new_settings)
    assert updated.retention_policy == RetentionPolicy.SESSION
    assert updated.max_image_dimension == 1600

    # Restore ephemeral default
    vision_manager.update_settings({"retention_policy": RetentionPolicy.EPHEMERAL, "max_image_dimension": 1280})

# ==========================================
# 8. Vision REST API Endpoints Tests
# ==========================================

def test_api_vision_status():
    res = client.get("/api/vision/status")
    assert res.status_code == 200
    data = res.json()
    assert data["supported"] is True
    assert "monitors_count" in data
    assert "settings" in data

def test_api_vision_windows():
    res = client.get("/api/vision/windows")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

def test_api_vision_settings_get_and_patch():
    res = client.get("/api/vision/settings")
    assert res.status_code == 200
    settings_data = res.json()
    assert settings_data["enabled"] is True

    patch_res = client.patch("/api/vision/settings", json={"jpeg_quality": 90})
    assert patch_res.status_code == 200
    assert patch_res.json()["jpeg_quality"] == 90

    # Revert
    client.patch("/api/vision/settings", json={"jpeg_quality": 85})

def test_api_vision_clear():
    res = client.post("/api/vision/clear")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "cleared_count" in data

def test_api_vision_capture_mock():
    synthetic_screen = create_synthetic_test_image("REST API CAPTURE TEST", 800, 600)
    with mock.patch("PIL.ImageGrab.grab", return_value=synthetic_screen):
        res = client.post("/api/vision/capture?target=PRIMARY")
        assert res.status_code == 200
        data = res.json()
        assert "capture_id" in data
        assert data["width"] <= 1280
        assert data["base64_preview"] is not None

def test_api_vision_analyze_mock():
    synthetic_screen = create_synthetic_test_image("ERROR 500: Database Connection Timeout", 800, 400)
    mock_chat_response = {
        "success": True,
        "content": "The screen shows a Database Connection Timeout error (Error 500).",
        "model": "qwen3:4b"
    }

    with mock.patch("PIL.ImageGrab.grab", return_value=synthetic_screen), \
         mock.patch("app.ai.model_manager.model_manager.chat", return_value=mock_chat_response):
        payload = {
            "prompt": "Read the error message on my screen.",
            "capture_target": "PRIMARY",
            "include_ocr": True
        }
        res = client.post("/api/vision/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert "Database Connection Timeout" in data["answer"]
        assert data["model_used"] == model_manager.active_model
