import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.personalization import (
    personalization_manager,
    preference_engine,
    knowledge_graph,
    context_resolver,
    recommendation_engine,
    feedback_manager,
    personalization_privacy,
    PreferenceCategory,
    PreferenceCreate,
    PreferenceUpdate,
    EntityType,
    RelationType,
    GraphEntity,
    ContextResolutionSource,
)

client = TestClient(app)

# ==================== 1. PREFERENCE ENGINE & PRECEDENCE ====================

def test_preference_crud():
    """Verify creating, getting, updating, and deleting preferences."""
    pref = preference_engine.set_preference(PreferenceCreate(
        category=PreferenceCategory.RESPONSE_LENGTH,
        key="response_length",
        value="concise",
        is_explicit=True,
        source="user_directive"
    ))
    assert pref.id is not None
    assert pref.value == "concise"
    assert pref.is_explicit is True

    # Get
    fetched = preference_engine.get_preference("response_length")
    assert fetched is not None
    assert fetched.value == "concise"

    # Update
    updated = preference_engine.update_preference(pref.id, PreferenceUpdate(value="ultra_concise"))
    assert updated.value == "ultra_concise"

    # Delete
    deleted = preference_engine.delete_preference(pref.id)
    assert deleted is True
    assert preference_engine.get_preference("response_length") is None

def test_explicit_preference_precedence():
    """Verify that explicit preferences take priority over inferred preferences."""
    # 1. Set explicit preference
    explicit = preference_engine.set_preference(PreferenceCreate(
        category=PreferenceCategory.PROGRAMMING_LANGUAGE,
        key="preferred_programming_language",
        value="Python",
        is_explicit=True,
        source="user_directive"
    ))
    assert explicit.value == "Python"
    assert explicit.is_explicit is True

    # 2. Inferred preference attempt should NOT overwrite explicit preference
    attempt = preference_engine.set_preference(PreferenceCreate(
        category=PreferenceCategory.PROGRAMMING_LANGUAGE,
        key="preferred_programming_language",
        value="JavaScript",
        is_explicit=False,
        source="inferred"
    ))
    assert attempt.value == "Python" # Retains explicit value!

    # 3. New explicit preference CAN overwrite previous explicit preference
    overwritten = preference_engine.set_preference(PreferenceCreate(
        category=PreferenceCategory.PROGRAMMING_LANGUAGE,
        key="preferred_programming_language",
        value="TypeScript",
        is_explicit=True,
        source="user_directive"
    ))
    assert overwritten.value == "TypeScript"

    preference_engine.delete_preference(explicit.id)

def test_preference_directive_detection():
    """Verify natural-language preference detection in user statements."""
    detected = preference_engine.detect_preference_in_directive("Hey NOVA, keep your technical explanations concise")
    assert detected is not None
    assert detected.category == PreferenceCategory.RESPONSE_LENGTH
    assert detected.value == "concise"

    detected2 = preference_engine.detect_preference_in_directive("Remember that I prefer detailed explanations")
    assert detected2 is not None
    assert detected2.category == PreferenceCategory.EXPLANATION_DEPTH
    assert detected2.value == "detailed"

    detected3 = preference_engine.detect_preference_in_directive("Prefer Python examples for any scripts")
    assert detected3 is not None
    assert detected3.value == "Python"

# ==================== 2. CONTEXT RESOLUTION & AMBIGUITY ====================

def test_context_resolution_priority():
    """Verify context resolution priority: explicit query > explicit selection > saved memory."""
    # Priority 1: Explicit instruction in query takes highest precedence
    ctx1 = context_resolver.resolve_context(
        user_query="How do I configure routing in project HireLens?",
        explicit_project_id="nova" # Conflicting UI selection
    )
    assert ctx1.active_project_id == "hirelens"
    assert ctx1.resolution_source == ContextResolutionSource.EXPLICIT_INSTRUCTION

    # Priority 2: Explicit selection from parameter
    ctx2 = context_resolver.resolve_context(
        user_query="Show me the current test coverage",
        explicit_project_id="nova"
    )
    assert ctx2.active_project_id == "nova"
    assert ctx2.resolution_source == ContextResolutionSource.EXPLICIT_SELECTION

