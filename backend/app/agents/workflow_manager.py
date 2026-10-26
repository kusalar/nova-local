import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .agent_schemas import (
    WorkflowPlan, WorkflowStep, WorkflowStatus, WorkflowStepStatus,
    EventType, AgentRole, WorkflowReport
)
from .agent_context import AgentContext
from .agent_registry import agent_registry
from .agent_scheduler import WorkflowScheduler
from .agent_permissions import AgentPermissionEnforcer
from .agent_reflection import AgentReflectionEngine
from .agent_events import AgentEventBus
from .workflow_logger import workflow_logger
from app.tools.tool_schemas import PermissionLevel

logger = logging.getLogger("nova.agents.workflow_manager")

class WorkflowManager:
    """
    Stateful execution engine for agentic workflows:
    - Executes steps respecting DAG dependencies.
    - Limits parallel execution strictly to independent, READ_ONLY steps (max 2).
    - Enforces human approval checkpoints for CONFIRMATION_REQUIRED steps.
    - Handles timeouts, bounded retries (max 2), and reflection.
    - Synthesizes final verifiable reports.
    """

    def __init__(self):
        self._active_contexts: Dict[str, AgentContext] = {}

    def get_context(self, workflow_id: str, plan: Optional[WorkflowPlan] = None) -> AgentContext:
        """Retrieves or creates shared execution context for a workflow."""
        if workflow_id not in self._active_contexts:
            obj = plan.objective if plan else "Unknown Objective"
            proj = plan.project_id if plan else None
            self._active_contexts[workflow_id] = AgentContext(workflow_id, obj, proj)
        return self._active_contexts[workflow_id]

    async def execute_workflow(self, plan: WorkflowPlan) -> WorkflowPlan:
        """
        Executes a workflow plan asynchronously through its step lifecycle.
        """
        start_time = time.time()
        context = self.get_context(plan.workflow_id, plan)

        plan.status = WorkflowStatus.RUNNING
        workflow_logger.save_workflow(plan)

        AgentEventBus.emit(
            workflow_id=plan.workflow_id,
            event_type=EventType.WORKFLOW_STARTED,
            message=f"Workflow started: {plan.objective}"
        )

        while True:
            # Check for cancellation or external pause
            current = workflow_logger.get_workflow(plan.workflow_id)
            if current and current.status in (WorkflowStatus.CANCELLED, WorkflowStatus.FAILED):
                plan.status = current.status
                return plan

            # 1. Fetch next executable steps according to DAG scheduler
            ready_steps = WorkflowScheduler.get_executable_steps(plan)

            if not ready_steps:
                # No more steps ready. Check if workflow is complete or paused
                incomplete = [s for s in plan.steps if s.status not in (
                    WorkflowStepStatus.COMPLETED, WorkflowStepStatus.FAILED,
                    WorkflowStepStatus.SKIPPED, WorkflowStepStatus.CANCELLED
                )]

                if not incomplete:
                    # All steps reached terminal state
                    has_failures = any(s.status == WorkflowStepStatus.FAILED for s in plan.steps)
                    plan.status = WorkflowStatus.FAILED if has_failures else WorkflowStatus.COMPLETED
                    plan.completed_at = datetime.now().isoformat()
                    break

                # If steps remain incomplete but none are executable, check for approvals
                pending_approval = next((s for s in plan.steps if s.status == WorkflowStepStatus.PENDING_APPROVAL), None)
                if pending_approval:
                    plan.status = WorkflowStatus.PENDING_APPROVAL
                    plan.requires_approval = True
                    plan.pending_approval_step_id = pending_approval.step_id
                    plan.approval_reason = f"Step {pending_approval.step_id} requires human approval: {pending_approval.description}"
                    workflow_logger.save_workflow(plan)
                    
                    AgentEventBus.emit(
                        workflow_id=plan.workflow_id,
                        event_type=EventType.STEP_PAUSED_APPROVAL,
                        step_id=pending_approval.step_id,
                        message=plan.approval_reason
                    )
                    return plan

                # Deadlock or broken dependencies -> finish workflow
                logger.warning(f"Workflow {plan.workflow_id} halted: no steps ready to execute.")
                plan.status = WorkflowStatus.FAILED
                break

            # 2. Check if any ready step requires approval before running
            approval_step = next((s for s in ready_steps if s.permission_level == PermissionLevel.CONFIRMATION_REQUIRED), None)
            if approval_step:
                approval_step.status = WorkflowStepStatus.PENDING_APPROVAL
                plan.status = WorkflowStatus.PENDING_APPROVAL
                plan.requires_approval = True
                plan.pending_approval_step_id = approval_step.step_id
                plan.approval_reason = f"Step {approval_step.step_id} ({approval_step.description}) requires approval."
                workflow_logger.save_workflow(plan)
                
                AgentEventBus.emit(
                    workflow_id=plan.workflow_id,
                    event_type=EventType.STEP_PAUSED_APPROVAL,
                    step_id=approval_step.step_id,
                    message=plan.approval_reason
                )
                return plan

            # 3. Execute batch of ready steps (sequentially or parallel if read-only)
            if len(ready_steps) == 1:
                await self._execute_single_step(ready_steps[0], plan, context)
            else:
                # Parallel execution for up to 2 read-only steps
                tasks = [self._execute_single_step(s, plan, context) for s in ready_steps]
                await asyncio.gather(*tasks)

            # Update completed steps count and persist
            plan.completed_steps = sum(1 for s in plan.steps if s.status == WorkflowStepStatus.COMPLETED)
            workflow_logger.save_workflow(plan)

        # 4. Generate final reflection report
        duration = time.time() - start_time
        report = await AgentReflectionEngine.generate_workflow_report(plan, context, duration)
        plan.final_report = report.summary
        workflow_logger.save_workflow(plan)

        AgentEventBus.emit(
            workflow_id=plan.workflow_id,
            event_type=EventType.WORKFLOW_COMPLETED if plan.status == WorkflowStatus.COMPLETED else EventType.WORKFLOW_FAILED,
            message=f"Workflow completed: {report.summary[:100]}",
            payload={"report": report.dict()}
        )

        return plan

    async def _execute_single_step(self, step: WorkflowStep, plan: WorkflowPlan, context: AgentContext):
        """Executes a single step with timeout, retry tracking, and reflection."""
        step.status = WorkflowStepStatus.RUNNING
        step.started_at = datetime.now().isoformat()
        workflow_logger.save_workflow(plan)

        AgentEventBus.emit(
            workflow_id=plan.workflow_id,
            event_type=EventType.STEP_STARTED,
            step_id=step.step_id,
            agent_role=step.assigned_agent,
            message=f"Step {step.step_id} started by {step.assigned_agent.value}: {step.description}"
        )

        agent = agent_registry.get_agent(step.assigned_agent)
        if not agent:
            step.status = WorkflowStepStatus.FAILED
            step.error = f"No agent registered for role '{step.assigned_agent}'."
            step.completed_at = datetime.now().isoformat()
            return

        try:
            # Enforce step timeout
            result = await asyncio.wait_for(
                agent.execute_step(step, context),
                timeout=step.timeout_seconds
            )
            step.result = result

            # Bounded reflection
            reflection = await AgentReflectionEngine.evaluate_step(step, result, context)
            step.reflection = reflection.evidence

            if reflection.success and reflection.goal_satisfied:
                step.status = WorkflowStepStatus.COMPLETED
                step.error = None
                context.record_step_result(step.step_id, result)
                
                AgentEventBus.emit(
                    workflow_id=plan.workflow_id,
                    event_type=EventType.STEP_COMPLETED,
                    step_id=step.step_id,
                    agent_role=step.assigned_agent,
                    message=f"Step {step.step_id} completed: {reflection.evidence[:80]}"
                )
            else:
                # Handle retry policy
                if step.retry_policy.retry_count < step.retry_policy.max_retries:
                    step.retry_policy.retry_count += 1
                    step.status = WorkflowStepStatus.PENDING # Re-queue for retry
                    logger.info(f"Retrying step {step.step_id} (Attempt {step.retry_policy.retry_count}/{step.retry_policy.max_retries})")
                else:
                    step.status = WorkflowStepStatus.FAILED
                    step.error = reflection.evidence
                    context.unresolved_issues.append(f"Step {step.step_id} failed: {reflection.evidence}")

                    AgentEventBus.emit(
                        workflow_id=plan.workflow_id,
                        event_type=EventType.STEP_FAILED,
                        step_id=step.step_id,
                        agent_role=step.assigned_agent,
                        message=f"Step {step.step_id} failed: {step.error[:100]}"
                    )

        except asyncio.TimeoutError:
            step.status = WorkflowStepStatus.FAILED
            step.error = f"Step timed out after {step.timeout_seconds} seconds."
            context.unresolved_issues.append(f"Step {step.step_id} timed out.")
        except Exception as e:
            step.status = WorkflowStepStatus.FAILED
            step.error = str(e)
            context.unresolved_issues.append(f"Step {step.step_id} error: {str(e)}")
        finally:
            step.completed_at = datetime.now().isoformat()
            workflow_logger.save_workflow(plan)

    # ==========================================
    # Approval & Control Flow
    # ==========================================

    def generate_approval_token(self, workflow_id: str, step_id: int) -> str:
        """Generates a cryptographically signed, single-use approval token for a workflow step."""
        from app.security.approval_tokens import approval_token_manager
        return approval_token_manager.generate_token(action_type="workflow_step", target_id=f"{workflow_id}:{step_id}")

    async def approve_step(self, workflow_id: str, step_id: int, approval_token: Optional[str] = None) -> Optional[WorkflowPlan]:
        """Human approval for a specific paused step, with optional single-use token verification."""
        if approval_token:
            from app.security.approval_tokens import approval_token_manager
            valid = approval_token_manager.verify_and_consume_token(
                approval_token, "workflow_step", f"{workflow_id}:{step_id}"
            )
            if not valid:
                logger.warning(f"Invalid or expired approval token for workflow '{workflow_id}', step {step_id}.")
                raise PermissionError("Approval token is invalid, expired, or already used.")

        plan = workflow_logger.get_workflow(workflow_id)
        if not plan:
            return None

        step = next((s for s in plan.steps if s.step_id == step_id), None)
        if not step or step.status != WorkflowStepStatus.PENDING_APPROVAL:
            return plan

        step.status = WorkflowStepStatus.READY
        step.permission_level = PermissionLevel.LOW_RISK # Mark as approved
        plan.requires_approval = False
        plan.pending_approval_step_id = None
        plan.approval_reason = None
        plan.status = WorkflowStatus.RUNNING
        workflow_logger.save_workflow(plan)

        AgentEventBus.emit(
            workflow_id=workflow_id,
            event_type=EventType.STEP_APPROVED,
            step_id=step_id,
            message=f"Step {step_id} approved by user."
        )

        # Resume execution
        return await self.execute_workflow(plan)

    async def reject_step(self, workflow_id: str, step_id: int) -> Optional[WorkflowPlan]:
        """Human rejection of a paused step."""
        plan = workflow_logger.get_workflow(workflow_id)
        if not plan:
            return None

        step = next((s for s in plan.steps if s.step_id == step_id), None)
        if step:
            step.status = WorkflowStepStatus.CANCELLED
            step.error = "Rejected by user approval checkpoint."

        plan.status = WorkflowStatus.CANCELLED
        plan.requires_approval = False
        plan.completed_at = datetime.now().isoformat()
        workflow_logger.save_workflow(plan)

        AgentEventBus.emit(
            workflow_id=workflow_id,
            event_type=EventType.STEP_REJECTED,
            step_id=step_id,
            message=f"Step {step_id} rejected. Workflow halted."
        )

        return plan

    async def cancel_workflow(self, workflow_id: str) -> Optional[WorkflowPlan]:
        """Cancels an ongoing workflow and halts future steps."""
        plan = workflow_logger.get_workflow(workflow_id)
        if not plan:
            return None

        for s in plan.steps:
            if s.status in (WorkflowStepStatus.PENDING, WorkflowStepStatus.READY, WorkflowStepStatus.PENDING_APPROVAL):
                s.status = WorkflowStepStatus.CANCELLED

        plan.status = WorkflowStatus.CANCELLED
        plan.completed_at = datetime.now().isoformat()
        workflow_logger.save_workflow(plan)

        AgentEventBus.emit(
            workflow_id=workflow_id,
            event_type=EventType.WORKFLOW_CANCELLED,
            message="Workflow cancelled by user directive."
        )

        return plan

# Singleton
workflow_manager = WorkflowManager()
