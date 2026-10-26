import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings
from .agent_schemas import (
    WorkflowPlan, WorkflowStep, WorkflowEvent, WorkflowStatus,
    WorkflowStepStatus, EventType, AgentRole, RetryPolicy, WorkflowReport
)

logger = logging.getLogger("nova.agents.logger")

class WorkflowLogger:
    """
    Persistent SQLite storage and audit system for agentic workflows,
    steps, state transitions, approvals, events, and reports.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._migrate()

    def _get_connection(self) -> sqlite3.Connection:
        from app.database import get_db_connection
        return get_db_connection(self.db_path)

    def _migrate(self):
        """Creates v0.6 workflow orchestration tables if not existing."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Workflows Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS agent_workflows (
                        workflow_id TEXT PRIMARY KEY,
                        objective TEXT NOT NULL,
                        project_id TEXT,
                        status TEXT NOT NULL,
                        requires_approval INTEGER DEFAULT 0,
                        pending_approval_step_id INTEGER,
                        approval_reason TEXT,
                        total_steps INTEGER DEFAULT 0,
                        completed_steps INTEGER DEFAULT 0,
                        final_report TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        completed_at DATETIME
                    )
                """)

                # 2. Workflow Steps Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS agent_workflow_steps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        workflow_id TEXT NOT NULL,
                        step_id INTEGER NOT NULL,
                        description TEXT NOT NULL,
                        assigned_agent TEXT NOT NULL,
                        tool_id TEXT,
                        arguments TEXT NOT NULL,
                        dependencies TEXT NOT NULL,
                        permission_level TEXT NOT NULL,
                        expected_output TEXT,
                        timeout_seconds INTEGER DEFAULT 45,
                        retry_policy TEXT,
                        status TEXT NOT NULL,
                        result TEXT,
                        error TEXT,
                        reflection TEXT,
                        started_at DATETIME,
                        completed_at DATETIME,
                        FOREIGN KEY (workflow_id) REFERENCES agent_workflows(workflow_id) ON DELETE CASCADE,
                        UNIQUE(workflow_id, step_id)
                    )
                """)

                # 3. Agent Events Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS agent_events (
                        event_id TEXT PRIMARY KEY,
                        workflow_id TEXT NOT NULL,
                        step_id INTEGER,
                        event_type TEXT NOT NULL,
                        agent_role TEXT,
                        message TEXT NOT NULL,
                        payload TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 4. Workflow Approvals Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_approvals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        workflow_id TEXT NOT NULL,
                        step_id INTEGER NOT NULL,
                        tool_id TEXT NOT NULL,
                        action_description TEXT NOT NULL,
                        arguments_preview TEXT NOT NULL,
                        status TEXT NOT NULL,
                        requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        decided_at DATETIME,
                        expires_at DATETIME
                    )
                """)

                # 5. Workflow Summaries Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_summaries (
                        workflow_id TEXT PRIMARY KEY,
                        objective TEXT NOT NULL,
                        project_id TEXT,
                        status TEXT NOT NULL,
                        duration_seconds REAL,
                        total_steps INTEGER,
                        successful_steps INTEGER,
                        failed_steps INTEGER,
                        summary TEXT,
                        key_findings TEXT,
                        verifiable_evidence TEXT,
                        unresolved_issues TEXT,
                        completed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.commit()
                logger.info("Agent orchestration database migration verified.")
        except Exception as e:
            logger.error(f"Error migrating agent workflow tables: {e}")

    # ==========================================
    # Workflow CRUD
    # ==========================================

    def save_workflow(self, plan: WorkflowPlan):
        """Insert or update a complete workflow plan and its steps."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO agent_workflows (
                    workflow_id, objective, project_id, status, requires_approval,
                    pending_approval_step_id, approval_reason, total_steps,
                    completed_steps, final_report, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workflow_id) DO UPDATE SET
                    status=excluded.status,
                    requires_approval=excluded.requires_approval,
                    pending_approval_step_id=excluded.pending_approval_step_id,
                    approval_reason=excluded.approval_reason,
                    total_steps=excluded.total_steps,
                    completed_steps=excluded.completed_steps,
                    final_report=excluded.final_report,
                    updated_at=?,
                    completed_at=excluded.completed_at
            """, (
                plan.workflow_id, plan.objective, plan.project_id, plan.status.value,
                1 if plan.requires_approval else 0, plan.pending_approval_step_id,
                plan.approval_reason, plan.total_steps, plan.completed_steps,
                plan.final_report, plan.created_at, now, plan.completed_at, now
            ))

            for step in plan.steps:
                cursor.execute("""
                    INSERT INTO agent_workflow_steps (
                        workflow_id, step_id, description, assigned_agent, tool_id,
                        arguments, dependencies, permission_level, expected_output,
                        timeout_seconds, retry_policy, status, result, error, reflection,
                        started_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(workflow_id, step_id) DO UPDATE SET
                        status=excluded.status,
                        result=excluded.result,
                        error=excluded.error,
                        reflection=excluded.reflection,
                        started_at=excluded.started_at,
                        completed_at=excluded.completed_at,
                        retry_policy=excluded.retry_policy
                """, (
                    plan.workflow_id, step.step_id, step.description,
                    step.assigned_agent.value, step.tool_id,
                    json.dumps(step.arguments), json.dumps(step.dependencies),
                    step.permission_level.value, step.expected_output,
                    step.timeout_seconds, json.dumps(step.retry_policy.dict()),
                    step.status.value,
                    json.dumps(step.result) if step.result is not None else None,
                    step.error, step.reflection, step.started_at, step.completed_at
                ))

            conn.commit()

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowPlan]:
        """Fetch a workflow and its steps by workflow_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_workflows WHERE workflow_id = ?", (workflow_id,))
            w_row = cursor.fetchone()
            if not w_row:
                return None

            cursor.execute("SELECT * FROM agent_workflow_steps WHERE workflow_id = ? ORDER BY step_id ASC", (workflow_id,))
            step_rows = cursor.fetchall()

            steps: List[WorkflowStep] = []
            for s in step_rows:
                args = json.loads(s["arguments"]) if s["arguments"] else {}
                deps = json.loads(s["dependencies"]) if s["dependencies"] else []
                res = json.loads(s["result"]) if s["result"] else None
                retry = json.loads(s["retry_policy"]) if s["retry_policy"] else {}

                steps.append(WorkflowStep(
                    step_id=s["step_id"],
                    workflow_id=s["workflow_id"],
                    description=s["description"],
                    assigned_agent=AgentRole(s["assigned_agent"]),
                    tool_id=s["tool_id"],
                    arguments=args,
                    dependencies=deps,
                    permission_level=s["permission_level"],
                    expected_output=s["expected_output"] or "",
                    timeout_seconds=s["timeout_seconds"],
                    retry_policy=RetryPolicy(**retry) if retry else RetryPolicy(),
                    status=WorkflowStepStatus(s["status"]),
                    result=res,
                    error=s["error"],
                    reflection=s["reflection"],
                    started_at=s["started_at"],
                    completed_at=s["completed_at"]
                ))

            return WorkflowPlan(
                workflow_id=w_row["workflow_id"],
                objective=w_row["objective"],
                project_id=w_row["project_id"],
                steps=steps,
                status=WorkflowStatus(w_row["status"]),
                requires_approval=bool(w_row["requires_approval"]),
                pending_approval_step_id=w_row["pending_approval_step_id"],
                approval_reason=w_row["approval_reason"],
                created_at=w_row["created_at"],
                updated_at=w_row["updated_at"],
                completed_at=w_row["completed_at"],
                total_steps=w_row["total_steps"],
                completed_steps=w_row["completed_steps"],
                final_report=w_row["final_report"]
            )

    def list_workflows(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent workflows with summary metadata."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT workflow_id, objective, project_id, status, total_steps,
                       completed_steps, requires_approval, created_at, updated_at, completed_at
                FROM agent_workflows
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    # ==========================================
    # Events Logging
    # ==========================================

    def log_event(self, event: WorkflowEvent):
        """Append an orchestration event to the audit trail."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_events (
                    event_id, workflow_id, step_id, event_type, agent_role, message, payload, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.workflow_id, event.step_id, event.event_type.value,
                event.agent_role.value if event.agent_role else None,
                event.message, json.dumps(event.payload), event.timestamp
            ))
            conn.commit()

    def get_workflow_events(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Retrieve audit events for a specific workflow."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_events WHERE workflow_id = ? ORDER BY timestamp ASC
            """, (workflow_id,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if d["payload"]:
                    try:
                        d["payload"] = json.loads(d["payload"])
                    except Exception:
                        pass
                result.append(d)
            return result

    # ==========================================
    # Restart Recovery Safeguard
    # ==========================================

    def handle_restart_recovery(self) -> int:
        """
        Scans for workflows left in 'RUNNING' status during an unexpected shutdown.
        Safely transitions them to 'PAUSED' and marks any 'RUNNING' steps as 'PENDING_APPROVAL'
        or 'FAILED', guaranteeing no partially completed modifications auto-resume without validation.
        """
        recovered_count = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT workflow_id FROM agent_workflows WHERE status = 'RUNNING'")
            running = cursor.fetchall()

            for r in running:
                w_id = r["workflow_id"]
                # Pause workflow
                cursor.execute("""
                    UPDATE agent_workflows
                    SET status = 'PAUSED',
                        requires_approval = 1,
                        approval_reason = 'System restarted during execution. Manual resumption and verification required.'
                    WHERE workflow_id = ?
                """, (w_id,))

                # Pause any active running steps
                cursor.execute("""
                    UPDATE agent_workflow_steps
                    SET status = 'PENDING_APPROVAL',
                        error = 'Interrupted by application restart.'
                    WHERE workflow_id = ? AND status = 'RUNNING'
                """, (w_id,))

                recovered_count += 1

            conn.commit()

        if recovered_count > 0:
            logger.warning(f"Crash recovery: safely paused {recovered_count} active workflow(s).")
        return recovered_count

# Singleton
workflow_logger = WorkflowLogger()
