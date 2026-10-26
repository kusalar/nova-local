from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
import logging

from app.personalization import (
    personalization_manager,
    UserPreference,
    PreferenceCreate,
    PreferenceUpdate,
    PreferenceCategory,
    Recommendation,
    FeedbackRecord,
    FeedbackSubmit,
    ResolvedContext,
    KnowledgeGraphView,
    PersonalizationStatus,
    GraphEntity,
)

logger = logging.getLogger("nova.api.personalization")
router = APIRouter(prefix="/personalization", tags=["Personalization & Adaptive Intelligence"])

# ==================== STATUS & MASTER CONTROLS ====================

@router.get("/status", response_model=PersonalizationStatus)
async def get_personalization_status():
    """Get high-level status of personalization, preference counts, and graph stats."""
    return personalization_manager.get_status()

@router.post("/enable")
async def enable_personalization():
    """Enable personalization and adaptive context features."""
    personalization_manager.enable()
    return {"status": "enabled", "message": "Personalization enabled."}

@router.post("/disable")
async def disable_personalization():
    """Disable personalization, adaptive analysis, and recommendations."""
    personalization_manager.disable()
    return {"status": "disabled", "message": "Personalization disabled."}

@router.post("/refresh")
async def refresh_personalization():
    """Manually trigger sync of knowledge graph, adaptive analysis, and recommendations."""
    return personalization_manager.refresh()

# ==================== USER PREFERENCES ====================

@router.get("/preferences", response_model=List[UserPreference])
async def list_preferences(
    category: Optional[PreferenceCategory] = Query(default=None),
    explicit_only: bool = Query(default=False),
    context_scope: Optional[str] = Query(default=None)
):
    """Retrieve saved user preferences."""
    return personalization_manager.preferences.list_preferences(
        category=category,
        explicit_only=explicit_only,
        context_scope=context_scope
    )

@router.post("/preferences", response_model=UserPreference)
async def create_preference(data: PreferenceCreate):
    """Save an explicit user preference."""
    try:
        return personalization_manager.preferences.set_preference(data)
    except Exception as e:
        logger.error(f"Failed to set preference: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/preferences/{preference_id}", response_model=UserPreference)
async def update_preference(preference_id: str, updates: PreferenceUpdate):
    """Update an existing preference."""
    updated = personalization_manager.preferences.update_preference(preference_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Preference not found")
    return updated

@router.delete("/preferences/{preference_id}")
async def delete_preference(preference_id: str):
    """Remove a user preference."""
    success = personalization_manager.preferences.delete_preference(preference_id)
    if not success:
        raise HTTPException(status_code=404, detail="Preference not found")
    return {"status": "deleted", "id": preference_id}

# ==================== CONTEXT RESOLUTION ====================

@router.get("/context", response_model=ResolvedContext)
async def resolve_context(
    query: str = Query(default=""),
    session_id: str = Query(default="default"),
    project_id: Optional[str] = Query(default=None)
):
    """Resolve active context combining explicit instructions, project memory, and preferences."""
    return personalization_manager.context.resolve_context(
        user_query=query,
        session_id=session_id,
        explicit_project_id=project_id
    )

# ==================== RECOMMENDATIONS ====================

@router.get("/recommendations", response_model=List[Recommendation])
async def list_recommendations(active_only: bool = Query(default=True)):
    """Retrieve evidence-based recommendations."""
    return personalization_manager.recommendations.list_recommendations(active_only=active_only)

@router.post("/recommendations/{recommendation_id}/feedback", response_model=FeedbackRecord)
async def submit_recommendation_feedback(recommendation_id: str, feedback: FeedbackSubmit):
    """Record user feedback ('USEFUL', 'DISMISS_PERMANENT') on a recommendation."""
    rec = personalization_manager.recommendations.get_recommendation(recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return personalization_manager.feedback.record_feedback(
        feedback_type=feedback.feedback_type.value,
        target_type="recommendation",
        target_id=recommendation_id,
        user_correction=feedback.user_correction
    )

# ==================== KNOWLEDGE GRAPH ====================

@router.get("/knowledge-graph", response_model=KnowledgeGraphView)
async def get_knowledge_graph(project_id: Optional[str] = Query(default=None)):
    """Retrieve full knowledge graph view (entities and relations)."""
    return personalization_manager.graph.get_full_graph_view(project_id=project_id)

@router.get("/knowledge-graph/{entity_id}")
async def get_knowledge_graph_entity(entity_id: str):
    """Retrieve a specific entity and its incoming/outgoing subgraph."""
    subgraph = personalization_manager.graph.get_entity_subgraph(entity_id)
    if not subgraph.get("entity"):
        raise HTTPException(status_code=404, detail="Entity not found")
    return subgraph

@router.delete("/knowledge-graph/{entity_id}")
async def delete_knowledge_graph_entity(entity_id: str):
    """Remove an entity and its associated relationships from the knowledge graph."""
    success = personalization_manager.graph.delete_entity(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"status": "deleted", "id": entity_id}
