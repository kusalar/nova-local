from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional

from app.agents.agent_schemas import AgentMetadata, AgentRole
from app.agents.agent_registry import agent_registry
from app.agents.agent_orchestrator import agent_orchestrator

router = APIRouter(prefix="/agents", tags=["Agent Orchestration"])

@router.get("", response_model=List[AgentMetadata])
async def list_agents():
    """List all registered specialized agents and their active operational status."""
    return agent_orchestrator.list_agents()

@router.get("/status")
async def get_agent_status():
    """Get system-wide agent status, scheduler policies, and thread concurrency metrics."""
    return agent_orchestrator.get_agent_status()

@router.get("/{agent_id}", response_model=AgentMetadata)
async def get_agent(agent_id: str):
    """Retrieve detailed specification, role, and capabilities of a specific agent."""
    agents = agent_orchestrator.list_agents()
    for a in agents:
        if a.id == agent_id or a.role.value.lower() == agent_id.lower():
            return a
    raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
