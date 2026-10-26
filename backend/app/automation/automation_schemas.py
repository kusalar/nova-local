from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class AutonomyLevel(str, Enum):
    OBSERVE = "OBSERVE"
    PREPARE = "PREPARE"
    EXECUTE_LOW_RISK = "EXECUTE_LOW_RISK"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    BLOCKED = "BLOCKED"

class TriggerType(str, Enum):
    SCHEDULE = "SCHEDULE"
    APP_EVENT = "APP_EVENT"
    PROJECT_HEALTH = "PROJECT_HEALTH"
    SYSTEM_THRESHOLD = "SYSTEM_THRESHOLD"
    WORKFLOW_EVENT = "WORKFLOW_EVENT"
    TASK_OVERDUE = "TASK_OVERDUE"
    MANUAL = "MANUAL"

class ScheduleType(str, Enum):
    ONCE = "ONCE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    RECURRING = "RECURRING"
    CRON = "CRON"

class AutomationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"

class AutomationActionType(str, Enum):
    WORKFLOW = "WORKFLOW"
    DAILY_BRIEFING = "DAILY_BRIEFING"
    PROJECT_HEALTH = "PROJECT_HEALTH"
    REMINDER = "REMINDER"
    NOTIFICATION = "NOTIFICATION"

class NotificationType(str, Enum):
    REMINDER = "REMINDER"
    DAILY_BRIEFING = "DAILY_BRIEFING"
    PROJECT_HEALTH_REPORT = "PROJECT_HEALTH_REPORT"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    AUTOMATION_PAUSED = "AUTOMATION_PAUSED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"

class RetryPolicy(BaseModel):
    max_retries: int = Field(default=2, ge=0, le=5)
    retry_delay_seconds: int = Field(default=60, ge=5, le=3600)
    stop_on_critical: bool = True

class ScheduleConfig(BaseModel):
    schedule_type: ScheduleType = ScheduleType.DAILY
    time_of_day: Optional[str] = "08:00"  # HH:MM format
    days_of_week: Optional[List[int]] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6]) # 0=Monday, 6=Sunday
    interval_seconds: Optional[int] = None
    specific_datetime: Optional[str] = None # ISO format
    cron_expression: Optional[str] = None
    timezone: str = "UTC"

class TriggerConfig(BaseModel):
    trigger_type: TriggerType = TriggerType.SCHEDULE
    schedule: Optional[ScheduleConfig] = None
    app_name: Optional[str] = None # For APP_EVENT (e.g., "code.exe", "slack.exe")
    app_action: Optional[str] = "launched" # "launched" or "closed"
    system_metric: Optional[str] = None # "cpu_percent", "memory_percent"
    metric_threshold: Optional[float] = None # e.g. 90.0
    metric_operator: Optional[str] = ">" # ">", "<", ">="
    workflow_id_pattern: Optional[str] = None
    workflow_outcome: Optional[str] = None # "COMPLETED", "FAILED"
    project_id: Optional[str] = None
    task_filter: Optional[str] = None

class AutomationRule(BaseModel):
    id: str
    name: str
    description: str = ""
    enabled: bool = True
    status: AutomationStatus = AutomationStatus.ACTIVE
    autonomy_level: AutonomyLevel = AutonomyLevel.EXECUTE_LOW_RISK
    trigger_config: TriggerConfig
    action_type: AutomationActionType = AutomationActionType.WORKFLOW
    workflow_objective: Optional[str] = None
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    run_count: int = 0
    failure_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class AutomationCreate(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = ""
    enabled: bool = True
    autonomy_level: AutonomyLevel = AutonomyLevel.EXECUTE_LOW_RISK
    trigger_config: TriggerConfig
    action_type: AutomationActionType = AutomationActionType.WORKFLOW
    workflow_objective: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = Field(default_factory=dict)
    retry_policy: Optional[RetryPolicy] = Field(default_factory=RetryPolicy)

class AutomationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    status: Optional[AutomationStatus] = None
    autonomy_level: Optional[AutonomyLevel] = None
    trigger_config: Optional[TriggerConfig] = None
    action_type: Optional[AutomationActionType] = None
    workflow_objective: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    retry_policy: Optional[RetryPolicy] = None

class AutomationHistoryRecord(BaseModel):
    id: int
    automation_id: str
    trigger_type: str
    action_type: str
    status: str # "SUCCESS", "FAILED", "RUNNING", "SKIPPED", "REQUIRES_APPROVAL"
    started_at: str
    completed_at: Optional[str] = None
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    workflow_id: Optional[str] = None

class NotificationItem(BaseModel):
    id: int
    type: NotificationType
    title: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    read: bool = False
    dismissed: bool = False
    snoozed_until: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class NotificationCreate(BaseModel):
    type: NotificationType
    title: str
    message: str
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    speak_aloud: bool = False

class ReminderItem(BaseModel):
    id: int
    text: str
    due_at: Optional[str] = None
    completed: bool = False
    snoozed_until: Optional[str] = None
    recurring_cron: Optional[str] = None
    project_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ReminderCreate(BaseModel):
    text: str = Field(..., min_length=2)
    due_at: Optional[str] = None
    recurring_cron: Optional[str] = None
    project_id: Optional[str] = None

class AutomationStatusResponse(BaseModel):
    is_paused: bool
    active_count: int
    paused_count: int
    disabled_count: int
    total_count: int
    running_workflows_count: int
    unread_notifications_count: int
    pending_reminders_count: int
    next_scheduled_run: Optional[str] = None
