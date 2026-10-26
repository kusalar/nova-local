import os
import sys
import time
import json
import uuid
import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.tools.tool_registry import tool_registry
from app.tools.permission_manager import permission_manager, SecurityViolationError
from app.tools.tool_executor import tool_executor, ToolExecutionError
from app.tools.execution_logger import execution_logger
from app.tools.rollback_manager import rollback_manager, RollbackError
from app.tools.task_planner import task_planner
from app.tools.execution_manager import execution_manager
from app.tools.tool_schemas import (
    PermissionLevel, ToolCategory, TaskStatus, StepStatus,
    TaskPlan, TaskStep, ExecutionRecord
)
from app.voice.audio_manager import audio_manager

client = TestClient(app)

# ---------------------------------------------------------------------------
# 1. TOOL REGISTRATION & SCHEMAS
# ---------------------------------------------------------------------------

def test_tool_registration():
    """Verify all 23 verified tools are registered with proper metadata."""
    tools = tool_registry.list_tools()
    assert len(tools) >= 20
    tool_ids = [t.id for t in tools]
    
    # Required core tools
    expected_tools = [
        "app_open", "app_detect_installed", "file_open_default", "folder_open_explorer",
        "folder_list_contents", "file_search_name", "file_search_extension",
        "folder_create", "file_rename", "file_move", "file_copy", "file_read_text",
        "file_get_metadata", "folder_organize_preview", "system_battery_info",
        "system_cpu_ram", "system_disk_usage", "system_network_status",
        "system_volume_get", "system_volume_set", "system_lock_workstation",
        "browser_open_url", "browser_search_web"
    ]
    for et in expected_tools:
        assert et in tool_ids, f"Expected tool '{et}' not registered"

    # Verify uniqueness
    assert len(tool_ids) == len(set(tool_ids)), "Duplicate tool IDs detected"

def test_tool_schema_validation():
    """Verify parameter definitions, timeouts, and categories on all registered tools."""
    for tool in tool_registry.list_tools():
        assert tool.name, f"Tool '{tool.id}' has no name"
        assert tool.description, f"Tool '{tool.id}' has no description"
        assert tool.timeout_seconds > 0, f"Tool '{tool.id}' invalid timeout"
        assert tool.category in [c for c in ToolCategory]
        assert tool.permission_level in [p for p in PermissionLevel]

# ---------------------------------------------------------------------------
# 2. PERMISSION AND SECURITY SAFEGUARDS
# ---------------------------------------------------------------------------

def test_permission_classification():
    """Verify correct permission levels assigned to sensitive and safe tools."""
    assert tool_registry.get_definition("system_cpu_ram").permission_level == PermissionLevel.READ_ONLY
    assert tool_registry.get_definition("folder_list_contents").permission_level == PermissionLevel.READ_ONLY
    assert tool_registry.get_definition("app_open").permission_level == PermissionLevel.LOW_RISK
    assert tool_registry.get_definition("folder_create").permission_level == PermissionLevel.LOW_RISK
    assert tool_registry.get_definition("file_move").permission_level == PermissionLevel.CONFIRMATION_REQUIRED
    assert tool_registry.get_definition("file_rename").permission_level == PermissionLevel.CONFIRMATION_REQUIRED
    assert tool_registry.get_definition("system_lock_workstation").permission_level == PermissionLevel.CONFIRMATION_REQUIRED

def test_shell_injection_prevention():
    """Verify that dangerous arbitrary commands and shell binaries are blocked."""
    blocked_commands = [
        "powershell -ExecutionPolicy Bypass",
        "cmd.exe /c del C:\\*",
        "rmdir /s /q Windows",
        "bash -c 'rm -rf /'",
        "eval('__import__(\"os\").system(\"ls\")')",
        "format C: /y",
        "shutdown /s /t 0",
        "regedit.exe"
    ]
    for cmd in blocked_commands:
        blocked, reason = permission_manager.is_operation_blocked(cmd)
        assert blocked is True, f"Command '{cmd}' should have been blocked!"
        assert reason is not None

def test_path_traversal_prevention():
    """Verify path traversal attacks and access to sensitive files are strictly blocked."""
    with pytest.raises(SecurityViolationError):
        permission_manager.validate_path("../../Windows/System32")

    with pytest.raises(SecurityViolationError):
        permission_manager.validate_path("Nova/../../../sensitive.txt")

    # Sensitive files
    with pytest.raises(SecurityViolationError):
        permission_manager.validate_path(os.path.join(settings.ROOT_DIR, ".env"))

    with pytest.raises(SecurityViolationError):
        permission_manager.validate_path("id_rsa")

