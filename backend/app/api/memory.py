from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging

from app.memory.long_term_memory import long_term_memory
from app.memory.memory_manager import memory_manager
from app.memory.memory_models import (
    MemoryCategory, MemoryCreate, MemoryUpdate, MemoryItem,
    ProjectCreate, ProjectUpdate, ProjectItem, ConversationSummaryItem,
    MemoryExtractRequest, MemoryForgetRequest
)

logger = logging.getLogger("nova.api.memory")

router = APIRouter(prefix="/memory", tags=["Persistent Intelligence & Memory"])

@router.get("", response_model=List[MemoryItem])
async def list_memories(
    category: Optional[MemoryCategory] = None,
    project_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Retrieve persistent memories filtered by category and project."""
    return long_term_memory.list_memories(
        category=category,
        project_id=project_id,
        limit=limit,
        offset=offset
    )

@router.get("/stats")
async def get_memory_stats():
    """Retrieve statistical summary of persistent neural memory bank."""
    return long_term_memory.get_memory_stats()

@router.get("/search", response_model=List[MemoryItem])
async def search_memories(
    q: str = Query(..., min_length=1, description="Semantic or keyword query"),
    category: Optional[MemoryCategory] = None,
    project_id: Optional[str] = None,
    limit: int = Query(5, ge=1, le=50),
    threshold: float = Query(0.40, ge=0.0, le=1.0)
):
    """Perform local semantic vector search with keyword fallback."""
    return long_term_memory.search_memories(
        query=q,
        category=category,
        project_id=project_id,
        limit=limit,
        threshold=threshold
    )

@router.get("/projects", response_model=List[ProjectItem])
async def list_projects():
    """List all tracked software and operational projects."""
    return long_term_memory.list_projects()

@router.get("/projects/{project_id}", response_model=ProjectItem)
async def get_project(project_id: str):
    """Retrieve detailed project intelligence record."""
    proj = long_term_memory.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return proj

@router.post("/projects", response_model=ProjectItem)
async def create_project(payload: ProjectCreate):
    """Create a new project memory workspace."""
    proj = long_term_memory.create_project(payload)
    if not proj:
        raise HTTPException(status_code=400, detail="Failed to create project.")
    return proj

@router.patch("/projects/{project_id}", response_model=ProjectItem)
async def update_project(project_id: str, payload: ProjectUpdate):
    """Update project metadata, tech stack, decisions, or tasks."""
    proj = long_term_memory.update_project(project_id, payload)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return proj

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete project workspace and associated project memories."""
    success = long_term_memory.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return {"success": True, "message": f"Project '{project_id}' deleted."}

@router.post("", response_model=MemoryItem)
async def create_memory(payload: MemoryCreate):
    """Store an explicit memory item with vector embedding."""
    mem = long_term_memory.create_memory(payload)
    if not mem:
        raise HTTPException(status_code=400, detail="Failed to create memory.")
    return mem

@router.patch("/{memory_id}", response_model=MemoryItem)
async def update_memory(memory_id: int, payload: MemoryUpdate):
    """Update an existing memory item."""
    mem = long_term_memory.update_memory(memory_id, payload)
    if not mem:
        raise HTTPException(status_code=404, detail=f"Memory #{memory_id} not found.")
    return mem

@router.delete("/{memory_id}")
async def delete_memory(memory_id: int):
    """Purge a single memory item by ID."""
    success = long_term_memory.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Memory #{memory_id} not found.")
    return {"success": True, "message": f"Memory #{memory_id} purged."}

@router.post("/extract")
async def extract_memories(payload: MemoryExtractRequest):
    """Analyze text and extract structured memories."""
    extracted = memory_manager.process_turn_and_extract(
        user_query=payload.text,
        session_id=payload.session_id or "default",
        project_id=payload.project_id
    )
    return {
        "success": True,
        "count": len(extracted),
        "extracted": extracted
    }

@router.post("/summarize")
async def summarize_conversation(session_id: str = "default"):
    """Trigger summarization of session conversation history."""
    from app.memory.sqlite_memory import memory_bank
    messages = memory_bank.get_messages(session_id=session_id, limit=50)
    summary = await memory_manager.summarizer.summarize_session(
        messages=messages,
        session_id=session_id
    )
    return {
        "success": True,
        "session_id": session_id,
        "summary": summary
    }

@router.post("/forget")
async def forget_memories(payload: MemoryForgetRequest):
    """Purge memories matching keyword, phrase, or ID."""
    count = long_term_memory.forget_memories(
        target=payload.target,
        category=payload.category,
        project_id=payload.project_id
    )
    return {
        "success": True,
        "deleted_count": count,
        "message": f"Purged {count} memory record(s) matching '{payload.target}'."
    }
