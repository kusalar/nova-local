from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class MemoryCategory(str, Enum):
    USER_PROFILE = "user_profile"
    PROJECT_MEMORY = "project_memory"
    CONVERSATION_MEMORY = "conversation_memory"
    TASK_MEMORY = "task_memory"
    KNOWLEDGE_MEMORY = "knowledge_memory"

class MemoryCreate(BaseModel):
    category: MemoryCategory = Field(default=MemoryCategory.KNOWLEDGE_MEMORY)
    content: str = Field(..., min_length=1, description="Fact or knowledge to remember")
    project_id: Optional[str] = Field(default=None, description="Optional associated project identifier")
    tags: Optional[List[str]] = Field(default_factory=list)
    importance: float = Field(default=1.0, ge=0.0, le=5.0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MemoryUpdate(BaseModel):
    category: Optional[MemoryCategory] = None
    content: Optional[str] = None
    project_id: Optional[str] = None
    tags: Optional[List[str]] = None
    importance: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class MemoryItem(BaseModel):
    id: int
    category: MemoryCategory
    content: str
    project_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    importance: float = 1.0
    similarity: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str

class ProjectCreate(BaseModel):
    id: str = Field(..., min_length=1, description="Unique slug or identifier, e.g. 'nova', 'hirelens'")
    name: str = Field(..., min_length=1)
    description: Optional[str] = ""
    tech_stack: Optional[List[str]] = Field(default_factory=list)
    status: Optional[str] = "active"
    decisions: Optional[List[str]] = Field(default_factory=list)
    known_issues: Optional[List[str]] = Field(default_factory=list)
    pending_tasks: Optional[List[str]] = Field(default_factory=list)
    recent_updates: Optional[List[str]] = Field(default_factory=list)

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    status: Optional[str] = None
    decisions: Optional[List[str]] = None
    known_issues: Optional[List[str]] = None
    pending_tasks: Optional[List[str]] = None
    recent_updates: Optional[List[str]] = None

class ProjectItem(BaseModel):
    id: str
    name: str
    description: str = ""
    tech_stack: List[str] = Field(default_factory=list)
    status: str = "active"
    decisions: List[str] = Field(default_factory=list)
    known_issues: List[str] = Field(default_factory=list)
    pending_tasks: List[str] = Field(default_factory=list)
    recent_updates: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str

class ConversationSummaryItem(BaseModel):
    id: int
    session_id: str
    summary: str
    key_points: List[str] = Field(default_factory=list)
    turn_count: int = 0
    created_at: str

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = ""
    project_id: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    deadline: Optional[str] = None

class TaskItem(BaseModel):
    id: int
    title: str
    description: str = ""
    project_id: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    deadline: Optional[str] = None
    created_at: str

class MemorySearchQuery(BaseModel):
    query: str
    category: Optional[MemoryCategory] = None
    project_id: Optional[str] = None
    limit: int = 5
    threshold: float = 0.45

class MemoryExtractRequest(BaseModel):
    text: str = Field(..., min_length=1)
    session_id: Optional[str] = "default"
    project_id: Optional[str] = None

class MemoryForgetRequest(BaseModel):
    target: str = Field(..., min_length=1, description="Keyword, phrase, or memory ID to purge")
    category: Optional[MemoryCategory] = None
    project_id: Optional[str] = None