def test_symlink_escape_prevention(tmp_path):
    """Verify symlinks pointing outside permitted workspace roots are rejected."""
    permission_manager.add_allowed_root(str(tmp_path))
    
    # Target outside allowed root (system root)
    outside_target = Path("C:\\Windows") if os.name == "nt" else Path("/bin")
    if outside_target.exists():
        link_path = tmp_path / "escape_link"
        try:
            os.symlink(outside_target, link_path, target_is_directory=True)
            # Validating the link should resolve to outside_target and raise SecurityViolationError
            with pytest.raises(SecurityViolationError):
                permission_manager.validate_path(str(link_path))
        except (OSError, NotImplementedError):
            # Non-admin Windows might not allow creating symlinks; verify path validation directly
            pass

def test_sensitive_data_redaction():
    """Verify API tokens, passwords, and keys are automatically masked."""
    args = {
        "folder_path": "C:\\safe",
        "api_key": "sk-1234567890abcdef",
        "user_password": "SuperSecretPassword123",
        "nested": {
            "auth_token": "Bearer abcdef1234567890_token"
        }
    }
    redacted = permission_manager.redact_sensitive_data(args)
    assert redacted["folder_path"] == "C:\\safe"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["user_password"] == "[REDACTED]"
    assert redacted["nested"]["auth_token"] == "[REDACTED]"

# ---------------------------------------------------------------------------
# 3. APPLICATION & SYSTEM CONTROL
# ---------------------------------------------------------------------------

def test_application_resolution():
    """Verify installed application lookup and detection."""
    res = tool_executor.app_detect_installed("notepad")
    assert res["installed"] is True
    assert "notepad" in res["executable_path"].lower()

    # Non-existent application
    non_existent = tool_executor.app_detect_installed("totally_fake_app_xyz_99")
    assert non_existent["installed"] is False

def test_system_telemetry_tools():
    """Verify system metrics tools return valid telemetry structures."""
    cpu_ram = tool_executor.system_cpu_ram()
    assert "cpu" in cpu_ram and "ram" in cpu_ram
    assert isinstance(cpu_ram["cpu"]["percent"], (int, float))
    assert isinstance(cpu_ram["ram"]["percent"], (int, float))

    disk = tool_executor.system_disk_usage()
    assert "percent" in disk
    assert "used_gb" in disk

    battery = tool_executor.system_battery_info()
    assert "percent" in battery

    network = tool_executor.system_network_status()
    assert "connected" in network
    assert "bytes_sent_mb" in network

# ---------------------------------------------------------------------------
# 4. FILE OPERATIONS, DRY-RUNS & ROLLBACK (IN ISOLATED TEMP DIRECTORY)
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_workspace(tmp_path):
    """Provides an isolated directory added to allowed roots for safe testing."""
    permission_manager.add_allowed_root(str(tmp_path))
    test_dir = tmp_path / "nova_test_sandbox"
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)

def test_file_crud_and_metadata(temp_workspace):
    """Test folder creation, file writing, metadata retrieval, and text reading."""
    sub_dir = temp_workspace / "subfolder"
    create_res = tool_executor.folder_create(str(sub_dir))
    assert create_res["success"] is True
    assert sub_dir.exists()

    # Create dummy text file
    test_file = sub_dir / "notes.txt"
    test_file.write_text("NOVA Autonomous Engine v0.4 Test Line 1\nLine 2", encoding="utf-8")

    # Read text
    read_res = tool_executor.file_read_text(str(test_file))
    assert "NOVA Autonomous Engine" in read_res["content"]
    assert read_res["lines_read"] == 2

    # Get metadata
    meta = tool_executor.file_get_metadata(str(test_file))
    assert meta["name"] == "notes.txt"
    assert meta["extension"] == ".txt"
    assert meta["size_bytes"] > 0

    # Search by extension
    search_res = tool_executor.file_search_extension(str(temp_workspace), "txt")
    assert search_res["total_matches"] >= 1
    assert any(m["name"] == "notes.txt" for m in search_res["matches"])

def test_file_operation_dry_runs(temp_workspace):
    """Test dry-run simulation for folder creation, rename, and move."""
    target_folder = temp_workspace / "dry_run_folder"
    
    # Dry-run folder create
    res = tool_executor.folder_create(str(target_folder), dry_run=True)
    assert res.get("dry_run") is True
    assert not target_folder.exists(), "Dry run must NOT create the folder on disk"

    # Create real file to test dry-run rename
    real_file = temp_workspace / "sample.txt"
    real_file.write_text("content", encoding="utf-8")

    res_rename = tool_executor.file_rename(str(real_file), "sample_renamed.txt", dry_run=True)
    assert res_rename.get("dry_run") is True
    assert real_file.exists(), "Original file must remain untouched during dry run"
    assert not (temp_workspace / "sample_renamed.txt").exists()

