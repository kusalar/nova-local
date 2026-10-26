import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.config import settings
from .personalization_schemas import Recommendation
from .personalization_privacy import personalization_privacy

logger = logging.getLogger("nova.personalization.recommendations")

class RecommendationEngine:
    """
    Generates intelligent, context-aware, evidence-based recommendations.
    Every recommendation is backed by verifiable facts:
    - Failed workflows needing inspection or retry
    - Unfinished project memory tasks
    - Upcoming reminder deadlines
    - Projects lacking recent health check evaluations
    Recommendations NEVER execute actions automatically.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        from app.database import get_db_connection
        return get_db_connection(self.db_path)

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS recommendations (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        recommendation_text TEXT NOT NULL,
                        supporting_evidence TEXT NOT NULL,
                        related_project TEXT,
                        related_task TEXT,
                        confidence REAL DEFAULT 1.0,
                        reason TEXT NOT NULL,
                        suggested_action TEXT NOT NULL,
                        dismissed INTEGER DEFAULT 0,
                        feedback_status TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_rec_proj ON recommendations(related_project)")
                conn.commit()
                logger.info("recommendations table initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing recommendations table: {e}")

    # ==================== GENERATION ====================

    def generate_recommendations(self) -> List[Recommendation]:
        """
        Scans reliable subsystem context and compiles evidence-based recommendations.
        Honors privacy settings and suppressed feedback patterns.
        """
        if not personalization_privacy.is_recommendations_enabled():
            return []

        generated: List[Recommendation] = []
        now_iso = datetime.utcnow().isoformat()

        # Check permanently dismissed recommendation keys from feedback
        from .feedback_manager import feedback_manager
        dismissed_patterns = feedback_manager.get_permanently_dismissed_targets()

        # -------------------------------------------------------------
        # 1. Previously Failed Workflows Needing Attention
        # -------------------------------------------------------------
        try:
            from app.agents.workflow_logger import workflow_logger
            recent_wfs = workflow_logger.list_workflows(limit=5)
            for wf in recent_wfs:
                if wf.get("status") == "FAILED":
                    rec_id = f"rec_failed_wf_{wf['workflow_id']}"
                    if rec_id in dismissed_patterns:
                        continue
                    obj = wf.get("objective", "Unknown")
                    rec = Recommendation(
                        id=rec_id,
                        title=f"Workflow Failed: {obj[:40]}",
                        recommendation_text=f"The multi-agent workflow '{obj}' encountered an error. Consider inspecting step reports or re-planning.",
                        supporting_evidence=[
                            f"Workflow ID: {wf['workflow_id']}",
                            f"Status: FAILED",
                            f"Total Steps: {wf.get('total_steps')}, Completed: {wf.get('completed_steps')}"
                        ],
                        related_project=wf.get("project_id"),
                        confidence=0.9,
                        reason="Workflow halted prematurely due to step error.",
                        suggested_action=f"Retry workflow or inspect error report: /api/workflows/{wf['workflow_id']}/report"
                    )
                    generated.append(rec)
        except Exception as e:
            logger.debug(f"Failed workflow check error: {e}")

        # -------------------------------------------------------------
        # 2. Projects with Unfinished Tasks
        # -------------------------------------------------------------
        try:
            from app.memory.project_memory import project_memory
            projects = project_memory.list_projects()
            for p in projects:
                if p.pending_tasks:
                    rec_id = f"rec_pending_tasks_{p.id}"
                    if rec_id in dismissed_patterns:
                        continue
                    task_count = len(p.pending_tasks)
                    top_tasks = p.pending_tasks[:3]
                    rec = Recommendation(
                        id=rec_id,
                        title=f"Unfinished Tasks in {p.name}",
                        recommendation_text=f"Project '{p.name}' has {task_count} pending task(s) awaiting completion.",
                        supporting_evidence=[f"Task: {t}" for t in top_tasks],
                        related_project=p.id,
                        confidence=0.85,
                        reason="Project has pending tasks tracked in persistent memory.",
                        suggested_action="Review and execute pending tasks in the Operations Center."
                    )
                    generated.append(rec)
        except Exception as e:
            logger.debug(f"Project pending tasks check error: {e}")

        # -------------------------------------------------------------
        # 3. Upcoming Deadlines in Smart Reminders
        # -------------------------------------------------------------
        try:
            from app.automation.automation_logger import automation_logger
            reminders = automation_logger.list_reminders(pending_only=True)
            for r in reminders:
                if r.due_at:
                    rec_id = f"rec_deadline_{r.id}"
                    if rec_id in dismissed_patterns:
                        continue
                    rec = Recommendation(
                        id=rec_id,
                        title="Approaching Reminder Deadline",
                        recommendation_text=f"Reminder item '{r.text}' is due at {r.due_at}.",
                        supporting_evidence=[
                            f"Reminder ID: {r.id}",
                            f"Scheduled Due: {r.due_at}"
                        ],
                        related_project=r.project_id,
                        related_task=str(r.id),
                        confidence=0.95,
                        reason="Scheduled reminder deadline is approaching.",
                        suggested_action="Address task or snooze deadline."
                    )
                    generated.append(rec)
        except Exception as e:
            logger.debug(f"Reminders check error: {e}")

        # -------------------------------------------------------------
        # 4. Project Lacking Recent Health Check
        # -------------------------------------------------------------
        try:
            from app.memory.project_memory import project_memory
            for p in project_memory.list_projects():
                rec_id = f"rec_health_check_{p.id}"
                if rec_id in dismissed_patterns:
                    continue
                rec = Recommendation(
                    id=rec_id,
                    title=f"Schedule Health Check: {p.name}",
                    recommendation_text=f"Project '{p.name}' has active development tasks. Consider running a project health assessment.",
                    supporting_evidence=[
                        f"Project: {p.name} ({p.id})",
                        f"Tech Stack: {', '.join(p.tech_stack) if p.tech_stack else 'Standard'}"
                    ],
                    related_project=p.id,
                    confidence=0.8,
                    reason="Proactive health verification ensures code integrity.",
                    suggested_action=f"Run project health check for workspace: D:\\Nova"
                )
                generated.append(rec)
        except Exception as e:
            logger.debug(f"Health check recommendation error: {e}")

        # Persist generated recommendations
        for r in generated:
            self._save_recommendation(r)

        return self.list_recommendations(active_only=True)

    # ==================== CRUD & FEEDBACK ====================

    def _save_recommendation(self, rec: Recommendation):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO recommendations (
                    id, title, recommendation_text, supporting_evidence, related_project,
                    related_task, confidence, reason, suggested_action, dismissed,
                    feedback_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.id,
                rec.title,
                rec.recommendation_text,
                json.dumps(rec.supporting_evidence),
                rec.related_project,
                rec.related_task,
                rec.confidence,
                rec.reason,
                rec.suggested_action,
                1 if rec.dismissed else 0,
                rec.feedback_status,
                rec.created_at
            ))
            conn.commit()

    def list_recommendations(self, active_only: bool = True, limit: int = 50) -> List[Recommendation]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute("""
                    SELECT * FROM recommendations 
                    WHERE dismissed = 0 
                    ORDER BY confidence DESC, created_at DESC LIMIT ?
                """, (limit,))
            else:
                cursor.execute("SELECT * FROM recommendations ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [self._row_to_recommendation(r) for r in rows]

    def get_recommendation(self, rec_id: str) -> Optional[Recommendation]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recommendations WHERE id = ?", (rec_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_recommendation(row)

    def dismiss_recommendation(self, rec_id: str, permanent: bool = False) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE recommendations SET dismissed = 1, feedback_status = 'DISMISSED' WHERE id = ?", (rec_id,))
            conn.commit()

        if permanent:
            from .feedback_manager import feedback_manager
            feedback_manager.record_feedback(
                feedback_type="DISMISS_PERMANENT",
                target_type="recommendation",
                target_id=rec_id,
                user_correction="Permanently suppressed by user"
            )

        return True

    def clear_recommendations(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM recommendations")
            conn.commit()
            logger.info("All recommendations cleared.")

    def _row_to_recommendation(self, row: sqlite3.Row) -> Recommendation:
        d = dict(row)
        return Recommendation(
            id=d["id"],
            title=d["title"],
            recommendation_text=d["recommendation_text"],
            supporting_evidence=json.loads(d["supporting_evidence"]) if d["supporting_evidence"] else [],
            related_project=d["related_project"],
            related_task=d["related_task"],
            confidence=float(d["confidence"] or 1.0),
            reason=d["reason"],
            suggested_action=d["suggested_action"],
            dismissed=bool(d["dismissed"]),
            feedback_status=d["feedback_status"],
            created_at=d["created_at"]
        )

# Global singleton
recommendation_engine = RecommendationEngine()
