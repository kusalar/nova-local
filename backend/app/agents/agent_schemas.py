from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.tools.tool_schemas import PermissionLevel

# ==========================================
# Agent Roles & Statuses
# ==========================================

class AgentRole(str, Enum):
    ORCHESTRATOR = "ORCHESTRATOR"
    RESEARCH = "RESEARCH"
    DEVELOPER = "DEVELOPER"
    SYSTEM = "SYSTEM"
    VISION = "VISION"
    MEMORY = "MEMORY"

class AgentStatus(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    PAUSED = "PAUSED"
    ERROR = "ERROR"

class WorkflowStatus(str, Enum):
    PLANNING = "PLANNING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class WorkflowStepStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"

class EventType(str, Enum):
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_PLANNED = "WORKFLOW_PLANNED"
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_FAILED = "STEP_FAILED"
    STEP_PAUSED_APPROVAL = "STEP_PAUSED_APPROVAL"
    STEP_APPROVED = "STEP_APPROVED"
    STEP_REJECTED = "STEP_REJECTED"
    REFLECTION_EVALUATION = "REFLECTION_EVALUATION"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"

# ==========================================
# Agent Definitions
# ==========================================

class AgentMetadata(BaseModel):
    id: str
    name: str
    role: AgentRole
    description: str
    capabilities: List[str]
    allowed_tools: List[str]
    status: AgentStatus = AgentStatus.IDLE
    current_workflow_id: Optional[str] = None
    tasks_completed: int = 0

# ==========================================
# Workflow Steps & Dependencies
# ==========================================

class RetryPolicy(BaseModel):
    max_retries: int = 2
    retry_count: int = 0
    retry_delay_seconds: float = 1.0

class WorkflowStep(BaseModel):
    step_id: int
    workflow_id: str
    description: str
    assigned_agent: AgentRole
    tool_id: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[int] = Field(default_factory=list) # step_ids that must complete first
    permission_level: PermissionLevel = PermissionLevel.READ_ONLY
    expected_output: str = ""
    timeout_seconds: int = 45
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    reflection: Optional[str] = None

# ==========================================
# Workflow Plan & Structure
# ==========================================

class WorkflowPlan(BaseModel):
    workflow_id: str
    objective: str
    project_id: Optional[str] = None
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PLANNING
    requires_approval: bool = False
    pending_approval_step_id: Optional[int] = None
    approval_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    total_steps: int = 0
    completed_steps: int = 0
    final_report: Optional[str] = None

# ==========================================
# Reflection & Self-Evaluation
# ==========================================

class ReflectionEvaluation(BaseModel):
    step_id: int
    success: bool
    evidence: str
    goal_satisfied: bool
    requires_clarification: bool = False
    can_proceed: bool = True
    suggested_action: str = "CONTINUE" # CONTINUE, RETRY, PAUSE, ABORT

# ==========================================
# Workflow Report
# ==========================================

class WorkflowReport(BaseModel):
    workflow_id: str
    objective: str
    status: WorkflowStatus
    duration_seconds: float
    total_steps: int
    successful_steps: int
    failed_steps: int
    summary: str
    key_findings: List[str]
    verifiable_evidence: List[str]
    unresolved_issues: List[str]
    project_memory_updated: bool = False
    completed_at: str

# ==========================================
# Events & Telemetry
# ==========================================

class WorkflowEvent(BaseModel):
    event_id: str
    workflow_id: str
    step_id: Optional[int] = None
    event_type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    agent_role: Optional[AgentRole] = None
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)

# ==========================================
# API Payloads
# ==========================================

class PlanWorkflowRequest(BaseModel):
    objective: str = Field(..., min_length=3, description="High-level user objective")
    project_id: Optional[str] = None
    preferred_agents: Optional[List[AgentRole]] = None

class ExecuteWorkflowRequest(BaseModel):
    workflow_id: Optional[str] = None
    plan: Optional[WorkflowPlan] = None
