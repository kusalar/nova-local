import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings
from app.tools.permission_manager import permission_manager
from app.tools.tool_schemas import ExecutionRecord, TaskPlan, TaskStep, TaskStatus, StepStatus

logger = logging.getLogger("nova.tools.logger")

class ExecutionLogger:
    """
    Manages persistent SQLite audit records for all tool executions and tasks.
    Enforces non-destructive migrations and sensitive data redaction.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._migrate()

    def _get_connection(self) -> sqlite3.Connection:
        from app.database import get_db_connection
        return get_db_connection(self.db_path)

    def _migrate(self):
        """Creates v0.4 task and execution audit tables if not present."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Tasks Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS operational_tasks (
                        task_id TEXT PRIMARY KEY,
                        prompt TEXT NOT NULL,
                        description TEXT NOT NULL,
                        status TEXT NOT NULL,
                        requires_confirmation INTEGER DEFAULT 0,
                        confirmation_reason TEXT,
                        total_steps INTEGER DEFAULT 0,
                        current_step INTEGER DEFAULT 0,
                        rollback_eligible INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        completed_at DATETIME
                    )
                """)

                # 2. Task Steps Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS operational_task_steps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT NOT NULL,
                        step_id INTEGER NOT NULL,
                        tool_id TEXT NOT NULL,
                        description TEXT NOT NULL,
                        arguments TEXT NOT NULL,
                        permission_level TEXT NOT NULL,
                        status TEXT NOT NULL,
                        result TEXT,
                        error TEXT,
                        execution_id TEXT,
                        started_at DATETIME,
                        completed_at DATETIME,
                        UNIQUE(task_id, step_id)
                    )
                """)

                # 3. Tool Executions Table (Audit Log)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tool_executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        execution_id TEXT UNIQUE NOT NULL,
                        task_id TEXT,
                        step_id INTEGER,
                        tool_id TEXT NOT NULL,
                        tool_name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        permission_level TEXT NOT NULL,
                        arguments TEXT NOT NULL,
                        status TEXT NOT NULL,
                        result TEXT,
                        error_message TEXT,
                        is_reversible INTEGER DEFAULT 0,
                        is_rolled_back INTEGER DEFAULT 0,
                        rollback_data TEXT,
                        started_at DATETIME NOT NULL,
                        completed_at DATETIME,
                        duration_ms REAL
                    )
                """)

                # Indices
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_task ON tool_executions (task_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_tool ON tool_executions (tool_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_steps_task ON operational_task_steps (task_id)")
                conn.commit()
                logger.info("Operational execution SQLite tables migrated successfully.")
        except Exception as e:
            logger.error(f"Failed to migrate operational tables: {e}")

    def save_task(self, task: TaskPlan) -> bool:
        """Persist or update a task plan."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO operational_tasks (
                        task_id, prompt, description, status, requires_confirmation,
                        confirmation_reason, total_steps, current_step, rollback_eligible,
                        created_at, updated_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        status = excluded.status,
                        requires_confirmation = excluded.requires_confirmation,
                        confirmation_reason = excluded.confirmation_reason,
                        total_steps = excluded.total_steps,
                        current_step = excluded.current_step,
                        rollback_eligible = excluded.rollback_eligible,
                        updated_at = excluded.updated_at,
                        completed_at = excluded.completed_at
                """, (
                    task.task_id,
                    task.prompt,
                    task.description,
                    task.status.value if hasattr(task.status, 'value') else str(task.status),
                    1 if task.requires_confirmation else 0,
                    task.confirmation_reason,
                    len(task.steps),
                    task.current_step,
                    1 if task.rollback_eligible else 0,
                    task.created_at,
                    datetime.now().isoformat(),
                    task.completed_at
                ))

                # Also persist steps
                for step in task.steps:
                    redacted_args = permission_manager.redact_sensitive_data(step.arguments)
                    cursor.execute("""
                        INSERT INTO operational_task_steps (
                            task_id, step_id, tool_id, description, arguments,
                            permission_level, status, result, error, execution_id,
                            started_at, completed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(task_id, step_id) DO UPDATE SET
                            status = excluded.status,
                            result = excluded.result,
                            error = excluded.error,
                            execution_id = excluded.execution_id,
                            started_at = excluded.started_at,
                            completed_at = excluded.completed_at
                    """, (
                        task.task_id,
                        step.step_id,
                        step.tool_id,
                        step.description,
                        json.dumps(redacted_args),
                        step.permission_level.value if hasattr(step.permission_level, 'value') else str(step.permission_level),
                        step.status.value if hasattr(step.status, 'value') else str(step.status),
                        json.dumps(step.result) if step.result else None,
                        step.error,
                        step.execution_id,
                        step.started_at,
                        step.completed_at
                    ))

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving task '{task.task_id}': {e}")
            return False

    def get_task(self, task_id: str) -> Optional[TaskPlan]:
        """Fetch task and associated steps from SQLite."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM operational_tasks WHERE task_id = ?", (task_id,))
                task_row = cursor.fetchone()
                if not task_row:
                    return None

                cursor.execute(
                    "SELECT * FROM operational_task_steps WHERE task_id = ? ORDER BY step_id ASC",
                    (task_id,)
                )
                step_rows = cursor.fetchall()

                steps = []
                for s in step_rows:
                    steps.append(TaskStep(
                        step_id=s["step_id"],
                        tool_id=s["tool_id"],
                        description=s["description"],
                        arguments=json.loads(s["arguments"]) if s["arguments"] else {},
                        permission_level=s["permission_level"],
                        status=s["status"],
                        result=json.loads(s["result"]) if s["result"] else None,
                        error=s["error"],
                        execution_id=s["execution_id"],
                        started_at=s["started_at"],
                        completed_at=s["completed_at"]
                    ))

                return TaskPlan(
                    task_id=task_row["task_id"],
                    prompt=task_row["prompt"],
                    description=task_row["description"],
                    steps=steps,
                    status=task_row["status"],
                    requires_confirmation=bool(task_row["requires_confirmation"]),
                    confirmation_reason=task_row["confirmation_reason"],
                    created_at=task_row["created_at"],
                    updated_at=task_row["updated_at"],
                    completed_at=task_row["completed_at"],
                    total_steps=task_row["total_steps"],
                    current_step=task_row["current_step"],
                    rollback_eligible=bool(task_row["rollback_eligible"])
                )
        except Exception as e:
            logger.error(f"Error retrieving task '{task_id}': {e}")
            return None

    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent tasks."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT task_id, prompt, description, status, requires_confirmation,
                           confirmation_reason, total_steps, current_step, rollback_eligible,
                           created_at, completed_at
                    FROM operational_tasks
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return []

    def log_execution_start(
        self,
        execution_id: str,
        tool_id: str,
        tool_name: str,
        category: str,
        permission_level: str,
        arguments: Dict[str, Any],
        task_id: Optional[str] = None,
        step_id: Optional[int] = None,
        is_reversible: bool = False
    ) -> bool:
        """Create initial audit entry when tool starts."""
        try:
            redacted_args = permission_manager.redact_sensitive_data(arguments)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tool_executions (
                        execution_id, task_id, step_id, tool_id, tool_name,
                        category, permission_level, arguments, status, is_reversible,
                        started_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id,
                    task_id,
                    step_id,
                    tool_id,
                    tool_name,
                    category,
                    permission_level,
                    json.dumps(redacted_args),
                    "RUNNING",
                    1 if is_reversible else 0,
                    datetime.now().isoformat()
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error logging execution start '{execution_id}': {e}")
            return False

    def log_execution_complete(
        self,
        execution_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        rollback_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ) -> bool:
        """Finalize execution audit entry with outcomes and undo data."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tool_executions
                    SET status = ?,
                        result = ?,
                        error_message = ?,
                        rollback_data = ?,
                        duration_ms = ?,
                        completed_at = ?
                    WHERE execution_id = ?
                """, (
                    status,
                    json.dumps(result) if result else None,
                    error_message,
                    json.dumps(rollback_data) if rollback_data else None,
                    duration_ms,
                    datetime.now().isoformat(),
                    execution_id
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error logging execution completion '{execution_id}': {e}")
            return False

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Fetch execution record by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tool_executions WHERE execution_id = ?", (execution_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                d = dict(row)
                d["arguments"] = json.loads(d["arguments"]) if d["arguments"] else {}
                d["result"] = json.loads(d["result"]) if d["result"] else None
                d["rollback_data"] = json.loads(d["rollback_data"]) if d.get("rollback_data") else None
                return d
        except Exception as e:
            logger.error(f"Error getting execution '{execution_id}': {e}")
            return None

    def list_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List audit execution history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, execution_id, task_id, step_id, tool_id, tool_name,
                           category, permission_level, arguments, status, result,
                           error_message, is_reversible, is_rolled_back, started_at,
                           completed_at, duration_ms
                    FROM tool_executions
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
                results = []
                for row in cursor.fetchall():
                    item = dict(row)
                    item["arguments"] = json.loads(item["arguments"]) if item["arguments"] else {}
                    item["result"] = json.loads(item["result"]) if item["result"] else None
                    results.append(item)
                return results
        except Exception as e:
            logger.error(f"Error listing executions: {e}")
            return []

    def mark_rolled_back(self, execution_id: str) -> bool:
        """Mark record as rolled back."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tool_executions SET is_rolled_back = 1 WHERE execution_id = ?",
                    (execution_id,)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to mark execution rolled back: {e}")
            return False

execution_logger = ExecutionLogger()
