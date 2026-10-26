from typing import Dict, List, Any, Callable, Optional
import inspect
import logging
from app.tools.tool_schemas import (
    ToolDefinition, ToolParameter, PermissionLevel, ToolCategory
)
from app.tools.tool_executor import tool_executor

logger = logging.getLogger("nova.tools.registry")

class RegisteredTool:
    def __init__(self, definition: ToolDefinition, handler: Callable[..., Any]):
        self.definition = definition
        self.handler = handler

class ToolRegistry:
    """
    Central repository of verified, safe tools for NOVA v0.4.
    Exposes validated metadata and callable execution points.
    """

    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}
        self._register_default_tools()

    def register(self, definition: ToolDefinition, handler: Callable[..., Any]):
        """Register a new tool with metadata and execution handler."""
        self._tools[definition.id] = RegisteredTool(definition, handler)
        logger.debug(f"Registered tool: {definition.id} ({definition.permission_level.value})")

    def get_tool(self, tool_id: str) -> Optional[RegisteredTool]:
        return self._tools.get(tool_id)

    def get_definition(self, tool_id: str) -> Optional[ToolDefinition]:
        tool = self._tools.get(tool_id)
        return tool.definition if tool else None

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        permission_level: Optional[PermissionLevel] = None
    ) -> List[ToolDefinition]:
        """List registered tool definitions, optionally filtered."""
        defs = []
        for t in self._tools.values():
            d = t.definition
            if category and d.category != category:
                continue
            if permission_level and d.permission_level != permission_level:
                continue
            defs.append(d)
        return sorted(defs, key=lambda x: (x.category.value, x.name))

    def _register_default_tools(self):
        # -------------------------------------------------------------
        # 1. APPLICATION CONTROL
        # -------------------------------------------------------------
        self.register(
            ToolDefinition(
                id="app_open",
                name="Open Application",
                description="Safely launch an installed Windows desktop application (e.g., VS Code, Notepad, Calculator, Chrome, Edge, Terminal).",
                category=ToolCategory.APPLICATION,
                permission_level=PermissionLevel.LOW_RISK,
                timeout_seconds=20,
                parameters=[
                    ToolParameter(name="app_name", type="string", description="Name or identifier of the application (e.g. 'vscode', 'notepad', 'calc')"),
                    ToolParameter(name="arguments", type="array", description="Optional argument list or file/workspace path to open in the app", required=False, default=[])
                ]
            ),
            tool_executor.app_open
        )

        self.register(
            ToolDefinition(
                id="app_detect_installed",
                name="Detect Application Installed",
                description="Check whether a specific application is installed and find its executable path.",
                category=ToolCategory.APPLICATION,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=10,
                parameters=[
                    ToolParameter(name="app_name", type="string", description="Name of the application to detect")
                ]
            ),
            tool_executor.app_detect_installed
        )

        self.register(
            ToolDefinition(
                id="file_open_default",
                name="Open File in Default App",
                description="Launch a specified file using its default Windows application association.",
                category=ToolCategory.APPLICATION,
                permission_level=PermissionLevel.LOW_RISK,
                timeout_seconds=15,
                parameters=[
                    ToolParameter(name="file_path", type="string", description="Absolute or workspace path to the file")
                ]
            ),
            tool_executor.file_open_default
        )

        self.register(
            ToolDefinition(
                id="folder_open_explorer",
                name="Open in File Explorer",
                description="Open a specified directory inside the Windows File Explorer.",
                category=ToolCategory.APPLICATION,
                permission_level=PermissionLevel.LOW_RISK,
                timeout_seconds=15,
                parameters=[
                    ToolParameter(name="folder_path", type="string", description="Path to the directory to open")
                ]
            ),
            tool_executor.folder_open_explorer
        )

        # -------------------------------------------------------------
        # 2. FILE INTELLIGENCE
        # -------------------------------------------------------------
        self.register(
            ToolDefinition(
                id="folder_list_contents",
                name="List Directory Contents",
                description="Retrieve list of files and subdirectories with sizes and modification times.",
                category=ToolCategory.FILE_SYSTEM,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=15,
                parameters=[
                    ToolParameter(name="folder_path", type="string", description="Path to the directory to list"),
                    ToolParameter(name="max_items", type="integer", description="Maximum number of items to return", required=False, default=100)
                ]
            ),
            tool_executor.folder_list_contents
        )

        self.register(
            ToolDefinition(
                id="file_search_name",
                name="Search Files by Name",
                description="Search for files by filename or wildcard pattern within an allowed directory.",
                category=ToolCategory.FILE_SYSTEM,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=20,
                parameters=[
                    ToolParameter(name="folder_path", type="string", description="Root folder to search within"),
                    ToolParameter(name="pattern", type="string", description="Filename or glob pattern to match (e.g. '*.py', 'report')"),
                    ToolParameter(name="recursive", type="boolean", description="Whether to search subdirectories", required=False, default=True)
                ]
            ),
            tool_executor.file_search_name
        )

        self.register(
            ToolDefinition(
                id="file_search_extension",
                name="Search Files by Extension",
                description="Search for all files matching a specific extension (e.g. '.py', '.tsx', '.pdf').",
                category=ToolCategory.FILE_SYSTEM,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=20,
                parameters=[
                    ToolParameter(name="folder_path", type="string", description="Directory to search"),
                    ToolParameter(name="extension", type="string", description="Extension with or without dot (e.g. 'py', '.tsx')")
                ]
            ),
            tool_executor.file_search_extension
        )

        self.register(
            ToolDefinition(
                id="folder_create",
                name="Create Folder",
                description="Create a new directory within permitted workspace roots.",
                category=ToolCategory.FILE_SYSTEM,
                permission_level=PermissionLevel.LOW_RISK,
                is_reversible=True,
                timeout_seconds=10,
                parameters=[
                    ToolParameter(name="folder_path", type="string", description="Full path of the new directory to create"),
                    ToolParameter(name="dry_run", type="boolean", description="Simulate without creating", required=False, default=False)
                ]
            ),
            tool_executor.folder_create
        )

        self.register(
            ToolDefinition(
                id="file_rename",
                name="Rename File",
                description="Rename an existing file or directory within permitted boundaries.",
                category=ToolCategory.FILE_SYSTEM,
                permission_level=PermissionLevel.CONFIRMATION_REQUIRED,
                is_reversible=True,
                timeout_seconds=15,
                parameters=[
                    ToolParameter(name="current_path", type="string", description="Path to the file to rename"),
                    ToolParameter(name="new_name", type="string", description="New filename (basename only, no directory slashes)"),
                    ToolParameter(name="dry_run", type="boolean", description="Simulate rename", required=False, default=False)
                ]
            ),
            tool_executor.file_rename
        )

        self.register(
            ToolDefinition(
                id="file_move",
                name="Move File",
                description="Move a file from source path to an allowed destination folder.",
                category=ToolCategory.FILE_SYSTEM,
                permission_level=PermissionLevel.CONFIRMATION_REQUIRED,
                is_reversible=True,
                timeout_seconds=20,
                parameters=[
                    ToolParameter(name="source_path", type="string", description="Path of file to relocate"),
                    ToolParameter(name="destination_folder", type="string", description="Target destination directory"),
                    ToolParameter(name="dry_run", type="boolean", description="Simulate move without relocating", required=False, default=False)
                ]
            ),
            tool_executor.file_move
        )

        self.register(
            ToolDefinition(
                id="file_copy",
                name="Copy File",
                description="Copy a file to a destination folder.",
                category=ToolCategory.FILE_SYSTEM,
                permission_level=PermissionLevel.CONFIRMATION_REQUIRED,
                is_reversible=True,
                timeout_seconds=25,
                parameters=[
                    ToolParameter(name="source_path", type="string", description="Source file path"),
                    ToolParameter(name="destination_folder", type="string", description="Destination directory"),
                    ToolParameter(name="dry_run", type="boolean", description="Simulate copy", required=False, default=False)
                ]
            ),
            tool_executor.file_copy
        )

        self.register(
            ToolDefinition(
                id="file_read_text",
                name="Read Text File",
                description="Read UTF-8 content from a text file (safe size cap of 500 KB).",
                category=ToolCategory.FILE_SYSTEM,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=15,
                parameters=[
                    ToolParameter(name="file_path", type="string", description="Path to the text file"),
                    ToolParameter(name="max_lines", type="integer", description="Maximum lines to read", required=False, default=200)
                ]
            ),
            tool_executor.file_read_text
        )

        self.register(
            ToolDefinition(
                id="file_get_metadata",
                name="Get File Metadata",
                description="Retrieve file size, creation timestamp, modified timestamp, and permissions.",
                category=ToolCategory.FILE_SYSTEM,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=10,
                parameters=[
                    ToolParameter(name="file_path", type="string", description="Path to target file or directory")
                ]
            ),
            tool_executor.file_get_metadata
        )

        self.register(
            ToolDefinition(
                id="folder_organize_preview",
                name="Organize Folder Preview",
                description="Scan and classify files in a folder into categorical subdirectories (Documents, Images, Code, etc.) with a dry-run preview.",
                category=ToolCategory.FILE_SYSTEM,
                permission_level=PermissionLevel.READ_ONLY,
                is_reversible=True,
                timeout_seconds=20,
                parameters=[
                    ToolParameter(name="folder_path", type="string", description="Folder to organize (e.g. Downloads)")
                ]
            ),
            tool_executor.folder_organize_preview
        )

        # -------------------------------------------------------------
        # 3. SYSTEM CONTROL
        # -------------------------------------------------------------
        self.register(
            ToolDefinition(
                id="system_battery_info",
                name="Get Battery Status",
                description="Read battery percentage and charging state via psutil.",
                category=ToolCategory.SYSTEM_CONTROL,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=10,
                parameters=[]
            ),
            tool_executor.system_battery_info
        )

        self.register(
            ToolDefinition(
                id="system_cpu_ram",
                name="Get CPU & RAM Usage",
                description="Read current hardware CPU percent and RAM utilization.",
                category=ToolCategory.SYSTEM_CONTROL,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=10,
                parameters=[]
            ),
            tool_executor.system_cpu_ram
        )

        self.register(
            ToolDefinition(
                id="system_disk_usage",
                name="Get Disk Usage",
                description="Read storage volume capacity and percentage used.",
                category=ToolCategory.SYSTEM_CONTROL,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=10,
                parameters=[]
            ),
            tool_executor.system_disk_usage
        )

        self.register(
            ToolDefinition(
                id="system_network_status",
                name="Check Network Status",
                description="Check internet connectivity, round-trip latency, and network traffic counters.",
                category=ToolCategory.SYSTEM_CONTROL,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=15,
                parameters=[]
            ),
            tool_executor.system_network_status
        )

        self.register(
            ToolDefinition(
                id="system_volume_get",
                name="Get System Volume",
                description="Read master audio volume percentage.",
                category=ToolCategory.SYSTEM_CONTROL,
                permission_level=PermissionLevel.READ_ONLY,
                timeout_seconds=10,
                parameters=[]
            ),
            tool_executor.system_volume_get
        )

        self.register(
            ToolDefinition(
                id="system_volume_set",
                name="Set System Volume",
                description="Change master system volume level (0 to 100).",
                category=ToolCategory.SYSTEM_CONTROL,
                permission_level=PermissionLevel.CONFIRMATION_REQUIRED,
                timeout_seconds=15,
                parameters=[
                    ToolParameter(name="level", type="integer", description="Audio volume percentage from 0 to 100")
                ]
            ),
            tool_executor.system_volume_set
        )

        self.register(
            ToolDefinition(
                id="system_lock_workstation",
                name="Lock Workstation",
                description="Lock the Windows workstation (requires explicit confirmation).",
                category=ToolCategory.SYSTEM_CONTROL,
                permission_level=PermissionLevel.CONFIRMATION_REQUIRED,
                timeout_seconds=10,
                parameters=[]
            ),
            tool_executor.system_lock_workstation
        )

        # -------------------------------------------------------------
        # 4. BROWSER OPERATIONS
        # -------------------------------------------------------------
        self.register(
            ToolDefinition(
                id="browser_open_url",
                name="Open Website URL",
                description="Open a validated HTTP/HTTPS URL in the user's default browser.",
                category=ToolCategory.BROWSER,
                permission_level=PermissionLevel.LOW_RISK,
                timeout_seconds=15,
                parameters=[
                    ToolParameter(name="url", type="string", description="Web address or URL to navigate to")
                ]
            ),
            tool_executor.browser_open_url
        )

        self.register(
            ToolDefinition(
                id="browser_search_web",
                name="Search the Web",
                description="Perform a web search in the default web browser.",
                category=ToolCategory.BROWSER,
                permission_level=PermissionLevel.LOW_RISK,
                timeout_seconds=15,
                parameters=[
                    ToolParameter(name="query", type="string", description="Search phrase or keywords")
                ]
            ),
            tool_executor.browser_search_web
        )

tool_registry = ToolRegistry()
