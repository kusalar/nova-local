import logging
from typing import Dict, Any, Optional, List

from .agent_schemas import (
    WorkflowPlan, WorkflowStep, WorkflowStatus, AgentRole,
    AgentMetadata, WorkflowReport
)
from .agent_planner import AgentPlanner
from .workflow_manager import workflow_manager
from .workflow_logger import workflow_logger
from .agent_registry import agent_registry
from .agent_events import AgentEventBus, EventType

logger = logging.getLogger("nova.agents.orchestrator")

class AgentOrchestrator:
    """
    Central orchestration coordinator for NOVA v0.6:
    - Ingests high-level objectives.
    - Generates dependency-ordered, safety-checked workflow plans.
    - Dispatches execution to specialized agents.
    - Manages human confirmation checkpoints.
    - Interfaces with voice command handlers and REST endpoints.
    """

    def __init__(self):
        # Trigger crash/restart recovery check on boot
        workflow_logger.handle_restart_recovery()

    async def plan_workflow(self, objective: str, project_id: Optional[str] = None) -> WorkflowPlan:
        """Plans a structured multi-agent workflow from a user directive."""
        plan = await AgentPlanner.create_plan(objective, project_id=project_id)
        workflow_logger.save_workflow(plan)
        
        AgentEventBus.emit(
            workflow_id=plan.workflow_id,
            event_type=EventType.WORKFLOW_PLANNED,
            message=f"Plan generated with {len(plan.steps)} steps."
        )
        return plan

    async def execute_workflow(self, plan_or_id: Any) -> WorkflowPlan:
        """Executes a planned workflow by plan object or workflow_id."""
        if isinstance(plan_or_id, str):
            plan = workflow_logger.get_workflow(plan_or_id)
            if not plan:
                raise ValueError(f"Workflow '{plan_or_id}' not found.")
        else:
            plan = plan_or_id

        return await workflow_manager.execute_workflow(plan)

    async def plan_and_execute(self, objective: str, project_id: Optional[str] = None) -> WorkflowPlan:
        """Convenience method to plan and immediately initiate execution."""
        plan = await self.plan_workflow(objective, project_id=project_id)
        if plan.requires_approval and plan.steps[0].permission_level.value == "CONFIRMATION_REQUIRED":
            # If the very first step requires confirmation, return plan paused
            plan.status = WorkflowStatus.PENDING_APPROVAL
            workflow_logger.save_workflow(plan)
            return plan

        return await self.execute_workflow(plan)

    async def approve_step(self, workflow_id: str, step_id: int) -> Optional[WorkflowPlan]:
        return await workflow_manager.approve_step(workflow_id, step_id)

    async def reject_step(self, workflow_id: str, step_id: int) -> Optional[WorkflowPlan]:
        return await workflow_manager.reject_step(workflow_id, step_id)

    async def cancel_workflow(self, workflow_id: str) -> Optional[WorkflowPlan]:
        return await workflow_manager.cancel_workflow(workflow_id)

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowPlan]:
        return workflow_logger.get_workflow(workflow_id)

    def list_workflows(self, limit: int = 50) -> List[Dict[str, Any]]:
        return workflow_logger.list_workflows(limit=limit)

    def get_workflow_events(self, workflow_id: str) -> List[Dict[str, Any]]:
        return workflow_logger.get_workflow_events(workflow_id)

    def list_agents(self) -> List[AgentMetadata]:
        return agent_registry.list_agents()

    def get_agent_status(self) -> Dict[str, Any]:
        agents = agent_registry.list_agents()
        return {
            "active_agents": len(agents),
            "agents": [a.dict() for a in agents],
            "scheduler_policy": "DAG Dependency Order (Max 2 Parallel Read-Only)"
        }

    async def handle_voice_agentic_command(self, transcript: str) -> Dict[str, Any]:
        """
        Parses high-level voice instructions, creates plan, and executes or pauses for vocal approval.
        """
        lower = transcript.lower()

        # Cancellation command
        if any(w in lower for w in ["stop the current workflow", "stop workflow", "cancel workflow", "abort workflow"]):
            recent = self.list_workflows(limit=1)
            if recent and recent[0]["status"] in ("RUNNING", "PENDING_APPROVAL", "PAUSED"):
                wf_id = recent[0]["workflow_id"]
                await self.cancel_workflow(wf_id)
                return {
                    "action": "cancelled",
                    "spoken_response": "The current workflow has been stopped.",
                    "workflow_id": wf_id
                }
            return {
                "action": "none",
                "spoken_response": "There are no active workflows running.",
                "workflow_id": None
            }

        # Plan and initiate workflow
        plan = await self.plan_workflow(transcript)
        
        if plan.requires_approval:
            spoken = (
                f"I have formulated a plan with {len(plan.steps)} steps to {plan.objective}. "
                f"Step {plan.pending_approval_step_id} requires confirmation. Would you like me to proceed?"
            )
            return {
                "action": "pending_approval",
                "plan": plan,
                "spoken_response": spoken,
                "workflow_id": plan.workflow_id
            }
        else:
            # Safe to start execution
            asyncio.create_task(self.execute_workflow(plan))
            spoken = f"Initiating workflow with {len(plan.steps)} steps for {plan.objective}."
            return {
                "action": "executing",
                "plan": plan,
                "spoken_response": spoken,
                "workflow_id": plan.workflow_id
            }

# Global singleton
agent_orchestrator = AgentOrchestrator()
