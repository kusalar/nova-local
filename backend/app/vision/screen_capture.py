import ctypes
from ctypes import wintypes
import logging
from typing import List, Optional, Tuple
from PIL import Image, ImageGrab
from .vision_schemas import CaptureTarget, MonitorInfo, WindowInfo, ImageFormat, CaptureMetadata
from .window_manager import WindowManager
from .image_processor import ImageProcessor
from .privacy_filter import PrivacyFilter

logger = logging.getLogger("nova.vision.capture")

class ScreenCaptureError(Exception):
    """Raised when screen or window capture fails."""
    pass

class ScreenCaptureEngine:
    """
    Cross-monitor and window capture engine for Windows.
    Provides monitor enumeration, display scaling detection,
    active window isolation, and error resilience.
    """

    def __init__(self, image_processor: Optional[ImageProcessor] = None):
        self.processor = image_processor or ImageProcessor()
        self._user32 = ctypes.windll.user32

    def get_monitors(self) -> List[MonitorInfo]:
        """
        Enumerates all active display monitors with their bounds and primary status.
        """
        monitors: List[MonitorInfo] = []

        try:
            # MonitorEnumProc callback
            MonitorEnumProc = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HMONITOR,
                wintypes.HDC,
                ctypes.POINTER(wintypes.RECT),
                wintypes.LPARAM
            )

            # MONITORINFOEXW struct
            class MONITORINFOEXW(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD),
                    ("szDevice", wintypes.WCHAR * 32)
                ]

            CCHDEVICENAME = 32

            def enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
                info = MONITORINFOEXW()
                info.cbSize = ctypes.sizeof(MONITORINFOEXW)
                if self._user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                    rc = info.rcMonitor
                    is_primary = bool(info.dwFlags & 1) # MONITORINFOF_PRIMARY = 1
                    monitors.append(MonitorInfo(
                        index=len(monitors),
                        name=info.szDevice or f"DISPLAY_{len(monitors)+1}",
                        x=rc.left,
                        y=rc.top,
                        width=rc.right - rc.left,
                        height=rc.bottom - rc.top,
                        is_primary=is_primary,
                        scale_factor=1.0 # Windows DPI scale
                    ))
                return True

            cb = MonitorEnumProc(enum_proc)
            self._user32.EnumDisplayMonitors(None, None, cb, 0)
        except Exception as e:
            logger.warning(f"Failed to enumerate monitors via EnumDisplayMonitors: {e}")

        # Fallback to primary screen metrics if EnumDisplayMonitors yielded nothing
        if not monitors:
            try:
                w = self._user32.GetSystemMetrics(0) # SM_CXSCREEN
                h = self._user32.GetSystemMetrics(1) # SM_CYSCREEN
                monitors.append(MonitorInfo(
                    index=0,
                    name="Primary Display",
                    x=0,
                    y=0,
                    width=w if w > 0 else 1920,
                    height=h if h > 0 else 1080,
                    is_primary=True,
                    scale_factor=1.0
                ))
            except Exception:
                monitors.append(MonitorInfo(
                    index=0,
                    name="Default Display",
                    x=0,
                    y=0,
                    width=1920,
                    height=1080,
                    is_primary=True,
                    scale_factor=1.0
                ))

        return monitors

    def capture_screen(
        self,
        target: CaptureTarget = CaptureTarget.PRIMARY,
        monitor_index: Optional[int] = None,
        format: ImageFormat = ImageFormat.PNG,
        quality: int = 85,
        max_dimension: int = 1280,
        exclude_sensitive_windows: bool = True
    ) -> Tuple[CaptureMetadata, Image.Image]:
        """
        Captures the requested target (Primary, Specific Monitor, All Monitors, or Active Window).
        Enforces privacy boundaries and returns (metadata, processed_image).
        """
        monitors = self.get_monitors()
        window_info: Optional[WindowInfo] = None
        selected_monitor: Optional[MonitorInfo] = None
        bbox: Optional[Tuple[int, int, int, int]] = None

        if target == CaptureTarget.ACTIVE_WINDOW:
            window_info = WindowManager.get_active_window()
            if not window_info or window_info.width <= 0 or window_info.height <= 0:
                raise ScreenCaptureError("No active window with visible bounds detected to capture.")
            
            if exclude_sensitive_windows and window_info.is_sensitive:
                raise ScreenCaptureError(
                    f"Capture blocked: Active window '{window_info.title}' ({window_info.process_name}) "
                    "is recognized as a sensitive credential or security application."
                )

            bbox = (
                window_info.left,
                window_info.top,
                window_info.left + window_info.width,
                window_info.top + window_info.height
            )

        elif target == CaptureTarget.MONITOR_INDEX and monitor_index is not None:
            if 0 <= monitor_index < len(monitors):
                selected_monitor = monitors[monitor_index]
                bbox = (
                    selected_monitor.x,
                    selected_monitor.y,
                    selected_monitor.x + selected_monitor.width,
                    selected_monitor.y + selected_monitor.height
                )
            else:
                raise ScreenCaptureError(f"Monitor index {monitor_index} is out of range (0-{len(monitors)-1}).")

        elif target == CaptureTarget.ALL_MONITORS:
            # PIL ImageGrab all_screens=True grabs the virtual desktop bounding box
            selected_monitor = None
            bbox = None # Handled with all_screens=True

        else: # CaptureTarget.PRIMARY
            primary = next((m for m in monitors if m.is_primary), monitors[0] if monitors else None)
            selected_monitor = primary
            if primary:
                bbox = (primary.x, primary.y, primary.x + primary.width, primary.y + primary.height)

        # Attempt capture via PIL ImageGrab
        try:
            if target == CaptureTarget.ALL_MONITORS:
                raw_image = ImageGrab.grab(all_screens=True)
            elif bbox:
                raw_image = ImageGrab.grab(bbox=bbox, all_screens=True)
            else:
                raw_image = ImageGrab.grab()
        except OSError as e:
            logger.error(f"ImageGrab screen capture failed: {e}")
            raise ScreenCaptureError(f"Desktop screen capture failed (system or session limitation): {e}")
        except Exception as e:
            logger.error(f"Unexpected error capturing screen: {e}")
            raise ScreenCaptureError(f"Failed to capture screen: {e}")

        if not raw_image or raw_image.width <= 0 or raw_image.height <= 0:
            raise ScreenCaptureError("Captured image is empty or invalid.")

        # Save ephemeral copy and generate preview
        metadata, processed_image = self.processor.save_ephemeral(
            image=raw_image,
            target=target,
            format=format,
            quality=quality,
            max_dimension=max_dimension,
            window_info=window_info,
            monitor_info=selected_monitor
        )

        return metadata, processed_image
