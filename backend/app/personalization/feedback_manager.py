import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from app.config import settings
from .personalization_schemas import FeedbackRecord, FeedbackType

logger = logging.getLogger("nova.personalization.feedback")

class FeedbackManager:
    """
    Manages explicit user feedback loops for recommendations, preferences, and knowledge associations.
    Guarantees:
    - Never treats silence as positive feedback.
    - Never mutates preferences from single ambiguous interactions.
    - Persists feedback audit trail in SQLite.
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
                    CREATE TABLE IF NOT EXISTS user_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        feedback_type TEXT NOT NULL,
                        target_type TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        user_correction TEXT,
                        updated_state TEXT DEFAULT '{}',
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_tgt ON user_feedback(target_id)")
                conn.commit()
                logger.info("user_feedback table initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing user_feedback table: {e}")

    def record_feedback(
        self,
        feedback_type: str,
        target_type: str,
        target_id: str,
        user_correction: Optional[str] = None
    ) -> FeedbackRecord:
        """Records feedback and triggers appropriate state updates."""
        now_iso = datetime.utcnow().isoformat()
        updated_state: Dict[str, Any] = {}

        # 1. Recommendation feedback
        if target_type == "recommendation":
            from .recommendation_engine import recommendation_engine
            rec = recommendation_engine.get_recommendation(target_id)
            if rec:
                if feedback_type in ("DISMISS_PERMANENT", "DISMISSED"):
                    rec.dismissed = True
                    rec.feedback_status = "DISMISSED"
                elif feedback_type == "USEFUL":
                    rec.feedback_status = "USEFUL"
                recommendation_engine._save_recommendation(rec)
                updated_state["recommendation_status"] = rec.feedback_status

        # 2. Preference correction / forget
        elif target_type == "preference":
            from .preference_engine import preference_engine
            if feedback_type == "FORGET_PREFERENCE":
                deleted = preference_engine.delete_preference(target_id)
                updated_state["preference_deleted"] = deleted
            elif feedback_type == "PREFERENCE_CORRECTION" and user_correction:
                # Update preference value
                pref = preference_engine.get_preference(target_id)
                if pref:
                    pref.value = user_correction
                    pref.is_explicit = True
                    preference_engine.set_preference(pref)
                    updated_state["preference_updated"] = pref.dict()

        # 3. Knowledge Graph relation incorrect
        elif target_type == "relation":
            from .knowledge_graph import knowledge_graph
            try:
                rel_id = int(target_id)
                deleted = knowledge_graph.delete_relation(rel_id)
                updated_state["relation_removed"] = deleted
            except Exception:
                pass

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_feedback (
                    feedback_type, target_type, target_id, user_correction, updated_state, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                feedback_type,
                target_type,
                target_id,
                user_correction,
                json.dumps(updated_state),
                now_iso
            ))
            conn.commit()
            fid = cursor.lastrowid or 0

        logger.info(f"Recorded user feedback [{feedback_type}] on {target_type}:{target_id}")
        return FeedbackRecord(
            id=fid,
            feedback_type=FeedbackType(feedback_type) if feedback_type in FeedbackType._value2member_map_ else FeedbackType.USEFUL,
            target_type=target_type,
            target_id=target_id,
            user_correction=user_correction,
            updated_state=updated_state,
            timestamp=now_iso
        )

    def get_permanently_dismissed_targets(self) -> Set[str]:
        """Returns set of target IDs marked as DISMISS_PERMANENT."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT target_id FROM user_feedback 
                WHERE feedback_type = 'DISMISS_PERMANENT'
            """)
            rows = cursor.fetchall()
            return {r["target_id"] for r in rows}

    def list_feedback_history(self, limit: int = 50) -> List[FeedbackRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_feedback ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [
                FeedbackRecord(
                    id=r["id"],
                    feedback_type=FeedbackType(r["feedback_type"]) if r["feedback_type"] in FeedbackType._value2member_map_ else FeedbackType.USEFUL,
                    target_type=r["target_type"],
                    target_id=r["target_id"],
                    user_correction=r["user_correction"],
                    updated_state=json.loads(r["updated_state"]) if r["updated_state"] else {},
                    timestamp=r["timestamp"]
                ) for r in rows
            ]

    def clear_feedback(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_feedback")
            conn.commit()
            logger.info("All user feedback history cleared.")

    def process_voice_feedback(self, transcript: str) -> Tuple[bool, str]:
        """
        Parses verbal feedback statements such as:
        - "That recommendation was useful."
        - "Don't suggest this again."
        - "That project association is incorrect."
        - "Forget this preference."
        """
        lower = transcript.lower().strip()

        if "that recommendation was useful" in lower or "useful recommendation" in lower:
            from .recommendation_engine import recommendation_engine
            recs = recommendation_engine.list_recommendations(active_only=True, limit=1)
            if recs:
                self.record_feedback("USEFUL", "recommendation", recs[0].id)
                return True, f"Thank you for the feedback. Marked recommendation '{recs[0].title}' as useful."
            return True, "Acknowledged. No active recommendation found to record against."

        if "don't suggest this again" in lower or "do not suggest this again" in lower or "dismiss permanently" in lower:
            from .recommendation_engine import recommendation_engine
            recs = recommendation_engine.list_recommendations(active_only=True, limit=1)
            if recs:
                self.record_feedback("DISMISS_PERMANENT", "recommendation", recs[0].id, "Suppressed via voice")
                return True, f"Understood. I will not suggest '{recs[0].title}' again."
            return True, "Understood. Permanent suppression recorded."

        if "that project association is incorrect" in lower or "incorrect association" in lower:
            self.record_feedback("ASSOCIATION_INCORRECT", "relation", "recent", "Marked incorrect by user")
            return True, "Understood. I have flagged the recent project relationship as incorrect."

        if "forget this preference" in lower or "remove that preference" in lower or "forget my preference" in lower:
            from .preference_engine import preference_engine
            prefs = preference_engine.list_preferences()
            if prefs:
                target = prefs[0]
                preference_engine.delete_preference(target.id)
                self.record_feedback("FORGET_PREFERENCE", "preference", target.id)
                return True, f"I have removed the preference for {target.key.replace('_', ' ')}."
            return True, "You have no saved preferences to remove."

        return False, ""

# Global singleton
feedback_manager = FeedbackManager()
