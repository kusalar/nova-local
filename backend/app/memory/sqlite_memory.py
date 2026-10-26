import sqlite3
from typing import List, Dict, Any, Optional
import os
import logging
from app.config import settings

logger = logging.getLogger("nova.memory")

class SQLiteMemory:
    """Manages persistent SQLite memory bank for conversations and events."""

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
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        model TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT NOT NULL,
                        event TEXT NOT NULL,
                        metadata TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing SQLite memory: {e}")

    def add_message(self, role: str, content: str, session_id: str = "default", model: Optional[str] = None) -> int:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO messages (session_id, role, content, model) VALUES (?, ?, ?, ?)",
                    (session_id, role, content, model)
                )
                conn.commit()
                return cursor.lastrowid or 0
        except Exception as e:
            logger.error(f"Failed to add message to memory: {e}")
            return -1

    def get_messages(self, session_id: str = "default", limit: int = 50) -> List[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, session_id, role, content, model, timestamp 
                    FROM messages 
                    WHERE session_id = ? 
                    ORDER BY id ASC 
                    LIMIT ?
                    """,
                    (session_id, limit)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to read messages: {e}")
            return []

    def clear_session(self, session_id: str = "default") -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM messages")
                total_messages = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM messages WHERE role = 'user'")
                user_turns = cursor.fetchone()[0]

                # Check memories table if created
                try:
                    cursor.execute("SELECT COUNT(*) FROM memories")
                    total_memories = cursor.fetchone()[0]
                except Exception:
                    total_memories = 0

                try:
                    cursor.execute("SELECT COUNT(*) FROM projects")
                    total_projects = cursor.fetchone()[0]
                except Exception:
                    total_projects = 0
                
                return {
                    "total_messages": total_messages,
                    "session_turns": user_turns,
                    "total_memories": total_memories,
                    "total_projects": total_projects,
                    "db_path": self.db_path
                }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"total_messages": 0, "session_turns": 0, "total_memories": 0, "total_projects": 0, "db_path": self.db_path}

memory_bank = SQLiteMemory()
