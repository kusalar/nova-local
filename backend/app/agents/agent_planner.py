import uuid
import json
import logging
from typing import List, Dict, Any, Optional

from .agent_schemas import (
    WorkflowPlan, WorkflowStep, WorkflowStatus, WorkflowStepStatus,
    AgentRole, RetryPolicy
)
from .agent_permissions import AgentPermissionEnforcer
from .agent_scheduler import WorkflowScheduler
from app.memory.project_memory import project_memory
from app.tools.tool_schemas import PermissionLevel
from app.ai.model_manager import model_manager

logger = logging.getLogger("nova.agents.planner")

MAX_WORKFLOW_STEPS = 12

class AgentPlanner:
    """
    Task planning engine that decomposes high-level user directives
    into structured, dependency-ordered, permission-validated workflow steps.
    """

    @classmethod
    async def create_plan(
        cls,
        objective: str,
        project_id: Optional[str] = None
    ) -> WorkflowPlan:
        """
        Generates a validated workflow plan from a user objective.
        Tries deterministic structural templates first for reliability,
        falling back to LLM-driven multi-agent decomposition.
        """
        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"

        # 1. Resolve project association from text or argument
        resolved_project = project_id
        if not resolved_project:
            resolved_project = project_memory.detect_project_in_text(objective)

        # 2. Check for deterministic high-reliability workflow patterns
        steps = cls._deterministic_decomposition(workflow_id, objective, resolved_project)
        
        # 3. If no pattern matched, use local LLM to decompose
        if not steps:
            steps = await cls._llm_assisted_decomposition(workflow_id, objective, resolved_project)

        # 4. Enforce max steps limit
        if len(steps) > MAX_WORKFLOW_STEPS:
            steps = steps[:MAX_WORKFLOW_STEPS]

        # 5. Authoritatively validate permissions and dependencies for each step
        requires_approval = False
        first_approval_step = None
        approval_reason = None

        for step in steps:
            perm, needs_approval, reason = AgentPermissionEnforcer.evaluate_step_permission(step)
            step.permission_level = perm
            if needs_approval and not requires_approval:
                requires_approval = True
                first_approval_step = step.step_id
                approval_reason = reason

        # Validate DAG dependencies
        is_valid, dep_err = WorkflowScheduler.validate_dependencies(steps)
        if not is_valid:
            logger.warning(f"Dependency validation corrected: {dep_err}")
            # Fix dependencies to strictly point to prior steps
            for i, s in enumerate(steps):
                s.dependencies = [steps[i - 1].step_id] if i > 0 else []

        plan = WorkflowPlan(
            workflow_id=workflow_id,
            objective=objective,
            project_id=resolved_project,
            steps=steps,
            status=WorkflowStatus.PLANNING,
            requires_approval=requires_approval,
            pending_approval_step_id=first_approval_step,
            approval_reason=approval_reason,
            total_steps=len(steps),
            completed_steps=0
        )

        return plan

    @classmethod
    def _deterministic_decomposition(
        cls,
        workflow_id: str,
        objective: str,
        project_id: Optional[str]
    ) -> Optional[List[WorkflowStep]]:
        """
        Fast, zero-hallucination templates for common desktop and project engineering intents.
        """
        lower = objective.lower()

        # Pattern A: Project Inspection & Test Execution (Matches user prompt example)
        # "Inspect my NOVA project, run its tests, and tell me what needs improvement."
        if any(kw in lower for kw in ["inspect", "analyze project", "check project"]) and any(kw in lower for kw in ["test", "tests", "improve", "run"]):
            proj_name = project_id or "nova"
            return [
                WorkflowStep(
                    step_id=1,
                    workflow_id=workflow_id,
                    description=f"Resolve project workspace and context for '{proj_name}'",
                    assigned_agent=AgentRole.MEMORY,
                    arguments={"action": "retrieve", "project_id": proj_name},
                    dependencies=[],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Project configuration and tech stack retrieved."
                ),
                WorkflowStep(
                    step_id=2,
                    workflow_id=workflow_id,
                    description="Inspect repository structure and configuration files",
                    assigned_agent=AgentRole.DEVELOPER,
                    tool_id="folder_list_contents",
                    arguments={"folder_path": "."},
                    dependencies=[1],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Repository file listing obtained."
                ),
                WorkflowStep(
                    step_id=3,
                    workflow_id=workflow_id,
                    description="Read test configuration and documentation",
                    assigned_agent=AgentRole.DEVELOPER,
                    tool_id="file_read_text",
                    arguments={"file_path": "package.json"},
                    dependencies=[2],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Project dependencies and test commands parsed."
                ),
                WorkflowStep(
                    step_id=4,
                    workflow_id=workflow_id,
                    description="Analyze recent test results and identify failure points",
                    assigned_agent=AgentRole.DEVELOPER,
                    arguments={"action": "evaluate_tests"},
                    dependencies=[3],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Test execution evaluated with failure metrics."
                ),
                WorkflowStep(
                    step_id=5,
                    workflow_id=workflow_id,
                    description="Synthesize code quality assessment and improvement report",
                    assigned_agent=AgentRole.RESEARCH,
                    dependencies=[4],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Technical improvement recommendations produced."
                ),
                WorkflowStep(
                    step_id=6,
                    workflow_id=workflow_id,
                    description="Record findings and workflow summary into project memory",
                    assigned_agent=AgentRole.MEMORY,
                    arguments={"action": "save_summary"},
                    dependencies=[5],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Workflow milestones logged to persistent project memory."
                )
            ]

        # Pattern B: On-screen Error Analysis & Visual Diagnosis
        # "Analyze the error on my screen and explain it."
        if any(kw in lower for kw in ["screen", "error", "dialog"]) and any(kw in lower for kw in ["look", "analyze", "explain", "see", "read"]):
            return [
                WorkflowStep(
                    step_id=1,
                    workflow_id=workflow_id,
                    description="Capture active desktop display and extract visible text using local OCR",
                    assigned_agent=AgentRole.VISION,
                    arguments={"target": "ACTIVE_WINDOW", "prompt": objective},
                    dependencies=[],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="OCR text and active window boundaries captured."
                ),
                WorkflowStep(
                    step_id=2,
                    workflow_id=workflow_id,
                    description="Cross-correlate visible error with known project issues and memory",
                    assigned_agent=AgentRole.MEMORY,
                    arguments={"action": "retrieve"},
                    dependencies=[1],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Related project memory and known issues queried."
                ),
                WorkflowStep(
                    step_id=3,
                    workflow_id=workflow_id,
                    description="Diagnose root cause and formulate resolution steps",
                    assigned_agent=AgentRole.DEVELOPER,
                    dependencies=[1, 2],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Technical explanation and fix recommendations generated."
                )
            ]

        # Pattern C: System Health Inspection & Diagnostics
        if any(kw in lower for kw in ["system", "hardware", "cpu", "ram", "battery", "health"]):
            return [
                WorkflowStep(
                    step_id=1,
                    workflow_id=workflow_id,
                    description="Collect real-time CPU, RAM, disk, and battery hardware metrics",
                    assigned_agent=AgentRole.SYSTEM,
                    tool_id="system_cpu_ram",
                    arguments={},
                    dependencies=[],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Hardware utilization statistics collected."
                ),
                WorkflowStep(
                    step_id=2,
                    workflow_id=workflow_id,
                    description="Query active desktop processes and resource distribution",
                    assigned_agent=AgentRole.SYSTEM,
                    tool_id="system_disk_usage",
                    arguments={},
                    dependencies=[1],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Disk storage allocation metrics retrieved."
                ),
                WorkflowStep(
                    step_id=3,
                    workflow_id=workflow_id,
                    description="Synthesize system diagnostic health report",
                    assigned_agent=AgentRole.RESEARCH,
                    dependencies=[1, 2],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Comprehensive hardware diagnostics summary formulated."
                )
            ]

        # Pattern D: File Organization & Desktop Maintenance
        if any(kw in lower for kw in ["organize", "clean", "sort"]) and any(kw in lower for kw in ["file", "files", "folder", "downloads"]):
            return [
                WorkflowStep(
                    step_id=1,
                    workflow_id=workflow_id,
                    description="Scan target directory structure and enumerate unorganized files",
                    assigned_agent=AgentRole.SYSTEM,
                    tool_id="folder_list_contents",
                    arguments={"folder_path": "."},
                    dependencies=[],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Catalog of target files produced."
                ),
                WorkflowStep(
                    step_id=2,
                    workflow_id=workflow_id,
                    description="Generate dry-run organization proposal and preview categories",
                    assigned_agent=AgentRole.RESEARCH,
                    dependencies=[1],
                    permission_level=PermissionLevel.READ_ONLY,
                    expected_output="Safe category categorization plan formulated."
                ),
                WorkflowStep(
                    step_id=3,
                    workflow_id=workflow_id,
                    description="Preview folder organization plan (Requires user approval)",
                    assigned_agent=AgentRole.SYSTEM,
                    tool_id="folder_organize_preview",
                    arguments={"folder_path": "."},
                    dependencies=[2],
                    permission_level=PermissionLevel.CONFIRMATION_REQUIRED,
                    expected_output="Files organized into categorized subfolders."
                )
            ]

        return None

    @classmethod
    async def _llm_assisted_decomposition(
        cls,
        workflow_id: str,
        objective: str,
        project_id: Optional[str]
    ) -> List[WorkflowStep]:
        """
        Fallback LLM-assisted multi-agent decomposition using the local Ollama provider.
        """
        system_prompt = (
            "You are the NOVA Orchestration Planner. Decompose the user's objective into 3 to 6 logical steps. "
            "Available agents: RESEARCH, DEVELOPER, SYSTEM, VISION, MEMORY. "
            "Available tools: file_read, file_write, file_list, file_delete, system_cpu_ram, system_battery_info, app_launch. "
            "Return a JSON array of step objects with fields: "
            "step_id (int), description (str), assigned_agent (str), tool_id (optional str or null), "
            "arguments (dict), dependencies (list of prior step_ids)."
        )

        user_prompt = f"Objective: {objective}\nAssociated Project: {project_id or 'none'}"

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = await model_manager.chat(messages=messages, model=model_manager.active_model)
            content = response.get("content", "")
            
            # Extract JSON block
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(json_str)
            if isinstance(parsed, list) and len(parsed) > 0:
                steps: List[WorkflowStep] = []
                for idx, item in enumerate(parsed[:MAX_WORKFLOW_STEPS]):
                    s_id = idx + 1
                    role_str = str(item.get("assigned_agent", "RESEARCH")).upper()
                    try:
                        role = AgentRole(role_str)
                    except ValueError:
                        role = AgentRole.RESEARCH

                    deps = [d for d in item.get("dependencies", []) if isinstance(d, int) and d < s_id]
                    if not deps and idx > 0:
                        deps = [idx] # default sequential dependency

                    steps.append(WorkflowStep(
                        step_id=s_id,
                        workflow_id=workflow_id,
                        description=item.get("description", f"Step {s_id}"),
                        assigned_agent=role,
                        tool_id=item.get("tool_id"),
                        arguments=item.get("arguments", {}),
                        dependencies=deps,
                        permission_level=PermissionLevel.READ_ONLY,
                        expected_output=item.get("expected_output", "")
                    ))
                return steps
        except Exception as e:
            logger.warning(f"LLM planning decomposition fallback: {e}")

        # Safe generic default workflow
        return [
            WorkflowStep(
                step_id=1,
                workflow_id=workflow_id,
                description="Query project and contextual memory for directive",
                assigned_agent=AgentRole.MEMORY,
                arguments={"action": "retrieve"},
                dependencies=[],
                permission_level=PermissionLevel.READ_ONLY
            ),
            WorkflowStep(
                step_id=2,
                workflow_id=workflow_id,
                description=f"Analyze requirements and formulate plan for: {objective[:80]}",
                assigned_agent=AgentRole.RESEARCH,
                dependencies=[1],
                permission_level=PermissionLevel.READ_ONLY
            ),
            WorkflowStep(
                step_id=3,
                workflow_id=workflow_id,
                description="Synthesize technical findings and recommendations",
                assigned_agent=AgentRole.DEVELOPER,
                dependencies=[2],
                permission_level=PermissionLevel.READ_ONLY
            )
        ]