def test_context_ambiguity_clarification():
    """Verify that queries referencing multiple conflicting projects prompt for clarification."""
    ctx = context_resolver.resolve_context(
        user_query="Compare the architecture in project Nova and in project HireLens"
    )
    assert ctx.clarification_needed is True
    assert ctx.clarification_prompt is not None
    assert "hirelens" in ctx.clarification_prompt.lower()
    assert "nova" in ctx.clarification_prompt.lower()
    assert ctx.resolution_source == ContextResolutionSource.AMBIGUOUS

# ==================== 3. KNOWLEDGE GRAPH ====================

def test_knowledge_graph_entities_and_relations():
    """Verify adding entities, establishing relationships, and querying subgraphs."""
    # Add entities
    p = knowledge_graph.add_entity(GraphEntity(
        id="project:test_proj",
        entity_type=EntityType.PROJECT,
        name="Test Project",
        description="Knowledge graph test project",
        project_id="test_proj"
    ))
    t = knowledge_graph.add_entity(GraphEntity(
        id="tech:fastapi",
        entity_type=EntityType.TECHNOLOGY,
        name="FastAPI"
    ))
    assert p.id == "project:test_proj"
    assert t.id == "tech:fastapi"

    # Add relation
    rel = knowledge_graph.add_relation(
        source_id="project:test_proj",
        relation_type=RelationType.USES,
        target_id="tech:fastapi",
        confidence=1.0,
        source="test_verification"
    )
    assert rel.id > 0
    assert rel.relation_type == RelationType.USES

    # Duplicate entity prevention / upsert
    p2 = knowledge_graph.add_entity(GraphEntity(
        id="project:test_proj",
        entity_type=EntityType.PROJECT,
        name="Test Project Renamed",
        project_id="test_proj"
    ))
    entities = knowledge_graph.list_entities(project_id="test_proj")
    assert len(entities) == 1
    assert entities[0].name == "Test Project Renamed"

    # Subgraph query
    subgraph = knowledge_graph.get_entity_subgraph("project:test_proj")
    assert subgraph["entity"] is not None
    assert len(subgraph["outgoing_relations"]) == 1
    assert any(ce.id == "tech:fastapi" for ce in subgraph["connected_entities"])

    # Cleanup
    knowledge_graph.delete_entity("project:test_proj")
    knowledge_graph.delete_entity("tech:fastapi")

# ==================== 4. RECOMMENDATION ENGINE & EVIDENCE ====================

def test_recommendation_generation_and_evidence():
    """Verify that recommendations contain required verifiable evidence and non-autonomous actions."""
    recs = recommendation_engine.generate_recommendations()
    assert isinstance(recs, list)
    if recs:
        rec = recs[0]
        assert rec.id is not None
        assert len(rec.supporting_evidence) > 0 # Must have evidence!
        assert rec.reason != ""
        assert rec.suggested_action != ""

# ==================== 5. FEEDBACK PROCESSING ====================

def test_feedback_loop():
    """Verify recording feedback on recommendations and permanent dismissal suppression."""
    # Create test recommendation
    from app.personalization.personalization_schemas import Recommendation
    test_rec = Recommendation(
        id="rec_test_dismiss",
        title="Test Dismissal Recommendation",
        recommendation_text="Recommendation text",
        supporting_evidence=["Evidence 1"],
        reason="Testing feedback loop",
        suggested_action="Check settings"
    )
    recommendation_engine._save_recommendation(test_rec)

    # Permanent dismissal feedback
    fb = feedback_manager.record_feedback(
        feedback_type="DISMISS_PERMANENT",
        target_type="recommendation",
        target_id="rec_test_dismiss",
        user_correction="Do not show this test recommendation again"
    )
    assert fb.id > 0
    assert fb.feedback_type.value == "DISMISS_PERMANENT"

    dismissed_set = feedback_manager.get_permanently_dismissed_targets()
    assert "rec_test_dismiss" in dismissed_set

    # Ensure recommendation marked dismissed
    r = recommendation_engine.get_recommendation("rec_test_dismiss")
    assert r.dismissed is True

