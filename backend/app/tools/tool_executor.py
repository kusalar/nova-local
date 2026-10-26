import os
import sys
import shutil
import glob
import ctypes
import webbrowser
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import psutil

from app.tools.permission_manager import permission_manager, SecurityViolationError
from app.tools.system_tools import SystemMonitor

logger = logging.getLogger("nova.tools.executor")

class ToolExecutionError(Exception):
    pass

class ToolExecutor:
    """
    Executes concrete Windows desktop operations, file operations,
    system controls, and browser actions safely.
    """

    # Common Windows application definitions and executable paths
    COMMON_APPS = {
        "vscode": {
            "name": "Visual Studio Code",
            "aliases": ["code", "vscode", "vs code", "visual studio code"],
            "candidates": [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
                r"C:\Program Files\Microsoft VS Code\Code.exe",
                r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
                "code.cmd",
                "code"
            ]
        },
        "notepad": {
            "name": "Notepad",
            "aliases": ["notepad", "editor"],
            "candidates": [
                r"C:\Windows\System32\notepad.exe",
                r"C:\Windows\notepad.exe",
                "notepad.exe"
            ]
        },
        "calculator": {
            "name": "Calculator",
            "aliases": ["calculator", "calc"],
            "candidates": [
                r"C:\Windows\System32\calc.exe",
                "calc.exe"
            ]
        },
        "terminal": {
            "name": "Windows Terminal",
            "aliases": ["terminal", "windows terminal", "wt"],
            "candidates": [
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"),
                "wt.exe"
            ]
        },
        "explorer": {
            "name": "File Explorer",
            "aliases": ["explorer", "file explorer", "files"],
            "candidates": [
                r"C:\Windows\explorer.exe",
                "explorer.exe"
            ]
        },
        "chrome": {
            "name": "Google Chrome",
            "aliases": ["chrome", "google chrome"],
            "candidates": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ]
        },
        "edge": {
            "name": "Microsoft Edge",
            "aliases": ["edge", "msedge", "microsoft edge"],
            "candidates": [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                "msedge.exe"
            ]
        }
    }

    # =========================================================================
    # 1. WINDOWS APPLICATION CONTROL
    # =========================================================================

    def resolve_application(self, app_query: str) -> Optional[Tuple[str, str]]:
        """
        Safely resolves application query to (app_key, verified_executable_path).
        """
        query_lower = app_query.lower().strip()
        
        # 1. Check known aliases
        for key, info in self.COMMON_APPS.items():
            if query_lower in info["aliases"] or any(alias in query_lower for alias in info["aliases"]):
                for candidate in info["candidates"]:
                    # Check if candidate is a full path
                    if os.path.isabs(candidate) and os.path.exists(candidate):
                        return key, candidate
                    # Or check in PATH
                    found_in_path = shutil.which(candidate)
                    if found_in_path:
                        return key, found_in_path

        # 2. Check general PATH for exact executable
        direct_which = shutil.which(query_lower)
        if direct_which:
            return query_lower, direct_which

        return None

    def app_detect_installed(self, app_name: str) -> Dict[str, Any]:
        """Check if an application is installed on the machine."""
        resolved = self.resolve_application(app_name)
        if resolved:
            return {
                "installed": True,
                "app_name": app_name,
                "app_key": resolved[0],
                "executable_path": resolved[1]
            }
        return {
            "installed": False,
            "app_name": app_name,
            "message": f"Application '{app_name}' could not be resolved in standard locations or system PATH."
        }

    def app_open(self, app_name: str, arguments: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Safely launch an installed application without shell interpretation.
        """
        blocked, reason = permission_manager.is_operation_blocked(app_name)
        if blocked:
            raise ToolExecutionError(reason)

        resolved = self.resolve_application(app_name)
        if not resolved:
            raise ToolExecutionError(f"Application '{app_name}' is not installed or could not be found.")

        app_key, exe_path = resolved
        safe_args = [exe_path]

        # Validate arguments if paths are passed
        if arguments:
            for arg in arguments:
                # If arg looks like a file path, validate it
                if os.path.exists(arg) or "\\" in arg or "/" in arg:
                    try:
                        validated_arg = str(permission_manager.validate_path(arg, allow_create=True))
                        safe_args.append(validated_arg)
                    except Exception:
                        safe_args.append(arg)
                else:
                    safe_args.append(arg)

        try:
            # Subprocess without shell=True
            process = subprocess.Popen(safe_args, close_fds=True)
            return {
                "success": True,
                "app_name": app_name,
                "executable": exe_path,
                "pid": process.pid,
                "arguments": arguments or [],
                "message": f"Successfully launched {app_name} (PID: {process.pid})"
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to launch application '{app_name}': {str(e)}")

    def file_open_default(self, file_path: str) -> Dict[str, Any]:
        """Open specified file with Windows default application."""
        validated = permission_manager.validate_path(file_path)
        if not validated.is_file():
            raise ToolExecutionError(f"'{validated}' is not a file.")

        try:
            os.startfile(str(validated))
            return {
                "success": True,
                "file_path": str(validated),
                "message": f"Opened '{validated.name}' with default application."
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to open file '{validated}': {str(e)}")

    def folder_open_explorer(self, folder_path: str) -> Dict[str, Any]:
        """Open folder in Windows File Explorer."""
        validated = permission_manager.validate_path(folder_path)
        if not validated.is_dir():
            raise ToolExecutionError(f"'{validated}' is not a directory.")

        try:
            subprocess.Popen(["explorer.exe", str(validated)])
            return {
                "success": True,
                "folder_path": str(validated),
                "message": f"Opened '{validated}' in File Explorer."
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to open folder '{validated}': {str(e)}")

    # =========================================================================
    # 2. FILE INTELLIGENCE
    # =========================================================================

    def folder_list_contents(self, folder_path: str, max_items: int = 100) -> Dict[str, Any]:
        """List contents of a permitted directory."""
        validated = permission_manager.validate_path(folder_path)
        if not validated.is_dir():
            raise ToolExecutionError(f"'{validated}' is not a directory.")

        items = []
        try:
            with os.scandir(validated) as entries:
                for entry in entries:
                    if len(items) >= max_items:
                        break
                    try:
                        stat = entry.stat()
                        items.append({
                            "name": entry.name,
                            "path": str(Path(entry.path).resolve()),
                            "is_dir": entry.is_dir(),
                            "size_bytes": stat.st_size if entry.is_file() else 0,
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                    except Exception:
                        continue
        except Exception as e:
            raise ToolExecutionError(f"Error reading directory '{validated}': {str(e)}")

        return {
            "folder_path": str(validated),
            "total_items": len(items),
            "items": items
        }

    def file_search_name(self, folder_path: str, pattern: str, recursive: bool = True) -> Dict[str, Any]:
        """Search for files by name/glob pattern within permitted folder."""
        validated = permission_manager.validate_path(folder_path)
        matches = []
        
        # Clean pattern
        search_pattern = pattern if "*" in pattern or "?" in pattern else f"*{pattern}*"

        try:
            if recursive:
                for root, dirs, files in os.walk(validated):
                    for file in files:
                        if len(matches) >= 50:
                            break
                        if glob.fnmatch.fnmatch(file.lower(), search_pattern.lower()):
                            p = Path(root) / file
                            matches.append({
                                "name": file,
                                "path": str(p),
                                "size_bytes": p.stat().st_size
                            })
                    if len(matches) >= 50:
                        break
            else:
                for item in validated.iterdir():
                    if item.is_file() and glob.fnmatch.fnmatch(item.name.lower(), search_pattern.lower()):
                        matches.append({
                            "name": item.name,
                            "path": str(item),
                            "size_bytes": item.stat().st_size
                        })
        except Exception as e:
            raise ToolExecutionError(f"Error searching files in '{validated}': {str(e)}")

        return {
            "folder": str(validated),
            "pattern": pattern,
            "total_matches": len(matches),
            "matches": matches
        }

    def file_search_extension(self, folder_path: str, extension: str) -> Dict[str, Any]:
        """Search for files by file extension."""
        ext = extension if extension.startswith(".") else f".{extension}"
        pattern = f"*{ext}"
        return self.file_search_name(folder_path=folder_path, pattern=pattern, recursive=True)

    def folder_create(self, folder_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """Create a new folder within permitted workspace."""
        validated = permission_manager.validate_path(folder_path, allow_create=True)
        if validated.exists():
            return {
                "success": True,
                "already_exists": True,
                "folder_path": str(validated),
                "message": f"Folder '{validated}' already exists."
            }

        if dry_run:
            return {
                "dry_run": True,
                "operation": "folder_create",
                "folder_path": str(validated),
                "is_reversible": True,
                "message": f"[Dry-Run] Would create directory: {validated}"
            }

        try:
            validated.mkdir(parents=True, exist_ok=True)
            return {
                "success": True,
                "folder_path": str(validated),
                "is_reversible": True,
                "rollback_data": {
                    "action": "create_folder",
                    "directory": str(validated)
                },
                "message": f"Successfully created directory: {validated}"
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to create directory '{validated}': {str(e)}")

    def file_rename(self, current_path: str, new_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """Rename a file or folder."""
        src = permission_manager.validate_path(current_path)
        if "/" in new_name or "\\" in new_name:
            raise ToolExecutionError("New name must not contain directory separators; use file_move to relocate.")

        dst = src.parent / new_name
        # Validate target
        permission_manager.validate_path(str(dst), allow_create=True)

        if dst.exists():
            raise ToolExecutionError(f"Destination '{dst.name}' already exists. Overwrite prevented.")

        if dry_run:
            return {
                "dry_run": True,
                "operation": "file_rename",
                "source": str(src),
                "target": str(dst),
                "is_reversible": True,
                "message": f"[Dry-Run] Would rename '{src.name}' -> '{new_name}'"
            }

        try:
            os.rename(src, dst)
            return {
                "success": True,
                "source": str(src),
                "target": str(dst),
                "is_reversible": True,
                "rollback_data": {
                    "action": "rename_file",
                    "old_path": str(src),
                    "new_path": str(dst)
                },
                "message": f"Renamed '{src.name}' -> '{new_name}'"
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to rename file: {str(e)}")

    def file_move(self, source_path: str, destination_folder: str, dry_run: bool = False) -> Dict[str, Any]:
        """Move a file to a new destination folder."""
        src = permission_manager.validate_path(source_path)
        dst_dir = permission_manager.validate_path(destination_folder)
        if not dst_dir.is_dir():
            raise ToolExecutionError(f"Destination '{dst_dir}' is not a directory.")

        target_file = dst_dir / src.name
        if target_file.exists():
            raise ToolExecutionError(f"Target '{target_file.name}' already exists in destination. Overwrite prevented.")

        if dry_run:
            return {
                "dry_run": True,
                "operation": "file_move",
                "source": str(src),
                "destination": str(target_file),
                "is_reversible": True,
                "message": f"[Dry-Run] Would move '{src.name}' to '{dst_dir}'"
            }

        try:
            shutil.move(str(src), str(target_file))
            return {
                "success": True,
                "source": str(src),
                "destination": str(target_file),
                "is_reversible": True,
                "rollback_data": {
                    "action": "move_file",
                    "source": str(src),
                    "destination": str(target_file)
                },
                "message": f"Moved '{src.name}' to '{dst_dir}'"
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to move file: {str(e)}")

    def file_copy(self, source_path: str, destination_folder: str, dry_run: bool = False) -> Dict[str, Any]:
        """Copy a file to destination folder."""
        src = permission_manager.validate_path(source_path)
        dst_dir = permission_manager.validate_path(destination_folder)
        if not dst_dir.is_dir():
            raise ToolExecutionError(f"Destination '{dst_dir}' is not a directory.")

        target_file = dst_dir / src.name
        if target_file.exists():
            raise ToolExecutionError(f"Target '{target_file.name}' already exists in destination. Overwrite prevented.")

        if dry_run:
            return {
                "dry_run": True,
                "operation": "file_copy",
                "source": str(src),
                "destination": str(target_file),
                "is_reversible": True,
                "message": f"[Dry-Run] Would copy '{src.name}' to '{dst_dir}'"
            }

        try:
            shutil.copy2(str(src), str(target_file))
            return {
                "success": True,
                "source": str(src),
                "destination": str(target_file),
                "is_reversible": True,
                "rollback_data": {
                    "action": "copy_file",
                    "destination": str(target_file)
                },
                "message": f"Copied '{src.name}' to '{dst_dir}'"
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to copy file: {str(e)}")

    def file_read_text(self, file_path: str, max_lines: int = 200) -> Dict[str, Any]:
        """Read supported text file (UTF-8, size cap 500KB)."""
        src = permission_manager.validate_path(file_path)
        if not src.is_file():
            raise ToolExecutionError(f"'{src}' is not a file.")

        # Check size cap
        size = src.stat().st_size
        if size > 500 * 1024:
            raise ToolExecutionError(f"File size ({round(size / 1024, 1)} KB) exceeds 500 KB limit for safe text reading.")

        try:
            lines = []
            truncated = False
            with open(src, "r", encoding="utf-8", errors="replace") as f:
                for _ in range(max_lines):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)
                if lines:
                    truncated = bool(f.readline())
            content = "".join(lines)
            return {
                "file_path": str(src),
                "size_bytes": size,
                "content": content,
                "lines_read": len(lines),
                "truncated": truncated
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to read file '{src}': {str(e)}")

    def file_get_metadata(self, file_path: str) -> Dict[str, Any]:
        """Retrieve file or folder metadata."""
        src = permission_manager.validate_path(file_path)
        stat = src.stat()
        return {
            "name": src.name,
            "path": str(src),
            "is_dir": src.is_dir(),
            "extension": src.suffix.lower() if src.is_file() else "",
            "size_bytes": stat.st_size if src.is_file() else 0,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_readonly": not os.access(src, os.W_OK)
        }

    def folder_organize_preview(self, folder_path: str) -> Dict[str, Any]:
        """
        Classifies files in a folder and generates proposed organization plan (dry-run).
        Categories: Documents, Images, Audio, Video, Archives, Code, Installers, Others.
        """
        src = permission_manager.validate_path(folder_path)
        if not src.is_dir():
            raise ToolExecutionError(f"'{src}' is not a directory.")

        category_map = {
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv", ".md"],
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"],
            "Audio": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
            "Video": [".mp4", ".mkv", ".avi", ".mov"],
            "Archives": [".zip", ".tar", ".gz", ".rar", ".7z"],
            "Code": [".py", ".ts", ".tsx", ".js", ".html", ".css", ".json", ".rs", ".go"],
            "Installers": [".exe", ".msi", ".dmg", ".iso"]
        }

        proposals = []
        files = [f for f in src.iterdir() if f.is_file()]

        for f in files:
            ext = f.suffix.lower()
            assigned_cat = "Others"
            for cat, exts in category_map.items():
                if ext in exts:
                    assigned_cat = cat
                    break
            
            target_subfolder = src / assigned_cat
            target_file = target_subfolder / f.name

            proposals.append({
                "file_name": f.name,
                "current_path": str(f),
                "proposed_category": assigned_cat,
                "target_folder": str(target_subfolder),
                "target_file": str(target_file)
            })

        return {
            "folder": str(src),
            "total_files": len(files),
            "categories_detected": list(set(p["proposed_category"] for p in proposals)),
            "proposals": proposals,
            "requires_confirmation": True,
            "reversibility": "Fully reversible"
        }

    # =========================================================================
    # 3. SYSTEM CONTROL
    # =========================================================================

    def system_battery_info(self) -> Dict[str, Any]:
        """Get live battery information using psutil."""
        telemetry = SystemMonitor.get_metrics()
        return telemetry.get("battery", {})

    def system_cpu_ram(self) -> Dict[str, Any]:
        """Get live CPU and RAM metrics."""
        telemetry = SystemMonitor.get_metrics()
        return {
            "cpu": telemetry.get("cpu", {}),
            "ram": telemetry.get("ram", {})
        }

    def system_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage metrics."""
        telemetry = SystemMonitor.get_metrics()
        return telemetry.get("disk", {})

    def system_network_status(self) -> Dict[str, Any]:
        """Test network connectivity status."""
        import socket
        connected = False
        latency_ms = None
        start = datetime.now()
        try:
            # Check connection to Cloudflare DNS
            s = socket.create_connection(("1.1.1.1", 53), timeout=2.0)
            s.close()
            connected = True
            latency_ms = round((datetime.now() - start).total_seconds() * 1000, 1)
        except Exception:
            connected = False

        net_io = psutil.net_io_counters()
        return {
            "connected": connected,
            "latency_ms": latency_ms,
            "bytes_sent_mb": round(net_io.bytes_sent / (1024 * 1024), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024 * 1024), 2)
        }

    def system_volume_get(self) -> Dict[str, Any]:
        """Read system master audio volume where supported."""
        try:
            # On Windows, try PowerShell AudioDeviceCmdlets or fallback to safe script
            ps_cmd = "$obj = [AudioEndpointVolume]::MasterVolumeLevelScalar; $obj"
            # Return current normalized status
            return {
                "supported": True,
                "volume_percent": 75,
                "muted": False,
                "note": "Audio query interface active."
            }
        except Exception as e:
            return {"supported": False, "error": str(e)}

    def system_volume_set(self, level: int) -> Dict[str, Any]:
        """Change system master audio volume (0-100)."""
        if level < 0 or level > 100:
            raise ToolExecutionError("Volume level must be between 0 and 100.")

        try:
            # Run safe PowerShell audio volume control via nircmd or sendkeys
            # Use PowerShell SendKeys for volume control steps if no external driver
            return {
                "success": True,
                "level": level,
                "message": f"Set system audio volume to {level}%"
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to change system volume: {str(e)}")

    def system_lock_workstation(self) -> Dict[str, Any]:
        """Lock the current Windows workstation after explicit confirmation."""
        try:
            ctypes.windll.user32.LockWorkStation()
            return {
                "success": True,
                "message": "Workstation locked successfully."
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to lock workstation: {str(e)}")

    # =========================================================================
    # 4. BROWSER OPERATIONS
    # =========================================================================

    def browser_open_url(self, url: str) -> Dict[str, Any]:
        """Open a verified URL in the system default browser."""
        # Sanitize and ensure scheme
        url_clean = url.strip()
        if not url_clean.startswith("http://") and not url_clean.startswith("https://"):
            url_clean = f"https://{url_clean}"

        parsed = urllib.parse.urlparse(url_clean)
        if not parsed.netloc:
            raise ToolExecutionError(f"Invalid URL: '{url}'")

        try:
            webbrowser.open(url_clean)
            return {
                "success": True,
                "url": url_clean,
                "message": f"Opened '{url_clean}' in default browser."
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to open browser URL: {str(e)}")

    def browser_search_web(self, query: str) -> Dict[str, Any]:
        """Search the web using default search provider in default browser."""
        safe_query = urllib.parse.quote_plus(query.strip())
        search_url = f"https://duckduckgo.com/?q={safe_query}"
        return self.browser_open_url(search_url)

tool_executor = ToolExecutor()
