import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import logging
from app.config import settings
from app.tools.tool_schemas import PermissionLevel

logger = logging.getLogger("nova.tools.permissions")

class SecurityViolationError(Exception):
    """Raised when an operation violates security boundaries."""
    pass

class PermissionManager:
    """
    Enforces security boundaries, path sanitization, traversal prevention,
    symlink escape detection, and permission classifications for NOVA v0.4.
    """

    # Blocked tools / shell patterns
    BLOCKED_PATTERNS = [
        r"powershell(\.exe)?",
        r"cmd(\.exe)?",
        r"bash(\.exe)?",
        r"sh(\.exe)?",
        r"reg(edit)?(\.exe)?",
        r"format(\.exe)?",
        r"rmdir\s+/s",
        r"del\s+/f",
        r"drop\s+table",
        r"eval\(",
        r"exec\(",
        r"__import__",
        r"subprocess\.call",
        r"netsh",
        r"vssadmin",
        r"shutdown(\.exe)?",
        r"taskkill(\.exe)?"
    ]

    # Sensitive filenames/paths that must never be read or modified
    SENSITIVE_TARGETS = [
        r"^\.env",
        r"^id_rsa",
        r"^id_ed25519",
        r"^credentials(\..*)?$",
        r"^\.aws",
        r"^\.ssh",
        r"^SAM$",
        r"^SYSTEM$",
        r"^ntds\.dit$",
        r"^web\.config$",
        r"^\.git[\\/]config$",
        r"^master\.key$",
        r"^api_keys?(\..*)?$",
        r"^\.bashrc$",
        r"^\.zshrc$",
        r"^authorized_keys$",
        r"^known_hosts$",
        r"^shadow$",
        r"^passwd$",
        r".*password.*\.txt$",
        r".*secret.*\.json$"
    ]

    def __init__(self, custom_roots: Optional[List[str]] = None):
        self.allowed_roots: List[Path] = []
        self._init_allowed_roots(custom_roots)

    def _init_allowed_roots(self, custom_roots: Optional[List[str]] = None):
        """Initialize and resolve allowed base directories."""
        roots = []
        # 1. NOVA Repository Root
        roots.append(Path(settings.ROOT_DIR).resolve())

        # 2. User Home Directory and standard user libraries
        user_home = Path.home().resolve()
        roots.append(user_home)

        standard_folders = ["Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos", "Projects", "workspace"]
        for folder in standard_folders:
            sub = (user_home / folder).resolve()
            if sub.exists():
                roots.append(sub)

        # 3. Custom configured roots if any
        if custom_roots:
            for r in custom_roots:
                try:
                    p = Path(r).resolve()
                    if p.exists():
                        roots.append(p)
                except Exception:
                    pass

        # Deduplicate while preserving order
        deduped = []
        for r in roots:
            if r not in deduped:
                deduped.append(r)
        self.allowed_roots = deduped
        logger.info(f"Initialized {len(self.allowed_roots)} allowed workspace root(s)")

    def add_allowed_root(self, path_str: str) -> bool:
        """Add a validated directory root dynamically."""
        try:
            p = Path(path_str).resolve()
            if p.exists() and p.is_dir():
                if p not in self.allowed_roots:
                    self.allowed_roots.append(p)
                return True
        except Exception as e:
            logger.warning(f"Failed to add allowed root: {e}")
        return False

    def validate_path(self, target_path: str, allow_create: bool = False) -> Path:
        """
        Validates that a path is safe, free of directory traversal,
        free of symlink escape, and within allowed workspace boundaries.
        Returns resolved Path if safe, otherwise raises SecurityViolationError.
        """
        if not target_path or not isinstance(target_path, str):
            raise SecurityViolationError("Path must be a non-empty string.")

        # Check for directory traversal sequences in raw input
        normalized_str = target_path.replace("\\", "/")
        if "/../" in normalized_str or normalized_str.endswith("/..") or normalized_str.startswith("../"):
            raise SecurityViolationError(f"Directory traversal detected in path: '{target_path}'")

        # Check for sensitive files
        basename = os.path.basename(target_path)
        for pattern in self.SENSITIVE_TARGETS:
            if re.search(pattern, basename, re.IGNORECASE):
                raise SecurityViolationError(f"Access to sensitive target '{basename}' is strictly blocked.")

        try:
            p = Path(target_path)
            # Resolve to canonical absolute path (resolves symlinks and junctions)
            if p.is_absolute():
                resolved = p.resolve()
            else:
                # Relative to NOVA root
                resolved = (Path(settings.ROOT_DIR) / p).resolve()
        except Exception as e:
            raise SecurityViolationError(f"Could not resolve path '{target_path}': {str(e)}")

        # Check if resolved path is inside at least one allowed root
        is_inside_allowed = False
        for root in self.allowed_roots:
            try:
                # If resolved is root or starts with root
                if resolved == root or root in resolved.parents:
                    is_inside_allowed = True
                    break
            except Exception:
                continue

        if not is_inside_allowed:
            raise SecurityViolationError(
                f"Path '{resolved}' is outside permitted workspace roots. Access denied."
            )

        # Check if parent directory exists if allow_create is True
        if allow_create:
            if not resolved.parent.exists():
                raise SecurityViolationError(f"Parent directory '{resolved.parent}' does not exist.")
        else:
            if not resolved.exists():
                raise FileNotFoundError(f"Target path '{resolved}' does not exist.")

        return resolved

    def is_operation_blocked(self, command_or_action: str) -> Tuple[bool, Optional[str]]:
        """Determine if an arbitrary directive or payload contains blocked commands."""
        lower = command_or_action.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, lower):
                return True, f"Blocked directive: matches forbidden pattern '{pattern}'"
        return False, None

    def get_effective_permission(self, tool_id: str, arguments: Optional[Dict[str, Any]] = None) -> PermissionLevel:
        """Determines effective permission level for a tool and its arguments."""
        from app.tools.tool_registry import tool_registry
        blocked, _ = self.is_operation_blocked(tool_id)
        if blocked:
            return PermissionLevel.BLOCKED
        tool_entry = tool_registry.get_tool(tool_id)
        if not tool_entry:
            return PermissionLevel.BLOCKED
        return tool_entry.definition.permission_level

    def redact_sensitive_data(self, data: Any) -> Any:
        """Recursively redact passwords, keys, and tokens in arguments and logs."""
        if isinstance(data, dict):
            redacted = {}
            for k, v in data.items():
                k_lower = str(k).lower()
                if any(sec in k_lower for sec in ["key", "token", "password", "secret", "auth", "credential"]):
                    redacted[k] = "[REDACTED]"
                else:
                    redacted[k] = self.redact_sensitive_data(v)
            return redacted
        elif isinstance(data, list):
            return [self.redact_sensitive_data(item) for item in data]
        elif isinstance(data, str):
            # Mask potential tokens or keys
            if re.search(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{15,}", data):
                return re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{15,}", r"\1[REDACTED]", data)
            return data
        return data

permission_manager = PermissionManager()
