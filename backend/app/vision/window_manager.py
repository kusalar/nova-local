import os
import sys
import ctypes
from ctypes import wintypes
from typing import List, Optional, Tuple, Dict, Any
import logging
import psutil

from app.vision.vision_schemas import WindowInfo

logger = logging.getLogger("nova.vision.window_manager")

# RECT struct for Win32 GetWindowRect
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

class WindowManager:
    """
    Interrogates active and visible application windows on Windows
    using native Win32 APIs without third-party C-extensions.
    """

    # Common application process-to-human-name mapping
    APP_FRIENDLY_NAMES = {
        "code.exe": "Visual Studio Code",
        "devenv.exe": "Visual Studio",
        "chrome.exe": "Google Chrome",
        "msedge.exe": "Microsoft Edge",
        "firefox.exe": "Mozilla Firefox",
        "notepad.exe": "Notepad",
        "calc.exe": "Calculator",
        "calculatorapp.exe": "Calculator",
        "windowsterminal.exe": "Windows Terminal",
        "explorer.exe": "Windows Explorer",
        "powershell.exe": "PowerShell",
        "cmd.exe": "Command Prompt",
        "slack.exe": "Slack",
        "discord.exe": "Discord",
        "spotify.exe": "Spotify",
        "teams.exe": "Microsoft Teams"
    }

    # Sensitive window signatures that should trigger privacy protection
    SENSITIVE_PROCESSES = {
        "1password.exe",
        "bitwarden.exe",
        "keepass.exe",
        "keepassxc.exe",
        "lastpass.exe",
        "credentialui.exe",
        "consent.exe"  # Windows UAC prompt
    }

    SENSITIVE_TITLE_KEYWORDS = [
        "password",
        "bitwarden",
        "1password",
        "keepass",
        "authenticator",
        "credentials",
        "master key",
        "private key"
    ]

    _default_instance: Optional["WindowManager"] = None

    @classmethod
    def get_instance(cls) -> "WindowManager":
        if cls._default_instance is None:
            cls._default_instance = WindowManager()
        return cls._default_instance

    def __init__(self):
        self.is_windows = os.name == "nt"
        if self.is_windows:
            self.user32 = ctypes.windll.user32
        else:
            self.user32 = None

    @classmethod
    def get_active_window(cls) -> Optional[WindowInfo]:
        """Retrieve details of the current foreground application window."""
        return cls.get_instance()._get_active_window()

    def _get_active_window(self) -> Optional[WindowInfo]:
        if not self.is_windows or not self.user32:
            return None

        try:
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return None
            return self._build_window_info(hwnd, is_active=True)
        except Exception as e:
            logger.warning(f"Error querying active window: {e}")
            return None

    @classmethod
    def list_visible_windows(cls, max_windows: int = 30) -> List[WindowInfo]:
        """Enumerate top-level visible application windows."""
        return cls.get_instance()._list_visible_windows(max_windows)

    def _list_visible_windows(self, max_windows: int = 30) -> List[WindowInfo]:
        if not self.is_windows or not self.user32:
            return []

        windows: List[WindowInfo] = []

        try:
            active_hwnd = self.user32.GetForegroundWindow()

            # EnumWindows callback definition
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

            def enum_proc(hwnd, lParam):
                if len(windows) >= max_windows:
                    return False

                # Only include visible windows with non-empty titles
                if self.user32.IsWindowVisible(hwnd):
                    length = self.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        info = self._build_window_info(hwnd, is_active=(hwnd == active_hwnd))
                        # Filter out empty or zero-size system windows
                        if info and info.width > 30 and info.height > 30 and info.title.strip():
                            windows.append(info)
                return True

            callback = WNDENUMPROC(enum_proc)
            self.user32.EnumWindows(callback, 0)

        except Exception as e:
            logger.warning(f"Error enumerating windows: {e}")

        return windows

    def _build_window_info(self, hwnd: int, is_active: bool = False) -> Optional[WindowInfo]:
        """Extract title, process, dimensions, and privacy flags for a window handle."""
        try:
            # 1. Window Title
            length = self.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()

            # 2. Window Bounds
            rect = RECT()
            self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            width = max(0, rect.right - rect.left)
            height = max(0, rect.bottom - rect.top)

            # 3. Minimized / Iconic state
            is_minimized = bool(self.user32.IsIconic(hwnd))

            # 4. Process Name via psutil
            pid = wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            process_name = "unknown.exe"
            friendly_name = "Desktop Application"

            if pid.value > 0:
                try:
                    proc = psutil.Process(pid.value)
                    process_name = proc.name().lower()
                    friendly_name = self.APP_FRIENDLY_NAMES.get(process_name, proc.name().replace(".exe", "").capitalize())
                except Exception:
                    pass

            # 5. Check if window is sensitive
            is_sensitive = False
            if process_name in self.SENSITIVE_PROCESSES:
                is_sensitive = True
            elif any(kw in title.lower() for kw in self.SENSITIVE_TITLE_KEYWORDS):
                is_sensitive = True

            return WindowInfo(
                handle=hwnd,
                title=title or "Untitled Window",
                process_name=process_name,
                app_name=friendly_name,
                left=rect.left,
                top=rect.top,
                width=width,
                height=height,
                is_active=is_active,
                is_minimized=is_minimized,
                is_sensitive=is_sensitive
            )

        except Exception as e:
            logger.debug(f"Failed to build WindowInfo for hwnd {hwnd}: {e}")
            return None

window_manager = WindowManager()
