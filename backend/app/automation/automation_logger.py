import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings
from .automation_schemas import (
    AutomationRule, AutomationCreate, AutomationUpdate,
    AutomationHistoryRecord, NotificationItem, ReminderItem,
    AutonomyLevel, TriggerType, AutomationStatus, AutomationActionType,
    NotificationType, TriggerConfig, RetryPolicy
)

logger = logging.getLogger("nova.automation.logger")

class AutomationLogger:
    """
    Persistent SQLite storage and audit system for NOVA v0.7:
    - Automations rules and configurations
    - Execution history records
    - Notifications and preferences
    - Reminders with snooze and completion states
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._migrate()

    def _get_connection(self) -> sqlite3.Connection:
        from app.database import get_db_connection
        return get_db_connection(self.db_path)

    def _migrate(self):
        """Creates v0.7 automation tables non-destructively."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Automations Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS automations (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        enabled INTEGER DEFAULT 1,
                        status TEXT DEFAULT 'ACTIVE',
                        autonomy_level TEXT DEFAULT 'EXECUTE_LOW_RISK',
                        trigger_config TEXT NOT NULL,
                        action_type TEXT DEFAULT 'WORKFLOW',
                        workflow_objective TEXT,
                        action_payload TEXT DEFAULT '{}',
                        retry_policy TEXT DEFAULT '{}',
                        last_run_at TEXT,
                        next_run_at TEXT,
                        run_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 2. Automation History Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS automation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        automation_id TEXT NOT NULL,
                        trigger_type TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        completed_at TEXT,
                        result_summary TEXT,
                        error_message TEXT,
                        workflow_id TEXT,
                        FOREIGN KEY (automation_id) REFERENCES automations(id) ON DELETE CASCADE
                    )
                """)

                # 3. Notifications Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type TEXT NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        data TEXT DEFAULT '{}',
                        read INTEGER DEFAULT 0,
                        dismissed INTEGER DEFAULT 0,
                        snoozed_until TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 4. Reminders Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT NOT NULL,
                        due_at TEXT,
                        completed INTEGER DEFAULT 0,
                        snoozed_until TEXT,
                        recurring_cron TEXT,
                        project_id TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.commit()
                logger.info("AutomationLogger migrations applied successfully.")
        except Exception as e:
            logger.error(f"Error during AutomationLogger migrations: {e}")

    # ==================== AUTOMATIONS CRUD ====================

    def save_automation(self, auto: AutomationRule):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO automations (
                    id, name, description, enabled, status, autonomy_level,
                    trigger_config, action_type, workflow_objective, action_payload,
                    retry_policy, last_run_at, next_run_at, run_count, failure_count,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                auto.id,
                auto.name,
                auto.description,
                1 if auto.enabled else 0,
                auto.status.value if isinstance(auto.status, AutomationStatus) else auto.status,
                auto.autonomy_level.value if isinstance(auto.autonomy_level, AutonomyLevel) else auto.autonomy_level,
                json.dumps(auto.trigger_config.dict() if hasattr(auto.trigger_config, "dict") else auto.trigger_config),
                auto.action_type.value if isinstance(auto.action_type, AutomationActionType) else auto.action_type,
                auto.workflow_objective,
                json.dumps(auto.action_payload),
                json.dumps(auto.retry_policy.dict() if hasattr(auto.retry_policy, "dict") else auto.retry_policy),
                auto.last_run_at,
                auto.next_run_at,
                auto.run_count,
                auto.failure_count,
                auto.created_at,
                datetime.utcnow().isoformat()
            ))
            conn.commit()

    def get_automation(self, automation_id: str) -> Optional[AutomationRule]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM automations WHERE id = ?", (automation_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_automation(row)

    def list_automations(self) -> List[AutomationRule]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM automations ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_automation(r) for r in rows]

    def delete_automation(self, automation_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM automation_history WHERE automation_id = ?", (automation_id,))
            cursor.execute("DELETE FROM automations WHERE id = ?", (automation_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def _row_to_automation(self, row: sqlite3.Row) -> AutomationRule:
        d = dict(row)
        trig_dict = json.loads(d["trigger_config"]) if d["trigger_config"] else {}
        action_payload = json.loads(d["action_payload"]) if d["action_payload"] else {}
        retry_dict = json.loads(d["retry_policy"]) if d["retry_policy"] else {}

        return AutomationRule(
            id=d["id"],
            name=d["name"],
            description=d["description"] or "",
            enabled=bool(d["enabled"]),
            status=AutomationStatus(d["status"]) if d["status"] else AutomationStatus.ACTIVE,
            autonomy_level=AutonomyLevel(d["autonomy_level"]) if d["autonomy_level"] else AutonomyLevel.EXECUTE_LOW_RISK,
            trigger_config=TriggerConfig(**trig_dict),
            action_type=AutomationActionType(d["action_type"]) if d["action_type"] else AutomationActionType.WORKFLOW,
            workflow_objective=d["workflow_objective"],
            action_payload=action_payload,
            retry_policy=RetryPolicy(**retry_dict),
            last_run_at=d["last_run_at"],
            next_run_at=d["next_run_at"],
            run_count=d["run_count"] or 0,
            failure_count=d["failure_count"] or 0,
            created_at=d["created_at"] or "",
            updated_at=d["updated_at"] or ""
        )

    # ==================== EXECUTION HISTORY ====================

    def log_execution(
        self,
        automation_id: str,
        trigger_type: str,
        action_type: str,
        status: str,
        started_at: str,
        completed_at: Optional[str] = None,
        result_summary: Optional[str] = None,
        error_message: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO automation_history (
                    automation_id, trigger_type, action_type, status,
                    started_at, completed_at, result_summary, error_message, workflow_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                automation_id, trigger_type, action_type, status,
                started_at, completed_at, result_summary, error_message, workflow_id
            ))
            conn.commit()
            return cursor.lastrowid or 0

    def get_history(self, automation_id: Optional[str] = None, limit: int = 50) -> List[AutomationHistoryRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if automation_id:
                cursor.execute("""
                    SELECT * FROM automation_history
                    WHERE automation_id = ?
                    ORDER BY id DESC LIMIT ?
                """, (automation_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM automation_history
                    ORDER BY id DESC LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [
                AutomationHistoryRecord(
                    id=r["id"],
                    automation_id=r["automation_id"],
                    trigger_type=r["trigger_type"],
                    action_type=r["action_type"],
                    status=r["status"],
                    started_at=r["started_at"],
                    completed_at=r["completed_at"],
                    result_summary=r["result_summary"],
                    error_message=r["error_message"],
                    workflow_id=r["workflow_id"]
                ) for r in rows
            ]

    # ==================== NOTIFICATIONS ====================

    def add_notification(
        self,
        notif_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> NotificationItem:
        created_at = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notifications (type, title, message, data, read, dismissed, created_at)
                VALUES (?, ?, ?, ?, 0, 0, ?)
            """, (
                notif_type.value if isinstance(notif_type, NotificationType) else notif_type,
                title,
                message,
                json.dumps(data or {}),
                created_at
            ))
            conn.commit()
            nid = cursor.lastrowid or 0
            return NotificationItem(
                id=nid,
                type=notif_type,
                title=title,
                message=message,
                data=data or {},
                read=False,
                dismissed=False,
                created_at=created_at
            )

    def list_notifications(self, unread_only: bool = False, limit: int = 50) -> List[NotificationItem]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_iso = datetime.utcnow().isoformat()
            if unread_only:
                cursor.execute("""
                    SELECT * FROM notifications
                    WHERE dismissed = 0 AND read = 0 AND (snoozed_until IS NULL OR snoozed_until <= ?)
                    ORDER BY id DESC LIMIT ?
                """, (now_iso, limit))
            else:
                cursor.execute("""
                    SELECT * FROM notifications
                    WHERE dismissed = 0 AND (snoozed_until IS NULL OR snoozed_until <= ?)
                    ORDER BY id DESC LIMIT ?
                """, (now_iso, limit))
            rows = cursor.fetchall()
            items = []
            for r in rows:
                items.append(NotificationItem(
                    id=r["id"],
                    type=NotificationType(r["type"]) if r["type"] in NotificationType._value2member_map_ else NotificationType.REMINDER,
                    title=r["title"],
                    message=r["message"],
                    data=json.loads(r["data"]) if r["data"] else {},
                    read=bool(r["read"]),
                    dismissed=bool(r["dismissed"]),
                    snoozed_until=r["snoozed_until"],
                    created_at=r["created_at"]
                ))
            return items

    def mark_notification_read(self, notification_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET read = 1 WHERE id = ?", (notification_id,))
            conn.commit()
            return cursor.rowcount > 0

    def dismiss_notification(self, notification_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET dismissed = 1 WHERE id = ?", (notification_id,))
            conn.commit()
            return cursor.rowcount > 0

    def snooze_notification(self, notification_id: int, until_iso: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET snoozed_until = ? WHERE id = ?", (until_iso, notification_id))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== REMINDERS ====================

    def add_reminder(
        self,
        text: str,
        due_at: Optional[str] = None,
        recurring_cron: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> ReminderItem:
        created_at = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reminders (text, due_at, completed, recurring_cron, project_id, created_at)
                VALUES (?, ?, 0, ?, ?, ?)
            """, (text, due_at, recurring_cron, project_id, created_at))
            conn.commit()
            rid = cursor.lastrowid or 0
            return ReminderItem(
                id=rid,
                text=text,
                due_at=due_at,
                completed=False,
                recurring_cron=recurring_cron,
                project_id=project_id,
                created_at=created_at
            )

    def list_reminders(self, pending_only: bool = True) -> List[ReminderItem]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if pending_only:
                cursor.execute("""
                    SELECT * FROM reminders
                    WHERE completed = 0
                    ORDER BY due_at ASC, id DESC
                """)
            else:
                cursor.execute("SELECT * FROM reminders ORDER BY id DESC")
            rows = cursor.fetchall()
            return [
                ReminderItem(
                    id=r["id"],
                    text=r["text"],
                    due_at=r["due_at"],
                    completed=bool(r["completed"]),
                    snoozed_until=r["snoozed_until"],
                    recurring_cron=r["recurring_cron"],
                    project_id=r["project_id"],
                    created_at=r["created_at"]
                ) for r in rows
            ]

    def mark_reminder_completed(self, reminder_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET completed = 1 WHERE id = ?", (reminder_id,))
            conn.commit()
            return cursor.rowcount > 0

    def snooze_reminder(self, reminder_id: int, until_iso: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET snoozed_until = ? WHERE id = ?", (until_iso, reminder_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_reminder(self, reminder_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            return cursor.rowcount > 0

# Global singleton
automation_logger = AutomationLogger()
