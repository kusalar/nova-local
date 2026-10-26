from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

class PermissionLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    BLOCKED = "BLOCKED"

class ToolCategory(str, Enum):
    APPLICATION = "APPLICATION"
    FILE_SYSTEM = "FILE_SYSTEM"
    SYSTEM_CONTROL = "SYSTEM_CONTROL"
    BROWSER = "BROWSER"

class TaskStatus(str, Enum):
    PLANNING = "PLANNING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"

class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum_values: Optional[List[str]] = None

class ToolDefinition(BaseModel):
    id: str
    name: str
    description: str
    category: ToolCategory
    permission_level: PermissionLevel
    timeout_seconds: int = 30
    parameters: List[ToolParameter] = []
    is_reversible: bool = False

class TaskStep(BaseModel):
    step_id: int
    tool_id: str
    description: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    permission_level: PermissionLevel = PermissionLevel.READ_ONLY
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class TaskPlan(BaseModel):
    task_id: str
    prompt: str
    description: str
    steps: List[TaskStep] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PLANNING
    requires_confirmation: bool = False
    confirmation_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    total_steps: int = 0
    current_step: int = 0
    rollback_eligible: bool = False

class TaskPlanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language request or operational directive")
    project_id: Optional[str] = None
    auto_execute: bool = False

class TaskExecuteRequest(BaseModel):
    task_id: Optional[str] = None
    plan: Optional[TaskPlan] = None

class ExecutionRecord(BaseModel):
    execution_id: str
    task_id: Optional[str] = None
    step_id: Optional[int] = None
    tool_id: str
    tool_name: str
    category: str
    permission_level: str
    arguments: Dict[str, Any]
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    is_reversible: bool = False
    is_rolled_back: bool = False
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None

class RollbackRequest(BaseModel):
    execution_id: str

class DryRunResult(BaseModel):
    operation: str
    target: str
    details: Dict[str, Any] = Field(default_factory=dict)
    affects_count: int = 1
    is_reversible: bool = True
