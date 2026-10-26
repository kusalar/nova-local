from typing import List, Dict, Set, Tuple, Optional
import logging

from .agent_schemas import WorkflowStep, WorkflowStepStatus, WorkflowPlan
from app.tools.tool_schemas import PermissionLevel

logger = logging.getLogger("nova.agents.scheduler")

class WorkflowScheduler:
    """
    Dependency-aware task scheduler for agent workflows:
    - Resolves directed acyclic graph (DAG) step dependencies.
    - Limits parallel execution strictly to independent, READ_ONLY tasks (max 2).
    - Blocks execution of dependent steps if their prerequisites fail.
    """

    MAX_PARALLEL_READ_ONLY = 2

    @classmethod
    def get_executable_steps(cls, plan: WorkflowPlan) -> List[WorkflowStep]:
        """
        Returns the next batch of steps that are ready for execution.
        A step is ready if:
        1. Its status is PENDING or READY.
        2. All step_ids in its dependencies list have status COMPLETED.
        """
        completed_step_ids = {s.step_id for s in plan.steps if s.status == WorkflowStepStatus.COMPLETED}
        failed_or_cancelled_step_ids = {
            s.step_id for s in plan.steps 
            if s.status in (WorkflowStepStatus.FAILED, WorkflowStepStatus.CANCELLED, WorkflowStepStatus.SKIPPED)
        }

        ready_steps: List[WorkflowStep] = []

        for step in plan.steps:
            if step.status not in (WorkflowStepStatus.PENDING, WorkflowStepStatus.READY):
                continue

            # Check if any prerequisite failed -> mark this step SKIPPED
            if any(dep in failed_or_cancelled_step_ids for dep in step.dependencies):
                step.status = WorkflowStepStatus.SKIPPED
                step.error = f"Prerequisite step(s) {step.dependencies} failed or were skipped."
                continue

            # Check if all prerequisites are completed
            if all(dep in completed_step_ids for dep in step.dependencies):
                ready_steps.append(step)

        # Enforce parallel execution boundaries:
        # If all ready steps are READ_ONLY, allow up to 2 parallel tasks.
        # Otherwise, if any step is stateful/requires confirmation, enforce strict sequential execution.
        if len(ready_steps) > 1:
            all_read_only = all(s.permission_level == PermissionLevel.READ_ONLY for s in ready_steps)
            if all_read_only:
                return ready_steps[:cls.MAX_PARALLEL_READ_ONLY]
            else:
                return [ready_steps[0]]

        return ready_steps

    @classmethod
    def validate_dependencies(cls, steps: List[WorkflowStep]) -> Tuple[bool, Optional[str]]:
        """
        Validates that dependencies do not contain cycles and only reference earlier step IDs.
        """
        step_ids = {s.step_id for s in steps}
        for s in steps:
            for dep in s.dependencies:
                if dep not in step_ids:
                    return False, f"Step {s.step_id} depends on non-existent step {dep}."
                if dep >= s.step_id:
                    return False, f"Step {s.step_id} has invalid forward or self-dependency on step {dep}."

        return True, None
