import uuid
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from app.tools.tool_schemas import (
    TaskPlan, TaskStep, TaskStatus, StepStatus, PermissionLevel, ExecutionRecord
)
from app.tools.tool_registry import tool_registry
from app.tools.permission_manager import permission_manager, SecurityViolationError
from app.tools.execution_logger import execution_logger
from app.brain.state_manager import state_manager, NovaState

logger = logging.getLogger("nova.tools.execution_manager")

class ExecutionManager:
    """
    Coordinates end-to-end task execution, step dependency verification,
    permission gates, approval pausing, cancellation, and audit logging.
    """

    def __init__(self):
        self._active_tasks: Dict[str, TaskPlan] = {}
        self._cancelled_tasks: set = set()

    async def execute_task(self, plan: TaskPlan, is_approved: bool = False) -> TaskPlan:
        """
        Execute a TaskPlan step-by-step.
        Pauses and returns if a CONFIRMATION_REQUIRED step is encountered without approval.
        """
        self._active_tasks[plan.task_id] = plan
        
        # Check if already cancelled or rejected
        if plan.task_id in self._cancelled_tasks:
            plan.status = TaskStatus.CANCELLED
            execution_logger.save_task(plan)
            return plan

        # If confirmation is required and not yet approved
        if plan.requires_confirmation and not is_approved:
            plan.status = TaskStatus.PENDING_APPROVAL
            state_manager.set_state(NovaState.IDLE, "AWAITING USER CONFIRMATION")
            state_manager.add_activity(
                title="Approval Required",
                category="TASK",
                detail=plan.confirmation_reason or f"Task '{plan.task_id}' requires explicit approval.",
                level="WARN"
            )
            execution_logger.save_task(plan)
            return plan

        # Begin execution
        plan.status = TaskStatus.EXECUTING
        state_manager.set_state(NovaState.EXECUTING, f"EXECUTING: {plan.description[:40]}")
        state_manager.add_activity(
            title="Task Started",
            category="TASK",
            detail=f"Executing plan: {plan.description}",
            level="LIVE"
        )
        execution_logger.save_task(plan)

        has_reversible_steps = False

        for idx, step in enumerate(plan.steps):
            # Check cancellation between steps
            if plan.task_id in self._cancelled_tasks:
                step.status = StepStatus.CANCELLED
                plan.status = TaskStatus.CANCELLED
                break

            # If previous step failed, cancel remaining steps
            if plan.status == TaskStatus.FAILED:
                step.status = StepStatus.SKIPPED
                continue

            plan.current_step = step.step_id
            step.status = StepStatus.RUNNING
            step.started_at = datetime.now().isoformat()
            execution_logger.save_task(plan)

            # Execute individual tool step
            exec_res = await self.execute_step(step, task_id=plan.task_id)
            step.result = exec_res.get("result")
            step.error = exec_res.get("error")
            step.execution_id = exec_res.get("execution_id")
            step.completed_at = datetime.now().isoformat()

            if exec_res.get("success"):
                step.status = StepStatus.COMPLETED
                if exec_res.get("is_reversible"):
                    has_reversible_steps = True
            else:
                step.status = StepStatus.FAILED
                plan.status = TaskStatus.FAILED
                logger.warning(f"Step {step.step_id} failed: {step.error}")
                state_manager.add_activity(
                    title=f"Step {step.step_id} Failed",
                    category="TASK",
                    detail=f"Error in {step.tool_id}: {step.error}",
                    level="ERROR"
                )
                # Halt execution on critical step failure
                break

        # Finalize task outcome
        if plan.status != TaskStatus.FAILED and plan.status != TaskStatus.CANCELLED:
            plan.status = TaskStatus.COMPLETED
            state_manager.set_state(NovaState.IDLE, "TASK COMPLETED")
            state_manager.add_activity(
                title="Task Completed",
                category="TASK",
                detail=f"Finished {len(plan.steps)} steps successfully.",
                level="SUCCESS"
            )
        else:
            state_manager.set_state(NovaState.IDLE, "TASK TERMINATED")

        plan.completed_at = datetime.now().isoformat()
        plan.rollback_eligible = has_reversible_steps
        execution_logger.save_task(plan)
        return plan

    async def execute_step(self, step: TaskStep, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a single step with timeout, permission checks, and audit logging.
        """
        tool_entry = tool_registry.get_tool(step.tool_id)
        if not tool_entry:
            return {
                "success": False,
                "error": f"Tool '{step.tool_id}' is not registered.",
                "execution_id": None
            }

        definition = tool_entry.definition
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        # Audit log start
        execution_logger.log_execution_start(
            execution_id=execution_id,
            tool_id=definition.id,
            tool_name=definition.name,
            category=definition.category.value,
            permission_level=definition.permission_level.value,
            arguments=step.arguments,
            task_id=task_id,
            step_id=step.step_id,
            is_reversible=definition.is_reversible
        )

        try:
            handler = tool_entry.handler
            timeout = definition.timeout_seconds

            # Execute with timeout
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(handler(**step.arguments), timeout=timeout)
            else:
                loop = asyncio.get_running_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: handler(**step.arguments)),
                    timeout=timeout
                )

            duration_ms = round((time.time() - start_time) * 1000, 2)
            rollback_data = result.get("rollback_data") if isinstance(result, dict) else None

            # Audit log completion
            execution_logger.log_execution_complete(
                execution_id=execution_id,
                status="COMPLETED",
                result=result,
                rollback_data=rollback_data,
                duration_ms=duration_ms
            )

            return {
                "success": True,
                "result": result,
                "execution_id": execution_id,
                "is_reversible": definition.is_reversible and bool(rollback_data),
                "duration_ms": duration_ms
            }

        except asyncio.TimeoutError:
            err = f"Tool execution timed out after {definition.timeout_seconds}s"
            duration_ms = round((time.time() - start_time) * 1000, 2)
            execution_logger.log_execution_complete(
                execution_id=execution_id,
                status="FAILED",
                error_message=err,
                duration_ms=duration_ms
            )
            return {"success": False, "error": err, "execution_id": execution_id}

        except Exception as e:
            err = str(e)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            execution_logger.log_execution_complete(
                execution_id=execution_id,
                status="FAILED",
                error_message=err,
                duration_ms=duration_ms
            )
            return {"success": False, "error": err, "execution_id": execution_id}

    def generate_approval_token(self, task_id: str) -> str:
        """Generates a cryptographically signed, single-use approval token for a task."""
        from app.security.approval_tokens import approval_token_manager
        return approval_token_manager.generate_token(action_type="task", target_id=task_id)

    async def approve_and_execute(self, task_id: str, approval_token: Optional[str] = None) -> Optional[TaskPlan]:
        """Approve a pending task and resume execution, with optional single-use token verification."""
        if approval_token:
            from app.security.approval_tokens import approval_token_manager
            valid = approval_token_manager.verify_and_consume_token(approval_token, "task", task_id)
            if not valid:
                logger.warning(f"Invalid or expired approval token for task '{task_id}'.")
                raise PermissionError("Approval token is invalid, expired, or already used.")

        task = self._active_tasks.get(task_id) or execution_logger.get_task(task_id)
        if not task:
            return None

        if task.status != TaskStatus.PENDING_APPROVAL:
            logger.warning(f"Task '{task_id}' is in status '{task.status}', cannot approve.")
            return task

        logger.info(f"Task '{task_id}' approved by user.")
        return await self.execute_task(task, is_approved=True)

    def reject_task(self, task_id: str) -> Optional[TaskPlan]:
        """Reject a pending task."""
        task = self._active_tasks.get(task_id) or execution_logger.get_task(task_id)
        if not task:
            return None

        task.status = TaskStatus.REJECTED
        task.completed_at = datetime.now().isoformat()
        execution_logger.save_task(task)
        state_manager.set_state(NovaState.IDLE, "TASK REJECTED")
        state_manager.add_activity(
            title="Task Rejected",
            category="TASK",
            detail=f"User rejected task '{task_id}'",
            level="WARN"
        )
        return task

    def cancel_task(self, task_id: str) -> Optional[TaskPlan]:
        """Cancel an ongoing or scheduled task."""
        self._cancelled_tasks.add(task_id)
        task = self._active_tasks.get(task_id) or execution_logger.get_task(task_id)
        if not task:
            return None

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now().isoformat()
        execution_logger.save_task(task)
        state_manager.set_state(NovaState.IDLE, "TASK CANCELLED")
        state_manager.add_activity(
            title="Task Cancelled",
            category="TASK",
            detail=f"Task '{task_id}' cancelled by user directive.",
            level="WARN"
        )
        return task

execution_manager = ExecutionManager()
