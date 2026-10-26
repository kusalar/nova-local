from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class PreferenceCategory(str, Enum):
    RESPONSE_LENGTH = "response_length"
    EXPLANATION_DEPTH = "explanation_depth"
    PROGRAMMING_LANGUAGE = "programming_language"
    DEVELOPMENT_TOOL = "development_tool"
    COMMUNICATION_STYLE = "communication_style"
    NOTIFICATION = "notification"
    VOICE_BEHAVIOR = "voice_behavior"
    AUTOMATION_SCHEDULE = "automation_schedule"
    GENERAL = "general"

class EntityType(str, Enum):
    PROJECT = "PROJECT"
    TECHNOLOGY = "TECHNOLOGY"
    TASK = "TASK"
    DECISION = "DECISION"
    DOCUMENT = "DOCUMENT"
    WORKFLOW = "WORKFLOW"
    PREFERENCE = "PREFERENCE"
    KNOWLEDGE_ITEM = "KNOWLEDGE_ITEM"

class RelationType(str, Enum):
    USES = "USES"
    HAS_TASK = "HAS_TASK"
    HAS_DECISION = "HAS_DECISION"
    BELONGS_TO = "BELONGS_TO"
    REFERENCES = "REFERENCES"
    APPLIES_TO = "APPLIES_TO"
    RELATES_TO = "RELATES_TO"

class FeedbackType(str, Enum):
    USEFUL = "USEFUL"
    DISMISS_PERMANENT = "DISMISS_PERMANENT"
    PREFERENCE_CORRECTION = "PREFERENCE_CORRECTION"
    ASSOCIATION_INCORRECT = "ASSOCIATION_INCORRECT"
    FORGET_PREFERENCE = "FORGET_PREFERENCE"

class ContextResolutionSource(str, Enum):
    EXPLICIT_INSTRUCTION = "EXPLICIT_INSTRUCTION"
    EXPLICIT_SELECTION = "EXPLICIT_SELECTION"
    ACTIVE_WORKFLOW = "ACTIVE_WORKFLOW"
    SAVED_MEMORY = "SAVED_MEMORY"
    HISTORICAL = "HISTORICAL"
    AMBIGUOUS = "AMBIGUOUS"

# ==================== PREFERENCES ====================

class UserPreference(BaseModel):
    id: str
    category: PreferenceCategory
    key: str
    value: str
    is_explicit: bool = True
    source: str = "user_directive" # "user_directive", "settings_ui", "voice_command", "inferred"
    confidence: float = 1.0
    context_scope: Optional[str] = None # None = global, or project_id
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class PreferenceCreate(BaseModel):
    category: PreferenceCategory
    key: str = Field(..., min_length=2, max_length=60)
    value: str = Field(..., min_length=1, max_length=250)
    is_explicit: bool = True
    context_scope: Optional[str] = None
    source: Optional[str] = "user_directive"

class PreferenceUpdate(BaseModel):
    category: Optional[PreferenceCategory] = None
    value: Optional[str] = None
    is_explicit: Optional[bool] = None
    context_scope: Optional[str] = None
    confidence: Optional[float] = None

# ==================== KNOWLEDGE GRAPH ====================

class GraphEntity(BaseModel):
    id: str
    entity_type: EntityType
    name: str
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class GraphRelation(BaseModel):
    id: int
    source_id: str
    relation_type: RelationType
    target_id: str
    confidence: float = 1.0
    source: str = "project_memory"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class GraphRelationCreate(BaseModel):
    source_id: str
    relation_type: RelationType
    target_id: str
    confidence: float = 1.0
    source: Optional[str] = "user_directive"

class KnowledgeGraphView(BaseModel):
    entities: List[GraphEntity] = Field(default_factory=list)
    relations: List[GraphRelation] = Field(default_factory=list)
    total_entities: int = 0
    total_relations: int = 0

# ==================== RECOMMENDATIONS ====================

class Recommendation(BaseModel):
    id: str
    title: str
    recommendation_text: str
    supporting_evidence: List[str] = Field(default_factory=list)
    related_project: Optional[str] = None
    related_task: Optional[str] = None
    confidence: float = 1.0
    reason: str
    suggested_action: str
    dismissed: bool = False
    feedback_status: Optional[str] = None # "USEFUL", "DISMISSED", "INCORRECT"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ==================== FEEDBACK ====================

class FeedbackRecord(BaseModel):
    id: int
    feedback_type: FeedbackType
    target_type: str # "recommendation", "preference", "relation"
    target_id: str
    user_correction: Optional[str] = None
    updated_state: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class FeedbackSubmit(BaseModel):
    feedback_type: FeedbackType
    user_correction: Optional[str] = None

# ==================== CONTEXT RESOLUTION ====================

class ResolvedContext(BaseModel):
    active_project_id: Optional[str] = None
    project_name: Optional[str] = None
    confidence: float = 1.0
    resolution_source: ContextResolutionSource = ContextResolutionSource.HISTORICAL
    relevant_memories: List[str] = Field(default_factory=list)
    relevant_tasks: List[str] = Field(default_factory=list)
    recent_workflows: List[str] = Field(default_factory=list)
    active_window_title: Optional[str] = None
    applied_preferences: List[str] = Field(default_factory=list)
    clarification_needed: bool = False
    clarification_prompt: Optional[str] = None
    formatted_instructions: str = ""

# ==================== STATUS & PRIVACY ====================

class PersonalizationStatus(BaseModel):
    enabled: bool = True
    adaptive_analysis_enabled: bool = True
    recommendations_enabled: bool = True
    total_preferences: int = 0
    explicit_preferences_count: int = 0
    inferred_preferences_count: int = 0
    active_recommendations_count: int = 0
    graph_entities_count: int = 0
    graph_relations_count: int = 0
    last_refreshed_at: Optional[str] = None

class PrivacySettings(BaseModel):
    local_only: bool = True
    no_cloud_sync: bool = True
    no_keystroke_monitoring: bool = True
    no_clipboard_monitoring: bool = True
    no_hidden_screen_storage: bool = True
    adaptive_analysis_enabled: bool = True
    recommendations_enabled: bool = True