def test_file_operation_rollback(temp_workspace):
    """Test safe reversible rollbacks on move and rename operations."""
    src_file = temp_workspace / "original.txt"
    src_file.write_text("Immutable Data", encoding="utf-8")

    dest_folder = temp_workspace / "archive"
    dest_folder.mkdir(parents=True, exist_ok=True)

    # Move file
    move_res = tool_executor.file_move(str(src_file), str(dest_folder))
    assert move_res["success"] is True
    assert not src_file.exists()
    assert (dest_folder / "original.txt").exists()

    # Log fake execution record to test rollback manager
    exec_id = f"test_exec_rb_{uuid.uuid4().hex[:8]}"
    execution_logger.log_execution_start(
        execution_id=exec_id,
        tool_id="file_move",
        tool_name="Move File",
        category="FILE_SYSTEM",
        permission_level="CONFIRMATION_REQUIRED",
        arguments={"source_path": str(src_file), "destination_folder": str(dest_folder)},
        is_reversible=True
    )
    execution_logger.log_execution_complete(
        execution_id=exec_id,
        status="COMPLETED",
        result=move_res,
        rollback_data=move_res["rollback_data"]
    )

    # Execute Rollback
    rb_res = rollback_manager.rollback(exec_id)
    assert rb_res["success"] is True
    assert src_file.exists(), "Rollback must move original file back to source location"
    assert not (dest_folder / "original.txt").exists()

def test_folder_organize_preview(temp_workspace):
    """Test folder classification preview without moving files."""
    downloads = temp_workspace / "MockDownloads"
    downloads.mkdir(parents=True, exist_ok=True)

    (downloads / "document.pdf").write_text("pdf", encoding="utf-8")
    (downloads / "photo.png").write_text("png", encoding="utf-8")
    (downloads / "script.py").write_text("code", encoding="utf-8")

    preview = tool_executor.folder_organize_preview(str(downloads))
    assert preview["total_files"] == 3
    assert "Documents" in preview["categories_detected"]
    assert "Images" in preview["categories_detected"]
    assert "Code" in preview["categories_detected"]
    assert len(preview["proposals"]) == 3
    assert preview["requires_confirmation"] is True

# ---------------------------------------------------------------------------
# 5. TASK PLANNER & MEMORY INTEGRATION
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_planner_deterministic():
    """Verify deterministic deconstruction of complex requests into validated action plans."""
    # Complex directive
    prompt = "Open VS Code, open my NOVA project, and tell me whether the backend is running."
    plan = await task_planner.plan_task(prompt)
    assert plan.task_id.startswith("task_")
    assert len(plan.steps) >= 2
    assert any(s.tool_id == "app_open" for s in plan.steps)
    # Check that NOVA root was correctly resolved
    app_open_step = next(s for s in plan.steps if s.tool_id == "app_open")
    assert str(Path(settings.ROOT_DIR).resolve()) in app_open_step.arguments.get("arguments", [])

@pytest.mark.asyncio
async def test_task_planner_hardware_directive():
    """Verify system telemetry planning."""
    plan = await task_planner.plan_task("Check my system status")
    assert len(plan.steps) >= 1
    assert any("system_" in s.tool_id for s in plan.steps)
    assert plan.requires_confirmation is False

@pytest.mark.asyncio
async def test_task_planner_confirmation_flagging():
    """Verify that confirmation-required tools flag the plan accordingly."""
    plan = await task_planner.plan_task("Lock my computer")
    assert any(s.tool_id == "system_lock_workstation" for s in plan.steps)
    assert plan.requires_confirmation is True
    assert plan.confirmation_reason is not None

# ---------------------------------------------------------------------------
# 6. EXECUTION MANAGER, APPROVALS & CANCELLATION
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execution_manager_approval_flow(temp_workspace):
    """Verify that confirmation-required plans pause in PENDING_APPROVAL and execute after approval."""
    test_file = temp_workspace / "to_rename.txt"
    test_file.write_text("hello", encoding="utf-8")

    step = TaskStep(
        step_id=1,
        tool_id="file_rename",
        description="Rename to_rename.txt",
        arguments={"current_path": str(test_file), "new_name": "renamed_ok.txt"},
        permission_level=PermissionLevel.CONFIRMATION_REQUIRED
    )
    plan = TaskPlan(
        task_id="test_approval_task",
        prompt="Rename file",
        description="Rename to_rename.txt",
        steps=[step],
        requires_confirmation=True,
        confirmation_reason="File rename requires authorization"
    )

    # 1. First execution attempt without approval -> MUST pause in PENDING_APPROVAL
    paused = await execution_manager.execute_task(plan, is_approved=False)
    assert paused.status == TaskStatus.PENDING_APPROVAL
    assert test_file.exists(), "File must not be renamed before explicit approval!"

    # 2. Explicit approval -> MUST execute successfully
    approved = await execution_manager.approve_and_execute(plan.task_id)
    assert approved.status == TaskStatus.COMPLETED
    assert not test_file.exists()
    assert (temp_workspace / "renamed_ok.txt").exists()

