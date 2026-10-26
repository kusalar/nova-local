import sqlite3
import logging
import uuid
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.config import settings
from .personalization_schemas import (
    UserPreference, PreferenceCreate, PreferenceUpdate, PreferenceCategory
)
from .personalization_privacy import personalization_privacy

logger = logging.getLogger("nova.personalization.preferences")

class PreferenceEngine:
    """
    Manages explicit user preferences and permitted inferred adaptations.
    Guarantees:
    - Explicit user preferences ALWAYS take precedence over inferred preferences.
    - Contradictory preferences are detected and reconciled with newest explicit instruction.
    - Non-destructive SQLite persistence.
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
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        is_explicit INTEGER DEFAULT 1,
                        source TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        context_scope TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pref_key ON user_preferences(key)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pref_cat ON user_preferences(category)")
                conn.commit()
                logger.info("user_preferences table initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing user_preferences table: {e}")

    # ==================== CRUD OPERATIONS ====================

    def set_preference(self, data: PreferenceCreate) -> UserPreference:
        """
        Creates or updates a user preference.
        Enforces explicit precedence: Inferred preferences cannot overwrite explicit ones.
        """
        now_iso = datetime.utcnow().isoformat()
        pref_id = f"pref_{data.category.value}_{data.key}".replace(" ", "_").lower()

        existing = self.get_preference(data.key, context_scope=data.context_scope)
        if existing:
            # Rule: Explicit preferences take priority over inferred ones
            if existing.is_explicit and not data.is_explicit:
                logger.info(f"Ignoring inferred preference '{data.key}' because explicit preference already exists.")
                return existing
            pref_id = existing.id

        pref = UserPreference(
            id=pref_id,
            category=data.category,
            key=data.key,
            value=data.value,
            is_explicit=data.is_explicit,
            source=data.source or "user_directive",
            confidence=1.0 if data.is_explicit else 0.7,
            context_scope=data.context_scope,
            created_at=existing.created_at if existing else now_iso,
            updated_at=now_iso
        )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences (
                    id, category, key, value, is_explicit, source, confidence,
                    context_scope, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pref.id,
                pref.category.value if isinstance(pref.category, PreferenceCategory) else pref.category,
                pref.key,
                pref.value,
                1 if pref.is_explicit else 0,
                pref.source,
                pref.confidence,
                pref.context_scope,
                pref.created_at,
                pref.updated_at
            ))
            conn.commit()

        logger.info(f"Saved preference [{pref.category}]: {pref.key}='{pref.value}' (explicit={pref.is_explicit})")
        return pref

    def get_preference(self, key: str, context_scope: Optional[str] = None) -> Optional[UserPreference]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if context_scope:
                cursor.execute("""
                    SELECT * FROM user_preferences 
                    WHERE key = ? AND (context_scope = ? OR context_scope IS NULL)
                    ORDER BY context_scope DESC, is_explicit DESC, updated_at DESC LIMIT 1
                """, (key, context_scope))
            else:
                cursor.execute("""
                    SELECT * FROM user_preferences 
                    WHERE key = ? 
                    ORDER BY is_explicit DESC, updated_at DESC LIMIT 1
                """, (key,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_preference(row)

    def list_preferences(
        self,
        category: Optional[PreferenceCategory] = None,
        explicit_only: bool = False,
        context_scope: Optional[str] = None
    ) -> List[UserPreference]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM user_preferences WHERE 1=1"
            params: List[Any] = []

            if category:
                query += " AND category = ?"
                params.append(category.value if isinstance(category, PreferenceCategory) else category)
            if explicit_only:
                query += " AND is_explicit = 1"
            if context_scope:
                query += " AND (context_scope = ? OR context_scope IS NULL)"
                params.append(context_scope)

            query += " ORDER BY is_explicit DESC, category ASC, updated_at DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_preference(r) for r in rows]

    def update_preference(self, pref_id: str, updates: PreferenceUpdate) -> Optional[UserPreference]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_preferences WHERE id = ?", (pref_id,))
            row = cursor.fetchone()
            if not row:
                return None

            pref = self._row_to_preference(row)
            if updates.category is not None:
                pref.category = updates.category
            if updates.value is not None:
                pref.value = updates.value
            if updates.is_explicit is not None:
                pref.is_explicit = updates.is_explicit
            if updates.context_scope is not None:
                pref.context_scope = updates.context_scope
            if updates.confidence is not None:
                pref.confidence = updates.confidence

            pref.updated_at = datetime.utcnow().isoformat()

            cursor.execute("""
                UPDATE user_preferences 
                SET category = ?, value = ?, is_explicit = ?, context_scope = ?, confidence = ?, updated_at = ?
                WHERE id = ?
            """, (
                pref.category.value if isinstance(pref.category, PreferenceCategory) else pref.category,
                pref.value,
                1 if pref.is_explicit else 0,
                pref.context_scope,
                pref.confidence,
                pref.updated_at,
                pref_id
            ))
            conn.commit()
            return pref

    def delete_preference(self, pref_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_preferences WHERE id = ?", (pref_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_by_key(self, key: str, context_scope: Optional[str] = None) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if context_scope:
                cursor.execute("DELETE FROM user_preferences WHERE key = ? AND context_scope = ?", (key, context_scope))
            else:
                cursor.execute("DELETE FROM user_preferences WHERE key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_preferences(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_preferences")
            conn.commit()
            logger.info("All user preferences cleared.")

    def _row_to_preference(self, row: sqlite3.Row) -> UserPreference:
        d = dict(row)
        cat_str = d["category"]
        category = PreferenceCategory(cat_str) if cat_str in PreferenceCategory._value2member_map_ else PreferenceCategory.GENERAL
        return UserPreference(
            id=d["id"],
            category=category,
            key=d["key"],
            value=d["value"],
            is_explicit=bool(d["is_explicit"]),
            source=d["source"],
            confidence=float(d["confidence"] or 1.0),
            context_scope=d["context_scope"],
            created_at=d["created_at"],
            updated_at=d["updated_at"]
        )

    # ==================== DIRECTIVE DETECTION & FORMATTING ====================

    def detect_preference_in_directive(self, user_text: str) -> Optional[UserPreference]:
        """
        Parses explicit preference statements from natural-language user prompts.
        Examples:
        - "Keep your technical explanations concise"
        - "Remember that I prefer detailed explanations"
        - "Prefer Python examples unless I request another language"
        - "Prefer TypeScript for code"
        - "Don't speak notifications when I'm using headphones"
        """
        lower = user_text.lower().strip()

        # 1. Response length / explanation depth
        if any(p in lower for p in ["keep explanations concise", "keep your technical explanations concise", "prefer concise answers", "prefer concise explanations", "be concise"]):
            return self.set_preference(PreferenceCreate(
                category=PreferenceCategory.RESPONSE_LENGTH,
                key="response_length",
                value="concise",
                is_explicit=True,
                source="user_directive"
            ))

        if any(p in lower for p in ["prefer detailed explanations", "give detailed technical explanations", "prefer in-depth answers", "be thorough"]):
            return self.set_preference(PreferenceCreate(
                category=PreferenceCategory.EXPLANATION_DEPTH,
                key="explanation_depth",
                value="detailed",
                is_explicit=True,
                source="user_directive"
            ))

        # 2. Programming Language
        lang_match = re.search(r"prefer\s+([a-zA-Z#+]+)\s+(?:examples|code|programming|by default)", lower)
        if lang_match:
            lang = lang_match.group(1).capitalize()
            return self.set_preference(PreferenceCreate(
                category=PreferenceCategory.PROGRAMMING_LANGUAGE,
                key="preferred_programming_language",
                value=lang,
                is_explicit=True,
                source="user_directive"
            ))

        # 3. Notification behavior
        if "don't speak notifications" in lower or "do not speak notifications" in lower or "silent notifications" in lower:
            return self.set_preference(PreferenceCreate(
                category=PreferenceCategory.NOTIFICATION,
                key="spoken_notifications",
                value="disabled",
                is_explicit=True,
                source="user_directive"
            ))

        return None

    def format_prompt_instructions(self, project_id: Optional[str] = None) -> str:
        """
        Compiles active user preferences into a concise instruction block
        for LLM prompt injection, preserving token limits.
        """
        if not personalization_privacy.is_enabled():
            return ""

        prefs = self.list_preferences(context_scope=project_id)
        if not prefs:
            return ""

        lines = ["[Active User Preferences]"]
        for p in prefs[:6]: # Bounded to top 6 preferences
            if p.key == "response_length" and p.value == "concise":
                lines.append("- Output Style: Keep technical explanations concise and direct.")
            elif p.key == "explanation_depth" and p.value == "detailed":
                lines.append("- Output Style: Provide in-depth explanations and comprehensive architectural rationale.")
            elif p.key == "preferred_programming_language":
                lines.append(f"- Language Preference: Prioritize {p.value} examples unless requested otherwise.")
            else:
                lines.append(f"- {p.key.replace('_', ' ').title()}: {p.value}")

        return "\n".join(lines)

# Global singleton
preference_engine = PreferenceEngine()
