from typing import List, Dict, Any
from .automation_schemas import (
    AutomationRule, AutonomyLevel, TriggerType, ScheduleType,
    AutomationActionType, AutomationStatus, TriggerConfig, ScheduleConfig, RetryPolicy
)

def get_routine_templates() -> List[Dict[str, Any]]:
    """Returns curated pre-configured templates for common personal automation routines."""
    return [
        {
            "id": "tpl_daily_briefing",
            "name": "Daily Morning Briefing",
            "description": "Every morning at 8:00 AM, compiles a verifiable summary of pending tasks, upcoming deadlines, recent project updates, and system health.",
            "category": "Productivity",
            "autonomy_level": AutonomyLevel.EXECUTE_LOW_RISK.value,
            "action_type": AutomationActionType.DAILY_BRIEFING.value,
            "trigger_config": {
                "trigger_type": TriggerType.SCHEDULE.value,
                "schedule": {
                    "schedule_type": ScheduleType.DAILY.value,
                    "time_of_day": "08:00",
                    "days_of_week": [0, 1, 2, 3, 4, 5, 6],
                    "timezone": "UTC"
                }
            },
            "action_payload": {
                "speak_aloud": False,
                "include_system_health": True,
                "include_recent_workflows": True
            }
        },
        {
            "id": "tpl_evening_tasks",
            "name": "Evening Task Reminder",
            "description": "Every evening at 6:00 PM, checks unfinished memory tasks and reminders and alerts you with a status digest.",
            "category": "Reminders",
            "autonomy_level": AutonomyLevel.EXECUTE_LOW_RISK.value,
            "action_type": AutomationActionType.REMINDER.value,
            "trigger_config": {
                "trigger_type": TriggerType.SCHEDULE.value,
                "schedule": {
                    "schedule_type": ScheduleType.DAILY.value,
                    "time_of_day": "18:00",
                    "days_of_week": [0, 1, 2, 3, 4, 5, 6],
                    "timezone": "UTC"
                }
            },
            "action_payload": {
                "reminder_filter": "pending",
                "speak_aloud": False
            }
        },
        {
            "id": "tpl_project_health",
            "name": "Weekly Project Health Check",
            "description": "Every Saturday at 10:00 AM, inspects your registered project workspace, checks git status, verifies config, and executes approved test suites safely.",
            "category": "Development",
            "autonomy_level": AutonomyLevel.EXECUTE_LOW_RISK.value,
            "action_type": AutomationActionType.PROJECT_HEALTH.value,
            "trigger_config": {
                "trigger_type": TriggerType.SCHEDULE.value,
                "schedule": {
                    "schedule_type": ScheduleType.WEEKLY.value,
                    "time_of_day": "10:00",
                    "days_of_week": [5], # Saturday
                    "timezone": "UTC"
                },
                "project_id": "nova"
            },
            "action_payload": {
                "workspace_path": "D:\\Nova",
                "run_tests": True,
                "test_command": "pytest backend/tests/test_health.py -q"
            }
        },
        {
            "id": "tpl_system_resource_guard",
            "name": "System Resource Threshold Alert",
            "description": "Monitors CPU and RAM thresholds event-driven and alerts when host system memory utilization exceeds 85%.",
            "category": "System",
            "autonomy_level": AutonomyLevel.OBSERVE.value,
            "action_type": AutomationActionType.NOTIFICATION.value,
            "trigger_config": {
                "trigger_type": TriggerType.SYSTEM_THRESHOLD.value,
                "system_metric": "memory_percent",
                "metric_threshold": 85.0,
                "metric_operator": ">"
            },
            "action_payload": {
                "title": "High Memory Utilization Detected",
                "message": "System RAM utilization has exceeded 85%. Review running desktop processes."
            }
        },
        {
            "id": "tpl_overdue_task_guard",
            "name": "Overdue Task & Deadline Guard",
            "description": "Monitors active memory tasks and deadlines, triggering priority reminders whenever a task passes its scheduled due date.",
            "category": "Reminders",
            "autonomy_level": AutonomyLevel.EXECUTE_LOW_RISK.value,
            "action_type": AutomationActionType.REMINDER.value,
            "trigger_config": {
                "trigger_type": TriggerType.TASK_OVERDUE.value
            },
            "action_payload": {
                "speak_aloud": False
            }
        }
    ]
