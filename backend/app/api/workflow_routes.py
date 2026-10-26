from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional

from app.agents.agent_schemas import (
    WorkflowPlan, PlanWorkflowRequest, ExecuteWorkflowRequest,
    WorkflowReport, WorkflowEvent
)
from app.agents.agent_orchestrator import agent_orchestrator
from app.agents.workflow_logger import workflow_logger

router = APIRouter(prefix="/workflows", tags=["Workflows"])

@router.get("", response_model=List[Dict[str, Any]])
async def list_workflows(limit: int = Query(50, ge=1, le=200)):
    """List recent agentic workflows with summary state and completion progress."""
    return agent_orchestrator.list_workflows(limit=limit)

@router.get("/{workflow_id}", response_model=WorkflowPlan)
async def get_workflow(workflow_id: str):
    """Retrieve complete workflow plan, steps, results, and reflection records."""
    plan = agent_orchestrator.get_workflow(workflow_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    return plan

@router.post("/plan", response_model=WorkflowPlan)
async def plan_workflow(request: PlanWorkflowRequest):
    """
    Decompose a natural-language objective into a structured, dependency-ordered,
    permission-validated workflow plan without immediately executing it.
    """
    try:
        return await agent_orchestrator.plan_workflow(
            objective=request.objective,
            project_id=request.project_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate workflow plan: {str(e)}")

@router.post("/execute", response_model=WorkflowPlan)
async def execute_workflow(request: ExecuteWorkflowRequest):
    """
    Initiate execution of a planned workflow by workflow_id or plan payload.
    """
    try:
        if request.plan:
            return await agent_orchestrator.execute_workflow(request.plan)
        elif request.workflow_id:
            return await agent_orchestrator.execute_workflow(request.workflow_id)
        else:
            raise HTTPException(status_code=400, detail="Must provide either 'workflow_id' or 'plan'.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")

@router.post("/{workflow_id}/approve", response_model=WorkflowPlan)
async def approve_workflow_step(
    workflow_id: str,
    step_id: Optional[int] = Query(None, description="Specific step ID to approve")
):
    """
    Approve a paused step requiring confirmation, safely unblocking the workflow.
    """
    plan = agent_orchestrator.get_workflow(workflow_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")

    target_step = step_id or plan.pending_approval_step_id
    if not target_step:
        raise HTTPException(status_code=400, detail="No step currently pending approval.")

    res = await agent_orchestrator.approve_step(workflow_id, target_step)
    if not res:
        raise HTTPException(status_code=500, detail="Failed to approve step.")
    return res

@router.post("/{workflow_id}/reject", response_model=WorkflowPlan)
async def reject_workflow_step(
    workflow_id: str,
    step_id: Optional[int] = Query(None, description="Specific step ID to reject")
):
    """
    Reject a pending confirmation step and halt the workflow.
    """
    plan = agent_orchestrator.get_workflow(workflow_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")

    target_step = step_id or plan.pending_approval_step_id
    if not target_step:
        raise HTTPException(status_code=400, detail="No step currently pending approval.")

    res = await agent_orchestrator.reject_step(workflow_id, target_step)
    if not res:
        raise HTTPException(status_code=500, detail="Failed to reject step.")
    return res

@router.post("/{workflow_id}/cancel", response_model=WorkflowPlan)
async def cancel_workflow(workflow_id: str):
    """
    Explicitly cancel an ongoing or paused workflow.
    """
    res = await agent_orchestrator.cancel_workflow(workflow_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    return res

@router.post("/{workflow_id}/resume", response_model=WorkflowPlan)
async def resume_workflow(workflow_id: str):
    """
    Resume execution of a paused or restart-recovered workflow.
    """
    plan = agent_orchestrator.get_workflow(workflow_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")

    return await agent_orchestrator.execute_workflow(plan)

@router.get("/{workflow_id}/events", response_model=List[Dict[str, Any]])
async def get_workflow_events(workflow_id: str):
    """
    Retrieve chronological audit trail of all step executions, approvals, and reflection events.
    """
    return agent_orchestrator.get_workflow_events(workflow_id)

@router.get("/{workflow_id}/report", response_model=Dict[str, Any])
async def get_workflow_report(workflow_id: str):
    """
    Retrieve final reflection summary and verifiable evidence report.
    """
    plan = agent_orchestrator.get_workflow(workflow_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")

    return {
        "workflow_id": plan.workflow_id,
        "objective": plan.objective,
        "status": plan.status.value,
        "final_report": plan.final_report,
        "completed_steps": plan.completed_steps,
        "total_steps": plan.total_steps
    }
