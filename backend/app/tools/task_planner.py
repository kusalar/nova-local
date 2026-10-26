import re
import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config import settings
from app.tools.tool_schemas import (
    TaskPlan, TaskStep, TaskStatus, StepStatus, PermissionLevel
)
from app.tools.tool_registry import tool_registry
from app.tools.permission_manager import permission_manager
from app.memory.project_memory import project_memory
from app.ai.model_manager import model_manager

logger = logging.getLogger("nova.tools.planner")

class TaskPlanner:
    """
    Translates natural-language requests into structured, validated action plans.
    Integrates project memory for workspace resolution and enforces safety limits.
    """

    MAX_STEPS = 8

    async def plan_task(self, prompt: str, project_id: Optional[str] = None) -> TaskPlan:
        """
        Generate a validated TaskPlan from a user prompt.
        Uses deterministic intent matching for instant sub-millisecond planning,
        falling back to structured LLM inference when needed.
        """
        prompt_clean = prompt.strip()
        task_id = f"task_{uuid.uuid4().hex[:10]}"

        # 1. Check for blocked content first
        blocked, reason = permission_manager.is_operation_blocked(prompt_clean)
        if blocked:
            return TaskPlan(
                task_id=task_id,
                prompt=prompt_clean,
                description=f"Blocked: {reason}",
                steps=[],
                status=TaskStatus.REJECTED,
                requires_confirmation=False,
                confirmation_reason=reason
            )

        # 2. Try deterministic plan synthesis
        plan = self._deterministic_plan(task_id, prompt_clean, project_id)
        if not plan:
            # 3. Model-assisted planning
            plan = await self._model_assisted_plan(task_id, prompt_clean, project_id)

        # 4. Enforce strict safety constraints
        plan = self._validate_and_sanitize_plan(plan)
        return plan

    def _resolve_project_workspace(self, query: str, explicit_project_id: Optional[str] = None) -> Optional[str]:
        """Resolve a project mention to an allowed directory path."""
        lower = query.lower()
        if "nova" in lower or (explicit_project_id and explicit_project_id.lower() == "nova"):
            return str(Path(settings.ROOT_DIR).resolve())

        # Check v0.3 project memory
        detected = explicit_project_id or project_memory.detect_project_in_text(query)
        if detected:
            proj = project_memory.memory_store.get_project(detected)
            if proj:
                # Look in standard projects or documents folders for matching project name
                user_home = Path.home()
                for base in [Path(settings.ROOT_DIR).parent, user_home / "Projects", user_home / "Documents"]:
                    cand = base / proj.name
                    if cand.exists() and cand.is_dir():
                        try:
                            val = permission_manager.validate_path(str(cand))
                            return str(val)
                        except Exception:
                            pass
        return None

    def _resolve_standard_folder(self, folder_name: str) -> Optional[str]:
        """Resolve common user folders (Downloads, Documents, Desktop, etc.)."""
        lower = folder_name.lower().strip()
        user_home = Path.home()
        mapping = {
            "downloads": user_home / "Downloads",
            "download": user_home / "Downloads",
            "documents": user_home / "Documents",
            "document": user_home / "Documents",
            "desktop": user_home / "Desktop",
            "pictures": user_home / "Pictures",
            "music": user_home / "Music",
            "videos": user_home / "Videos",
            "nova": Path(settings.ROOT_DIR),
            "workspace": Path(settings.ROOT_DIR)
        }
        for k, p in mapping.items():
            if k in lower:
                if p.exists():
                    try:
                        return str(permission_manager.validate_path(str(p)))
                    except Exception:
                        pass
        return None

    def _deterministic_plan(self, task_id: str, prompt: str, project_id: Optional[str] = None) -> Optional[TaskPlan]:
        """Fast pattern-based intent recognizer."""
        lower = prompt.lower()
        steps: List[TaskStep] = []

        # A. Complex Multi-Intent: "Open VS Code, open my NOVA project, and tell me whether the backend is running."
        if ("vs code" in lower or "vscode" in lower) and "nova" in lower and ("backend" in lower or "running" in lower or "status" in lower):
            workspace = str(Path(settings.ROOT_DIR).resolve())
            steps.append(TaskStep(
                step_id=1,
                tool_id="app_detect_installed",
                description="Verify Visual Studio Code installation",
                arguments={"app_name": "vscode"}
            ))
            steps.append(TaskStep(
                step_id=2,
                tool_id="app_open",
                description="Launch Visual Studio Code with NOVA workspace",
                arguments={"app_name": "vscode", "arguments": [workspace]}
            ))
            steps.append(TaskStep(
                step_id=3,
                tool_id="system_network_status",
                description="Check system service and network status",
                arguments={}
            ))
            return TaskPlan(
                task_id=task_id,
                prompt=prompt,
                description="Launch VS Code with NOVA workspace and verify system status",
                steps=steps
            )

        # B. Open App + Workspace: "open my nova project in vs code" / "open vs code with my nova project"
        if ("open" in lower or "launch" in lower) and ("vs code" in lower or "vscode" in lower or "code" in lower) and "nova" in lower:
            workspace = str(Path(settings.ROOT_DIR).resolve())
            steps.append(TaskStep(
                step_id=1,
                tool_id="app_open",
                description="Launch VS Code with NOVA workspace",
                arguments={"app_name": "vscode", "arguments": [workspace]}
            ))
            return TaskPlan(
                task_id=task_id,
                prompt=prompt,
                description=f"Open Visual Studio Code in {workspace}",
                steps=steps
            )

        # C. Single Application Launch: "Open Notepad", "Open Calculator", "Open Chrome", "Open Terminal"
        open_app_match = re.search(r"\b(open|launch|start)\s+(the\s+)?(visual studio code|vscode|vs code|notepad|calculator|calc|windows terminal|terminal|chrome|edge|explorer|file explorer)\b", lower)
        if open_app_match:
            app_raw = open_app_match.group(3)
            steps.append(TaskStep(
                step_id=1,
                tool_id="app_open",
                description=f"Launch application '{app_raw}'",
                arguments={"app_name": app_raw, "arguments": []}
            ))
            return TaskPlan(
                task_id=task_id,
                prompt=prompt,
                description=f"Launch {app_raw}",
                steps=steps
            )

        # D. System Monitoring: "Check my system status", "Check CPU and RAM", "What is my battery level"
        if any(kw in lower for kw in ["system status", "battery", "cpu", "ram usage", "disk usage", "hardware status", "hardware"]):
            if "battery" in lower:
                steps.append(TaskStep(
                    step_id=1,
                    tool_id="system_battery_info",
                    description="Query battery telemetry",
                    arguments={}
                ))
            elif "disk" in lower:
                steps.append(TaskStep(
                    step_id=1,
                    tool_id="system_disk_usage",
                    description="Query storage drive telemetry",
                    arguments={}
                ))
            else:
                steps.append(TaskStep(
                    step_id=1,
                    tool_id="system_cpu_ram",
                    description="Query CPU and RAM telemetry",
                    arguments={}
                ))
                steps.append(TaskStep(
                    step_id=2,
                    tool_id="system_battery_info",
                    description="Query battery telemetry",
                    arguments={}
                ))
            return TaskPlan(
                task_id=task_id,
                prompt=prompt,
                description="Gather hardware and system telemetry",
                steps=steps
            )

        # E. Folder Organization: "Organize my Downloads folder" / "organize downloads"
        if "organize" in lower and ("download" in lower or "document" in lower or "folder" in lower):
            target_folder = self._resolve_standard_folder(lower) or str(Path.home() / "Downloads")
            steps.append(TaskStep(
                step_id=1,
                tool_id="folder_organize_preview",
                description=f"Scan and classify files in {target_folder}",
                arguments={"folder_path": target_folder}
            ))
            return TaskPlan(
                task_id=task_id,
                prompt=prompt,
                description=f"Classify and organize files in '{target_folder}'",
                steps=steps,
                requires_confirmation=True,
                confirmation_reason=f"File organization requires approval before moving files in {target_folder}"
            )

        # F. Create Folder: "Create a folder called Research in my Documents"
        create_folder_match = re.search(r"create\s+(a\s+)?folder\s+(called\s+|named\s+)?['\"]?([a-zA-Z0-9_\-\s]+)['\"]?\s+in\s+(my\s+)?([a-zA-Z0-9_\-]+)", lower)
        if create_folder_match:
            folder_name = create_folder_match.group(3).strip()
            parent_name = create_folder_match.group(5).strip()
            parent_resolved = self._resolve_standard_folder(parent_name)
            if parent_resolved:
                new_folder_path = str(Path(parent_resolved) / folder_name)
                steps.append(TaskStep(
                    step_id=1,
                    tool_id="folder_create",
                    description=f"Create folder '{folder_name}' in {parent_name}",
                    arguments={"folder_path": new_folder_path}
                ))
                return TaskPlan(
                    task_id=task_id,
                    prompt=prompt,
                    description=f"Create folder '{folder_name}' in {parent_resolved}",
                    steps=steps
                )

        # G. Search Files: "Find my python projects", "Search for *.tsx files in Nova"
        if any(kw in lower for kw in ["find", "search"]) and ("file" in lower or "project" in lower or "extension" in lower or "python" in lower):
            target_dir = self._resolve_standard_folder(lower) or str(Path(settings.ROOT_DIR).resolve())
            ext = ".py" if "python" in lower else (".tsx" if "tsx" in lower else "*")
            if ext != "*":
                steps.append(TaskStep(
                    step_id=1,
                    tool_id="file_search_extension",
                    description=f"Search for '{ext}' files in {target_dir}",
                    arguments={"folder_path": target_dir, "extension": ext}
                ))
            else:
                steps.append(TaskStep(
                    step_id=1,
                    tool_id="file_search_name",
                    description=f"Search files in {target_dir}",
                    arguments={"folder_path": target_dir, "pattern": "*"}
                ))
            return TaskPlan(
                task_id=task_id,
                prompt=prompt,
                description=f"Search files in {target_dir}",
                steps=steps
            )

        # H. Browser Search / Navigation: "Search the web for...", "Open website..."
        if "search the web for" in lower or "search online for" in lower or "google" in lower:
            query = re.sub(r"^(search the web for|search online for|search for|google)\s+", "", lower).strip()
            steps.append(TaskStep(
                step_id=1,
                tool_id="browser_search_web",
                description=f"Search web for '{query}'",
                arguments={"query": query}
            ))
            return TaskPlan(
                task_id=task_id,
                prompt=prompt,
                description=f"Search web for '{query}'",
                steps=steps
            )

        if "open website" in lower or "go to" in lower or ("open" in lower and (".com" in lower or ".org" in lower or "http" in lower)):
            url_match = re.search(r"(https?://\S+|www\.\S+|[a-zA-Z0-9_\-]+\.(com|org|io|dev|net|edu))\b", prompt)
            if url_match:
                raw_url = url_match.group(0)
                steps.append(TaskStep(
                    step_id=1,
                    tool_id="browser_open_url",
                    description=f"Open website {raw_url}",
                    arguments={"url": raw_url}
                ))
                return TaskPlan(
                    task_id=task_id,
                    prompt=prompt,
                    description=f"Navigate to {raw_url}",
                    steps=steps
                )

        # I. Workstation Lock
        if "lock" in lower and ("workstation" in lower or "computer" in lower or "pc" in lower or "screen" in lower):
            steps.append(TaskStep(
                step_id=1,
                tool_id="system_lock_workstation",
                description="Lock Windows workstation",
                arguments={}
            ))
            return TaskPlan(
                task_id=task_id,
                prompt=prompt,
                description="Lock Windows workstation",
                steps=steps,
                requires_confirmation=True,
                confirmation_reason="Locking workstation will lock the screen and require Windows credentials to unlock."
            )

        return None

    async def _model_assisted_plan(self, task_id: str, prompt: str, project_id: Optional[str] = None) -> TaskPlan:
        """
        Use model inference to generate a structured JSON action plan.
        """
        tools_summary = []
        for t in tool_registry.list_tools():
            tools_summary.append(f"- {t.id} ({t.permission_level.value}): {t.description}")
        tools_str = "\n".join(tools_summary)

        system_prompt = (
            "You are the NOVA Task Planner. Your job is to translate a user request into a sequence of tool calls.\n"
            f"Available Tools:\n{tools_str}\n\n"
            "Rules:\n"
            "1. Output ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "description": "Short summary of what this plan does",\n'
            '  "steps": [\n'
            '    {"tool_id": "<tool_id>", "description": "<step description>", "arguments": {<valid params>}}\n'
            "  ]\n"
            "}\n"
            "2. Maximum 8 steps.\n"
            "3. Use only registered tools and their documented parameters.\n"
            "4. NEVER invent tools or execute shell code."
        )

        try:
            res = await model_manager.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt
            )

            content = res.get("content", "").strip()
            # Extract JSON block
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                desc = parsed.get("description", f"Plan for: {prompt}")
                raw_steps = parsed.get("steps", [])

                steps: List[TaskStep] = []
                for idx, rs in enumerate(raw_steps[:self.MAX_STEPS]):
                    tid = rs.get("tool_id", "")
                    if tool_registry.get_definition(tid):
                        steps.append(TaskStep(
                            step_id=idx + 1,
                            tool_id=tid,
                            description=rs.get("description", f"Execute {tid}"),
                            arguments=rs.get("arguments", {})
                        ))

                if steps:
                    return TaskPlan(
                        task_id=task_id,
                        prompt=prompt,
                        description=desc,
                        steps=steps
                    )
        except Exception as e:
            logger.warning(f"Model-assisted planning failed: {e}")

        # Fallback empty plan
        return TaskPlan(
            task_id=task_id,
            prompt=prompt,
            description=f"Could not automatically decompose prompt: '{prompt}'. Please clarify your request.",
            steps=[]
        )

    def _validate_and_sanitize_plan(self, plan: TaskPlan) -> TaskPlan:
        """
        Validates tools, attaches permission levels, detects confirmations,
        and limits total steps.
        """
        if len(plan.steps) > self.MAX_STEPS:
            plan.steps = plan.steps[:self.MAX_STEPS]

        validated_steps: List[TaskStep] = []
        requires_conf = plan.requires_confirmation
        conf_reasons = []

        if plan.confirmation_reason:
            conf_reasons.append(plan.confirmation_reason)

        for idx, step in enumerate(plan.steps):
            step.step_id = idx + 1
            tool_def = tool_registry.get_definition(step.tool_id)
            if not tool_def:
                logger.warning(f"Unregistered tool in plan: '{step.tool_id}'")
                continue

            step.permission_level = tool_def.permission_level
            step.arguments = permission_manager.redact_sensitive_data(step.arguments)

            if tool_def.permission_level == PermissionLevel.CONFIRMATION_REQUIRED:
                requires_conf = True
                conf_reasons.append(f"Step {step.step_id} ({tool_def.name}) requires approval.")

            validated_steps.append(step)

        plan.steps = validated_steps
        plan.total_steps = len(validated_steps)
        plan.requires_confirmation = requires_conf
        if conf_reasons:
            plan.confirmation_reason = "; ".join(conf_reasons)

        if not validated_steps and plan.status != TaskStatus.REJECTED:
            plan.status = TaskStatus.FAILED
            plan.description += " (No valid tools could be resolved)"

        return plan

task_planner = TaskPlanner()
