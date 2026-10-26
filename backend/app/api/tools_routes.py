from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.tools.tool_registry import tool_registry
from app.tools.tool_schemas import ToolDefinition, ToolCategory, PermissionLevel

router = APIRouter(prefix="/tools", tags=["Tools"])

@router.get("", response_model=List[ToolDefinition])
async def list_tools(
    category: Optional[ToolCategory] = Query(None, description="Filter by tool category"),
    permission: Optional[PermissionLevel] = Query(None, description="Filter by permission level")
):
    """List all registered tools available in NOVA v0.4."""
    return tool_registry.list_tools(category=category, permission_level=permission)

@router.get("/{tool_id}", response_model=ToolDefinition)
async def get_tool(tool_id: str):
    """Retrieve detailed specification and parameter schema for a specific tool."""
    definition = tool_registry.get_definition(tool_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found.")
    return definition