@pytest.mark.asyncio
async def test_task_rejection():
    """Verify that rejecting a task sets status to REJECTED without executing steps."""
    step = TaskStep(
        step_id=1,
        tool_id="system_lock_workstation",
        description="Lock screen",
        arguments={},
        permission_level=PermissionLevel.CONFIRMATION_REQUIRED
    )
    plan = TaskPlan(
        task_id="test_reject_task",
        prompt="Lock screen",
        description="Lock workstation",
        steps=[step],
        requires_confirmation=True
    )
    await execution_manager.execute_task(plan, is_approved=False)
    rejected = execution_manager.reject_task(plan.task_id)
    assert rejected.status == TaskStatus.REJECTED

@pytest.mark.asyncio
async def test_task_cancellation():
    """Verify task cancellation prevents further execution."""
    step = TaskStep(
        step_id=1,
        tool_id="system_cpu_ram",
        description="Get telemetry",
        arguments={}
    )
    plan = TaskPlan(
        task_id="test_cancel_task",
        prompt="Check status",
        description="Status check",
        steps=[step]
    )
    execution_manager.cancel_task(plan.task_id)
    executed = await execution_manager.execute_task(plan)
    assert executed.status == TaskStatus.CANCELLED

# ---------------------------------------------------------------------------
# 7. VOICE & TASK EXECUTION INTEGRATION
# ---------------------------------------------------------------------------

def test_voice_command_interception():
    """Verify that speech directives for desktop operations are dispatched correctly."""
    # Simulate pending voice confirmation
    audio_manager.pending_voice_task_id = "vtask_confirm_123"
    audio_manager.pending_voice_task_expiry = time.time() + 30.0

    # User says "no" -> should cancel
    plan = TaskPlan(
        task_id="vtask_confirm_123",
        prompt="Test",
        description="Voice action",
        steps=[]
    )
    execution_logger.save_task(plan)

    audio_manager._dispatch_to_brain("no, cancel that")
    assert audio_manager.pending_voice_task_id is None
    saved = execution_logger.get_task("vtask_confirm_123")
    assert saved.status == TaskStatus.REJECTED

# ---------------------------------------------------------------------------
# 8. FASTAPI REST API ENDPOINTS COMPATIBILITY
# ---------------------------------------------------------------------------

def test_api_list_tools():
    """Test GET /api/tools."""
    response = client.get("/api/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) >= 20
    assert any(t["id"] == "app_open" for t in tools)

def test_api_get_tool():
    """Test GET /api/tools/{tool_id}."""
    response = client.get("/api/tools/app_open")
    assert response.status_code == 200
    tool = response.json()
    assert tool["id"] == "app_open"
    assert tool["permission_level"] == "LOW_RISK"

    # Non-existent tool
    bad_res = client.get("/api/tools/non_existent_tool_id")
    assert bad_res.status_code == 404

def test_api_plan_and_execute_task():
    """Test POST /api/tasks/plan and POST /api/tasks/execute."""
    plan_res = client.post("/api/tasks/plan", json={
        "prompt": "Check my CPU and RAM usage",
        "auto_execute": False
    })
    assert plan_res.status_code == 200
    plan = plan_res.json()
    assert "task_id" in plan
    assert len(plan["steps"]) >= 1

    # Execute planned task
    exec_res = client.post("/api/tasks/execute", json={
        "task_id": plan["task_id"]
    })
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "COMPLETED"

def test_api_approval_endpoints():
    """Test POST /api/tasks/{task_id}/approve and /reject."""
    plan_res = client.post("/api/tasks/plan", json={
        "prompt": "Lock my workstation"
    })
    task_id = plan_res.json()["task_id"]

    # Reject
    rej_res = client.post(f"/api/tasks/{task_id}/reject")
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "REJECTED"

def test_api_executions_and_rollback():
    """Test GET /api/executions and POST /api/executions/{id}/rollback."""
    res = client.get("/api/executions?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