# ==================== 6. PRIVACY & MASTER TOGGLES ====================

def test_privacy_and_master_toggles():
    """Verify master enable/disable, adaptive analysis toggle, and data clearing."""
    personalization_privacy.set_enabled(True)
    assert personalization_privacy.is_enabled() is True

    # Disable
    personalization_privacy.set_enabled(False)
    assert personalization_privacy.is_enabled() is False

    # When disabled, recommendations and prompt formatting are bypassed
    assert recommendation_engine.generate_recommendations() == []
    assert preference_engine.format_prompt_instructions() == ""

    # Re-enable
    personalization_privacy.set_enabled(True)
    assert personalization_privacy.is_enabled() is True

# ==================== 7. VOICE COMMAND INTEGRATION ====================

def test_voice_personalization_commands():
    """Verify voice personalization directives handling."""
    from app.voice.audio_manager import audio_manager

    # 1. Disable / Enable
    handled, resp = audio_manager.handle_voice_personalization_command("Hey NOVA, disable personalization")
    assert handled is True
    assert "disabled" in resp.lower()

    handled, resp = audio_manager.handle_voice_personalization_command("Hey NOVA, enable personalization")
    assert handled is True
    assert "enabled" in resp.lower()

    # 2. Preference setting via voice
    handled, resp = audio_manager.handle_voice_personalization_command("Hey NOVA, remember that I prefer concise answers")
    assert handled is True
    assert "concise" in resp.lower()

    # 3. Show saved preferences
    handled, resp = audio_manager.handle_voice_personalization_command("Hey NOVA, show my saved preferences")
    assert handled is True
    assert "preferences" in resp.lower()

    # 4. Project knowledge inquiry
    handled, resp = audio_manager.handle_voice_personalization_command("Hey NOVA, what do you know about my current project?")
    assert handled is True

    # 5. Recommendation explanation
    handled, resp = audio_manager.handle_voice_personalization_command("Hey NOVA, why are you recommending this?")
    assert handled is True

# ==================== 8. REST API VALIDATION ====================

def test_personalization_rest_api():
    """Verify all REST API endpoints under /api/personalization."""
    # GET /api/personalization/status
    res = client.get("/api/personalization/status")
    assert res.status_code == 200
    st = res.json()
    assert "enabled" in st
    assert "total_preferences" in st

    # POST /api/personalization/preferences
    create_payload = {
        "category": "communication_style",
        "key": "style_mode",
        "value": "professional",
        "is_explicit": True
    }
    create_res = client.post("/api/personalization/preferences", json=create_payload)
    assert create_res.status_code == 200
    pref_id = create_res.json()["id"]

    # GET /api/personalization/preferences
    list_res = client.get("/api/personalization/preferences")
    assert list_res.status_code == 200
    assert any(p["id"] == pref_id for p in list_res.json())

    # PATCH /api/personalization/preferences/{id}
    patch_res = client.patch(f"/api/personalization/preferences/{pref_id}", json={"value": "direct_and_professional"})
    assert patch_res.status_code == 200
    assert patch_res.json()["value"] == "direct_and_professional"

    # GET /api/personalization/context
    ctx_res = client.get("/api/personalization/context?query=check%20tests")
    assert ctx_res.status_code == 200
    assert "resolution_source" in ctx_res.json()

    # GET /api/personalization/recommendations
    rec_res = client.get("/api/personalization/recommendations")
    assert rec_res.status_code == 200

    # GET /api/personalization/knowledge-graph
    kg_res = client.get("/api/personalization/knowledge-graph")
    assert kg_res.status_code == 200
    assert "entities" in kg_res.json()
    assert "relations" in kg_res.json()

    # POST /api/personalization/refresh
    ref_res = client.post("/api/personalization/refresh")
    assert ref_res.status_code == 200

    # POST /api/personalization/disable & enable
    assert client.post("/api/personalization/disable").status_code == 200
    assert client.post("/api/personalization/enable").status_code == 200

    # DELETE /api/personalization/preferences/{id}
    del_res = client.delete(f"/api/personalization/preferences/{pref_id}")
    assert del_res.status_code == 200
