import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .automation_schemas import (
    AutomationRule, AutomationCreate, AutomationUpdate,
    AutomationHistoryRecord, NotificationItem, ReminderItem, ReminderCreate,
    AutomationStatus, AutomationStatusResponse
)
from .automation_logger import automation_logger
from .automation_registry import automation_registry
from .automation_scheduler import automation_scheduler
from .automation_executor import automation_executor
from .automation_permissions import automation_permissions
from .trigger_engine import trigger_engine
from .notification_manager import notification_manager
from .routine_templates import get_routine_templates

logger = logging.getLogger("nova.automation.manager")

class AutomationManager:
    """
    Central facade for NOVA v0.7 Proactive Intelligence & Personal Automation.
    Coordinates registry, scheduler, trigger engine, executor, notifications, and permissions.
    """

    def __init__(self):
        self.logger = automation_logger
        self.registry = automation_registry
        self.scheduler = automation_scheduler
        self.executor = automation_executor
        self.permissions = automation_permissions
        self.triggers = trigger_engine
        self.notifications = notification_manager

    def initialize(self):
        """Initializes scheduler, checks restart recovery, and starts background heartbeat."""
        rules = self.registry.list_automations()
        self.scheduler.handle_restart_recovery(rules)
        self.scheduler.start()
        logger.info("AutomationManager initialized successfully.")

    def shutdown(self):
        """Gracefully halts scheduler and active executions."""
        self.scheduler.stop()
        logger.info("AutomationManager stopped.")

    # ==================== AUTOMATION CRUD ====================

    def create_automation(self, data: AutomationCreate) -> AutomationRule:
        rule = self.registry.create_automation(data)
        # Compute initial next_run_at if scheduled
        next_run = self.scheduler.compute_next_run(rule)
        if next_run:
            rule.next_run_at = next_run
            self.logger.save_automation(rule)
        return rule

    def update_automation(self, automation_id: str, updates: AutomationUpdate) -> Optional[AutomationRule]:
        rule = self.registry.update_automation(automation_id, updates)
        if rule and updates.trigger_config:
            next_run = self.scheduler.compute_next_run(rule)
            rule.next_run_at = next_run
            self.logger.save_automation(rule)
        return rule

    def delete_automation(self, automation_id: str) -> bool:
        return self.registry.delete_automation(automation_id)

    def get_automation(self, automation_id: str) -> Optional[AutomationRule]:
        return self.registry.get_automation(automation_id)

    def list_automations(self) -> List[AutomationRule]:
        return self.registry.list_automations()

    def enable_automation(self, automation_id: str) -> Optional[AutomationRule]:
        rule = self.registry.set_enabled(automation_id, True)
        if rule:
            rule.next_run_at = self.scheduler.compute_next_run(rule)
            self.logger.save_automation(rule)
        return rule

    def disable_automation(self, automation_id: str) -> Optional[AutomationRule]:
        return self.registry.set_enabled(automation_id, False)

    async def run_automation_now(self, automation_id: str) -> Dict[str, Any]:
        """Manually triggers immediate execution of an automation rule."""
        rule = self.get_automation(automation_id)
        if not rule:
            raise ValueError(f"Automation '{automation_id}' not found.")
        return await self.executor.execute_rule(rule)

    def get_history(self, automation_id: Optional[str] = None, limit: int = 50) -> List[AutomationHistoryRecord]:
        return self.logger.get_history(automation_id=automation_id, limit=limit)

    # ==================== GLOBAL CONTROLS ====================

    def pause_all(self):
        self.permissions.pause_all()
        self.notifications.send_notification(
            notif_type=self.notifications.preferences and "AUTOMATION_PAUSED",
            title="Automations Paused",
            message="Global automation pause activated. All scheduled and event routines are paused."
        )

    def resume_all(self):
        self.permissions.resume_all()

    def get_status(self) -> AutomationStatusResponse:
        rules = self.list_automations()
        active = sum(1 for r in rules if r.enabled and r.status == AutomationStatus.ACTIVE)
        paused = sum(1 for r in rules if r.status == AutomationStatus.PAUSED)
        disabled = sum(1 for r in rules if not r.enabled or r.status == AutomationStatus.DISABLED)

        # Find earliest upcoming next_run_at
        upcoming = [r.next_run_at for r in rules if r.enabled and r.next_run_at]
        next_scheduled = min(upcoming) if upcoming else None

        unread_notifs = len(self.notifications.list_notifications(unread_only=True))
        pending_reminders = len(self.logger.list_reminders(pending_only=True))

        return AutomationStatusResponse(
            is_paused=self.permissions.is_globally_paused(),
            active_count=active,
            paused_count=paused,
            disabled_count=disabled,
            total_count=len(rules),
            running_workflows_count=len(self.executor._active_runs),
            unread_notifications_count=unread_notifs,
            pending_reminders_count=pending_reminders,
            next_scheduled_run=next_scheduled
        )

    # ==================== NOTIFICATIONS & REMINDERS ====================

    def list_notifications(self, unread_only: bool = False, limit: int = 50) -> List[NotificationItem]:
        return self.notifications.list_notifications(unread_only=unread_only, limit=limit)

    def mark_notification_read(self, notification_id: int) -> bool:
        return self.notifications.mark_read(notification_id)

    def dismiss_notification(self, notification_id: int) -> bool:
        return self.notifications.dismiss(notification_id)

    def snooze_notification(self, notification_id: int, minutes: Optional[int] = None) -> bool:
        return self.notifications.snooze(notification_id, minutes)

    def list_reminders(self, pending_only: bool = True) -> List[ReminderItem]:
        return self.logger.list_reminders(pending_only=pending_only)

    def add_reminder(self, data: ReminderCreate) -> ReminderItem:
        item = self.logger.add_reminder(
            text=data.text,
            due_at=data.due_at,
            recurring_cron=data.recurring_cron,
            project_id=data.project_id
        )
        return item

    def complete_reminder(self, reminder_id: int) -> bool:
        return self.logger.mark_reminder_completed(reminder_id)

    def snooze_reminder(self, reminder_id: int, until_iso: str) -> bool:
        return self.logger.snooze_reminder(reminder_id, until_iso)

    def delete_reminder(self, reminder_id: int) -> bool:
        return self.logger.delete_reminder(reminder_id)

    def get_templates(self) -> List[Dict[str, Any]]:
        return get_routine_templates()

# Global singleton
automation_manager = AutomationManager()
