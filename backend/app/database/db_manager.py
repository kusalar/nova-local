import sqlite3
import os
import logging
from typing import Optional, Dict, Any, List, Generator
from contextlib import contextmanager

from app.config import settings

logger = logging.getLogger("nova.database.manager")

class DatabaseManager:
    """
    Centralized database connection, transaction, and integrity manager for NOVA v0.9.
    Enforces SQLite Write-Ahead Logging (WAL), busy timeouts, foreign key constraints,
    short transactions, and corruption detection.
    """

    def __init__(self, default_db_path: Optional[str] = None):
        self.default_db_path = default_db_path or settings.DATABASE_PATH
        self._initialized_paths: set = set()

    def get_connection(self, db_path: Optional[str] = None, timeout: float = 5.0) -> sqlite3.Connection:
        """
        Returns a configured sqlite3.Connection with WAL mode, busy timeout,
        and foreign key enforcement.
        """
        path = db_path or self.default_db_path
        
        # Ensure parent directory exists if path contains directories
        dir_name = os.path.dirname(path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        conn = sqlite3.connect(path, timeout=timeout)
        conn.row_factory = sqlite3.Row

        # Apply PRAGMAs once per connection
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA busy_timeout = 5000;")
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # WAL mode only needs to be set once per database file, but setting is idempotent
            if path not in self._initialized_paths:
                cursor.execute("PRAGMA journal_mode = WAL;")
                cursor.execute("PRAGMA synchronous = NORMAL;")
                self._initialized_paths.add(path)
                logger.debug(f"Configured SQLite WAL mode and PRAGMAs for: {path}")
        except Exception as e:
            logger.warning(f"Failed to set PRAGMAs on {path}: {e}")

        return conn

    @contextmanager
    def transaction(self, db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
        """
        Safe transaction context manager with automatic commit and rollback on error.
        Usage:
            with db_manager.transaction() as conn:
                conn.execute(...)
        """
        conn = self.get_connection(db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
                logger.debug(f"Transaction rolled back due to error: {e}")
            except Exception as rollback_err:
                logger.error(f"Rollback failed: {rollback_err}")
            raise e
        finally:
            conn.close()

    def check_integrity(self, db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes PRAGMA integrity_check and quick_check to detect database corruption.
        """
        path = db_path or self.default_db_path
        if not os.path.exists(path):
            return {"status": "NOT_FOUND", "healthy": False, "messages": ["Database file does not exist."]}

        try:
            conn = self.get_connection(path)
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                rows = cursor.fetchall()
                messages = [row[0] for row in rows]
                is_ok = len(messages) == 1 and messages[0].lower() == "ok"
                return {
                    "status": "HEALTHY" if is_ok else "CORRUPT",
                    "healthy": is_ok,
                    "messages": messages
                }
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Integrity check failed for {path}: {e}")
            return {
                "status": "ERROR",
                "healthy": False,
                "messages": [str(e)]
            }

    def get_database_status(self, db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns comprehensive database statistics (size, tables, row counts, journal mode).
        """
        path = db_path or self.default_db_path
        if not os.path.exists(path):
            return {
                "path": path,
                "exists": False,
                "size_bytes": 0,
                "healthy": False,
                "journal_mode": "unknown",
                "table_counts": {}
            }

        size_bytes = os.path.getsize(path)
        wal_path = f"{path}-wal"
        wal_size_bytes = os.path.getsize(wal_path) if os.path.exists(wal_path) else 0

        integrity = self.check_integrity(path)
        table_counts: Dict[str, int] = {}
        journal_mode = "unknown"

        try:
            conn = self.get_connection(path)
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode;")
                jm_row = cursor.fetchone()
                if jm_row:
                    journal_mode = jm_row[0]

                # Query all user tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                tables = [r[0] for r in cursor.fetchall()]

                for tbl in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM \"{tbl}\";")
                        cnt = cursor.fetchone()[0]
                        table_counts[tbl] = cnt
                    except Exception:
                        table_counts[tbl] = -1
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Error reading database metadata: {e}")

        total_records = sum(c for c in table_counts.values() if c > 0)

        return {
            "path": path,
            "exists": True,
            "size_bytes": size_bytes,
            "wal_size_bytes": wal_size_bytes,
            "total_size_bytes": size_bytes + wal_size_bytes,
            "healthy": integrity.get("healthy", False),
            "integrity_status": integrity.get("status", "UNKNOWN"),
            "journal_mode": journal_mode,
            "tables_count": len(table_counts),
            "total_records": total_records,
            "table_counts": table_counts
        }

    def cleanup_orphaned_records(self, db_path: Optional[str] = None) -> Dict[str, int]:
        """
        Performs safe integrity maintenance and cleans up orphaned records
        where foreign keys or relationships were broken.
        """
        cleaned = {"foreign_key_violations": 0}
        path = db_path or self.default_db_path

        try:
            with self.transaction(path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_key_check;")
                violations = cursor.fetchall()
                cleaned["foreign_key_violations"] = len(violations)
                # If any knowledge relations reference non-existent entities, safely clean
                cursor.execute("""
                    DELETE FROM knowledge_graph_relations 
                    WHERE source_id NOT IN (SELECT id FROM knowledge_graph_entities)
                       OR target_id NOT IN (SELECT id FROM knowledge_graph_entities);
                """)
                cleaned["orphaned_knowledge_relations"] = cursor.rowcount if cursor.rowcount > 0 else 0
        except Exception as e:
            logger.debug(f"Cleanup check note: {e}")

        return cleaned

db_manager = DatabaseManager()

def get_db_connection(db_path: Optional[str] = None, timeout: float = 5.0) -> sqlite3.Connection:
    """Convenience functional access for existing modules."""
    return db_manager.get_connection(db_path=db_path, timeout=timeout)
