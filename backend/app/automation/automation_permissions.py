import logging
import time
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from .automation_schemas import AutonomyLevel, AutomationActionType, AutomationRule

logger = logging.getLogger("nova.automation.permissions")

class AutomationPermissionError(Exception):
    """Raised when an automation rule attempts an operation beyond its allowed autonomy boundary."""
    pass

class AutomationPermissionManager:
    """
    Enforces autonomy levels, permission boundaries, approval freshness,
    and global pause/resume controls for NOVA v0.7.
    """

    # Numeric hierarchy for autonomy: higher index = more permissive
    LEVEL_HIERARCHY = {
        AutonomyLevel.BLOCKED: 0,
        AutonomyLevel.OBSERVE: 1,
        AutonomyLevel.PREPARE: 2,
        AutonomyLevel.EXECUTE_LOW_RISK: 3,
        AutonomyLevel.REQUIRES_APPROVAL: 4
    }

    # Actions allowed under each level
    ALLOWED_ACTIONS_BY_LEVEL = {
        AutonomyLevel.OBSERVE: {
            "read_memory", "get_telemetry", "generate_report", "read_file",
            "list_files", "system_status", "ocr_read", "inspect_project"
        },
        AutonomyLevel.PREPARE: {
            "read_memory", "get_telemetry", "generate_report", "read_file",
            "list_files", "system_status", "ocr_read", "inspect_project",
            "plan_workflow", "summarize_tasks", "recommend_actions"
        },
        AutonomyLevel.EXECUTE_LOW_RISK: {
            "read_memory", "get_telemetry", "generate_report", "read_file",
            "list_files", "system_status", "ocr_read", "inspect_project",
            "plan_workflow", "summarize_tasks", "recommend_actions",
            "open_application", "deliver_notification", "speak_tts",
            "run_approved_test", "mark_reminder_completed"
        },
        AutonomyLevel.REQUIRES_APPROVAL: {
            "modify_file", "move_file", "rename_file", "delete_file",
            "confirmation_required_operation", "change_settings"
        }
    }

    # Always strictly blocked under any circumstance
    STRICTLY_BLOCKED = {
        "arbitrary_shell", "arbitrary_code", "cmd.exe", "powershell.exe",
        "credential_access", "privilege_escalation", "disable_security",
        "drop_database", "unrestricted_deletion", "regedit", "format"
    }

    def __init__(self):
        self._globally_paused: bool = False
        self._approval_store: Dict[str, Dict[str, Any]] = {}
        self.approval_timeout_seconds: float = 300.0 # 5 minutes

    def is_globally_paused(self) -> bool:
        return self._globally_paused

    def pause_all(self):
        self._globally_paused = True
        logger.info("Global automation pause activated. All automations halted.")

    def resume_all(self):
        self._globally_paused = False
        logger.info("Global automation resumed. Automations will execute per schedule and triggers.")

    def can_rule_execute(self, rule: AutomationRule) -> Tuple[bool, str]:
        """Validates if rule can run based on global state and autonomy level."""
        if self._globally_paused:
            return False, "Global automation is currently paused."

        if not rule.enabled:
            return False, f"Automation '{rule.id}' is disabled."

        if rule.autonomy_level == AutonomyLevel.BLOCKED:
            return False, f"Automation '{rule.id}' autonomy level is BLOCKED."

        return True, "Execution permitted."

    def validate_action_permission(
        self,
        rule_level: AutonomyLevel,
        action_name: str,
        requires_user_approval: bool = False
    ) -> Tuple[bool, str]:
        """
        Validates whether a specific action is within the rule's autonomy level.
        Prevents self-escalation and strictly blocks disallowed behaviors.
        """
        action_lower = action_name.lower()

        # 1. Check strictly blocked actions
        if any(b in action_lower for b in self.STRICTLY_BLOCKED):
            return False, f"Action '{action_name}' is STRICTLY BLOCKED by NOVA safety policy."

        # 2. Check if rule is BLOCKED
        if rule_level == AutonomyLevel.BLOCKED:
            return False, "Automation level is BLOCKED."

        # 3. If action requires approval, the rule must be at least REQUIRES_APPROVAL
        if requires_user_approval and rule_level != AutonomyLevel.REQUIRES_APPROVAL:
            return False, f"Action '{action_name}' requires explicit user approval, but rule level is {rule_level.value}."

        return True, "Action allowed."

    # ==================== FRESH APPROVAL TRACKING ====================

    def register_pending_approval(
        self,
        approval_id: str,
        automation_id: str,
        action_name: str,
        action_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Associates an approval with an exact pending action and expiry."""
        record = {
            "approval_id": approval_id,
            "automation_id": automation_id,
            "action_name": action_name,
            "action_payload": action_payload,
            "created_at": time.time(),
            "expires_at": time.time() + self.approval_timeout_seconds,
            "used": False
        }
        self._approval_store[approval_id] = record
        return record

    def consume_approval(self, approval_id: str, automation_id: str, action_name: str) -> Tuple[bool, str]:
        """
        Validates and consumes an approval token.
        Rejects stale, expired, mismatched, or reused approvals.
        """
        if approval_id not in self._approval_store:
            return False, "Approval token not found."

        record = self._approval_store[approval_id]

        if record["used"]:
            return False, "Approval token has already been used (duplicate execution prevented)."

        if time.time() > record["expires_at"]:
            del self._approval_store[approval_id]
            return False, "Approval has expired. Fresh user confirmation required."

        if record["automation_id"] != automation_id:
            return False, "Approval token does not match the target automation ID."

        if record["action_name"] != action_name:
            return False, "Approval token action mismatch."

        # Mark as consumed so scheduled automations cannot reuse approvals
        record["used"] = True
        return True, "Approval valid and consumed."

# Global singleton
automation_permissions = AutomationPermissionManager()
