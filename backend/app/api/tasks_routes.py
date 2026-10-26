from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
import logging

from app.tools.tool_schemas import (
    TaskPlan, TaskPlanRequest, TaskExecuteRequest, TaskStatus,
    RollbackRequest, ExecutionRecord
)
from app.tools.task_planner import task_planner
from app.tools.execution_manager import execution_manager
from app.tools.execution_logger import execution_logger
from app.tools.rollback_manager import rollback_manager, RollbackError

logger = logging.getLogger("nova.api.tasks")

tasks_router = APIRouter(prefix="/tasks", tags=["Tasks"])
executions_router = APIRouter(prefix="/executions", tags=["Executions"])

@tasks_router.post("/plan", response_model=TaskPlan)
async def plan_task_endpoint(payload: TaskPlanRequest):
    """
    Deconstruct natural language request into a validated, multi-step action plan.
    Optionally executes immediately if auto_execute is True and plan requires no confirmation.
    """
    try:
        plan = await task_planner.plan_task(
            prompt=payload.prompt,
            project_id=payload.project_id
        )
        execution_logger.save_task(plan)

        if payload.auto_execute and not plan.requires_confirmation and plan.status != TaskStatus.REJECTED:
            plan = await execution_manager.execute_task(plan)

        return plan
    except Exception as e:
        logger.error(f"Error planning task: {e}")
        raise HTTPException(status_code=500, detail=f"Task planning error: {str(e)}")

@tasks_router.post("/execute", response_model=TaskPlan)
async def execute_task_endpoint(payload: TaskExecuteRequest):
    """
    Execute a previously planned task or a newly submitted plan.
    Pauses and sets status to PENDING_APPROVAL if any steps require confirmation.
    """
    task = None
    if payload.task_id:
        task = execution_logger.get_task(payload.task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task '{payload.task_id}' not found.")
    elif payload.plan:
        task = payload.plan
    else:
        raise HTTPException(status_code=400, detail="Either task_id or plan object must be provided.")

    try:
        executed_plan = await execution_manager.execute_task(task)
        return executed_plan
    except Exception as e:
        logger.error(f"Error executing task: {e}")
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")

@tasks_router.post("/{task_id}/approve", response_model=TaskPlan)
async def approve_task_endpoint(task_id: str):
    """
    Explicitly approve and resume execution of a confirmation-required task.
    """
    res = await execution_manager.approve_and_execute(task_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found or cannot be approved.")
    return res

@tasks_router.post("/{task_id}/reject", response_model=TaskPlan)
async def reject_task_endpoint(task_id: str):
    """
    Reject execution of a confirmation-required task.
    """
    res = execution_manager.reject_task(task_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return res

@tasks_router.post("/{task_id}/cancel", response_model=TaskPlan)
async def cancel_task_endpoint(task_id: str):
    """
    Cancel an active or queued task.
    """
    res = execution_manager.cancel_task(task_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return res

@tasks_router.get("", response_model=List[Dict[str, Any]])
async def list_tasks_endpoint(limit: int = Query(50, ge=1, le=100)):
    """
    Retrieve recent operational task plans and execution statuses.
    """
    return execution_logger.list_tasks(limit=limit)

@tasks_router.get("/{task_id}", response_model=TaskPlan)
async def get_task_endpoint(task_id: str):
    """
    Retrieve full details, steps, and execution status for a specific task.
    """
    task = execution_logger.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return task

@executions_router.get("", response_model=List[Dict[str, Any]])
async def list_executions_endpoint(limit: int = Query(50, ge=1, le=100)):
    """
    Retrieve audit history of executed tools, durations, and outcomes.
    """
    return execution_logger.list_executions(limit=limit)

@executions_router.post("/{execution_id}/rollback")
async def rollback_execution_endpoint(execution_id: str):
    """
    Revert the effect of an eligible file operation.
    """
    try:
        result = rollback_manager.rollback(execution_id)
        return result
    except RollbackError as re:
        raise HTTPException(status_code=400, detail=str(re))
    except Exception as e:
        logger.error(f"Rollback error for '{execution_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal rollback error: {str(e)}")
