import sqlite3
import json
import logging
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import settings
from app.memory.memory_models import (
    MemoryCategory, MemoryCreate, MemoryUpdate, MemoryItem,
    ProjectCreate, ProjectUpdate, ProjectItem, ConversationSummaryItem, TaskItem
)
from app.memory.semantic_search import semantic_search

logger = logging.getLogger("nova.memory.long_term")

class LongTermMemory:
    """
    Manages structured, persistent knowledge in SQLite with vector indexing.
    Supports user profiles, projects, conversation summaries, tasks, and knowledge.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._migrate_db()
        self._seed_default_projects_if_empty()

    def _get_connection(self) -> sqlite3.Connection:
        from app.database import get_db_connection
        return get_db_connection(self.db_path)

    def _migrate_db(self):
        """Safe non-destructive migration ensuring all v0.3 memory tables exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Structured memories table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        content TEXT NOT NULL,
                        project_id TEXT,
                        tags TEXT DEFAULT '[]',
                        importance REAL DEFAULT 1.0,
                        embedding BLOB,
                        metadata TEXT DEFAULT '{}',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 2. Projects table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        tech_stack TEXT DEFAULT '[]',
                        status TEXT DEFAULT 'active',
                        decisions TEXT DEFAULT '[]',
                        known_issues TEXT DEFAULT '[]',
                        pending_tasks TEXT DEFAULT '[]',
                        recent_updates TEXT DEFAULT '[]',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 3. Conversation summaries table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        key_points TEXT DEFAULT '[]',
                        turn_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 4. Tasks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memory_tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        project_id TEXT,
                        status TEXT DEFAULT 'pending',
                        priority TEXT DEFAULT 'medium',
                        deadline TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Indices for fast retrieval
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_category ON memories (category)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_project ON memories (project_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_summary_session ON conversation_summaries (session_id)")

                conn.commit()
                logger.info("SQLite memory database migrations executed successfully.")
        except Exception as e:
            logger.error(f"Migration error in LongTermMemory: {e}")

    def _seed_default_projects_if_empty(self):
        """Seed initial project record for NOVA so system knows its own architecture."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM projects WHERE id = 'nova'")
                if cursor.fetchone()[0] == 0:
                    nova_proj = {
                        "id": "nova",
                        "name": "NOVA AI Assistant",
                        "description": "Neural Operational Virtual Assistant - JARVIS-inspired desktop AI assistant for Windows.",
                        "tech_stack": json.dumps(["Tauri", "React", "TypeScript", "FastAPI", "Python", "Vite", "Tailwind CSS", "Ollama", "openWakeWord", "Vosk", "Piper TTS"]),
                        "status": "active",
                        "decisions": json.dumps([
                            "Use 100% offline local AI inference with Ollama and Qwen 2.5.",
                            "Implement persistent memory in SQLite with local fastembed ONNX vector search.",
                            "Use Piper TTS for local neural audio synthesis."
                        ]),
                        "known_issues": json.dumps([]),
                        "pending_tasks": json.dumps(["Finalize memory constellation graph", "Optimize wake word latency"]),
                        "recent_updates": json.dumps(["NOVA v0.3 persistent intelligence initialized."])
                    }
                    cursor.execute("""
                        INSERT INTO projects (id, name, description, tech_stack, status, decisions, known_issues, pending_tasks, recent_updates)
                        VALUES (:id, :name, :description, :tech_stack, :status, :decisions, :known_issues, :pending_tasks, :recent_updates)
                    """, nova_proj)
                    conn.commit()

                    # Add default seed memories
                    self.create_memory(MemoryCreate(
                        category=MemoryCategory.PROJECT_MEMORY,
                        content="NOVA desktop application uses Tauri, React, TypeScript, and Vite for its frontend HUD.",
                        project_id="nova",
                        tags=["frontend", "architecture", "tauri"],
                        importance=2.0
                    ))
                    self.create_memory(MemoryCreate(
                        category=MemoryCategory.PROJECT_MEMORY,
                        content="NOVA neural core backend uses FastAPI, Python 3.11, SQLite memory, and Ollama Qwen 2.5 model.",
                        project_id="nova",
                        tags=["backend", "fastapi", "ai"],
                        importance=2.0
                    ))
                    self.create_memory(MemoryCreate(
                        category=MemoryCategory.USER_PROFILE,
                        content="User prefers technical, concise, futuristic sci-fi JARVIS-style communication.",
                        tags=["preference", "persona"],
                        importance=1.5
                    ))
        except Exception as e:
            logger.warning(f"Could not seed default project: {e}")

    # ==================== MEMORY CRUD ====================

    def create_memory(self, memory_data: MemoryCreate) -> Optional[MemoryItem]:
        """Insert new memory item with computed dense vector embedding."""
        try:
            emb_vector = semantic_search.get_embedding(memory_data.content)
            emb_bytes = emb_vector.tobytes() if emb_vector is not None else None
            now_iso = datetime.now().isoformat()

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO memories (category, content, project_id, tags, importance, embedding, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_data.category.value,
                    memory_data.content.strip(),
                    memory_data.project_id.strip() if memory_data.project_id else None,
                    json.dumps(memory_data.tags or []),
                    float(memory_data.importance),
                    emb_bytes,
                    json.dumps(memory_data.metadata or {}),
                    now_iso,
                    now_iso
                ))
                conn.commit()
                mem_id = cursor.lastrowid
                return self.get_memory(mem_id)
        except Exception as e:
            logger.error(f"Failed to create memory: {e}")
            return None

    def get_memory(self, memory_id: int) -> Optional[MemoryItem]:
        """Fetch memory item by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, category, content, project_id, tags, importance, metadata, created_at, updated_at
                    FROM memories WHERE id = ?
                """, (memory_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_memory_item(row)
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None

    def update_memory(self, memory_id: int, update_data: MemoryUpdate) -> Optional[MemoryItem]:
        """Update existing memory fields, recomputing embedding if content changed."""
        try:
            existing = self.get_memory(memory_id)
            if not existing:
                return None

            new_content = update_data.content if update_data.content is not None else existing.content
            new_cat = update_data.category.value if update_data.category is not None else existing.category.value
            new_proj = update_data.project_id if update_data.project_id is not None else existing.project_id
            new_tags = update_data.tags if update_data.tags is not None else existing.tags
            new_imp = update_data.importance if update_data.importance is not None else existing.importance
            new_meta = update_data.metadata if update_data.metadata is not None else existing.metadata
            now_iso = datetime.now().isoformat()

            # Recompute embedding if content was modified
            if update_data.content is not None and update_data.content != existing.content:
                emb_vector = semantic_search.get_embedding(new_content)
                emb_bytes = emb_vector.tobytes() if emb_vector is not None else None
            else:
                emb_bytes = None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                if emb_bytes is not None:
                    cursor.execute("""
                        UPDATE memories
                        SET category = ?, content = ?, project_id = ?, tags = ?, importance = ?, embedding = ?, metadata = ?, updated_at = ?
                        WHERE id = ?
                    """, (new_cat, new_content, new_proj, json.dumps(new_tags), new_imp, emb_bytes, json.dumps(new_meta), now_iso, memory_id))
                else:
                    cursor.execute("""
                        UPDATE memories
                        SET category = ?, content = ?, project_id = ?, tags = ?, importance = ?, metadata = ?, updated_at = ?
                        WHERE id = ?
                    """, (new_cat, new_content, new_proj, json.dumps(new_tags), new_imp, json.dumps(new_meta), now_iso, memory_id))
                conn.commit()
                return self.get_memory(memory_id)
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return None

    def delete_memory(self, memory_id: int) -> bool:
        """Purge memory by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    def list_memories(
        self,
        category: Optional[MemoryCategory] = None,
        project_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MemoryItem]:
        """Query stored memories with category and project filters."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT id, category, content, project_id, tags, importance, metadata, created_at, updated_at FROM memories WHERE 1=1"
                params = []

                if category:
                    query += " AND category = ?"
                    params.append(category.value)
                if project_id:
                    query += " AND project_id = ?"
                    params.append(project_id)

                query += " ORDER BY id DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [self._row_to_memory_item(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list memories: {e}")
            return []

    def search_memories(
        self,
        query: str,
        category: Optional[MemoryCategory] = None,
        project_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.45
    ) -> List[MemoryItem]:
        """Perform semantic vector similarity search with metadata filtering."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                sql = "SELECT id, category, content, project_id, tags, importance, embedding, metadata, created_at, updated_at FROM memories WHERE 1=1"
                params = []

                if category:
                    sql += " AND category = ?"
                    params.append(category.value)
                if project_id:
                    sql += " AND project_id = ?"
                    params.append(project_id)

                cursor.execute(sql, params)
                rows = cursor.fetchall()
                candidates = [dict(r) for r in rows]

            ranked = semantic_search.search_memories(
                query=query,
                memories=candidates,
                threshold=threshold,
                limit=limit
            )

            results: List[MemoryItem] = []
            for item in ranked:
                mem = self._row_to_memory_item(item)
                mem.similarity = item.get("similarity")
                results.append(mem)
            return results
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    def forget_memories(
        self,
        target: str,
        category: Optional[MemoryCategory] = None,
        project_id: Optional[str] = None
    ) -> int:
        """Purge memories matching keyword, phrase, or ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Check if target is an integer ID
                if target.isdigit():
                    cursor.execute("DELETE FROM memories WHERE id = ?", (int(target),))
                    deleted = cursor.rowcount
                    conn.commit()
                    return deleted

                sql = "DELETE FROM memories WHERE (content LIKE ? OR tags LIKE ?)"
                pattern = f"%{target}%"
                params = [pattern, pattern]

                if category:
                    sql += " AND category = ?"
                    params.append(category.value)
                if project_id:
                    sql += " AND project_id = ?"
                    params.append(project_id)

                cursor.execute(sql, params)
                deleted = cursor.rowcount
                conn.commit()
                return deleted
        except Exception as e:
            logger.error(f"Failed to forget memories: {e}")
            return 0

    # ==================== PROJECT CRUD ====================

    def create_project(self, project: ProjectCreate) -> Optional[ProjectItem]:
        try:
            now_iso = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO projects (id, name, description, tech_stack, status, decisions, known_issues, pending_tasks, recent_updates, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project.id.lower().strip(),
                    project.name.strip(),
                    project.description or "",
                    json.dumps(project.tech_stack or []),
                    project.status or "active",
                    json.dumps(project.decisions or []),
                    json.dumps(project.known_issues or []),
                    json.dumps(project.pending_tasks or []),
                    json.dumps(project.recent_updates or []),
                    now_iso,
                    now_iso
                ))
                conn.commit()
                return self.get_project(project.id)
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return None

    def get_project(self, project_id: str) -> Optional[ProjectItem]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id.lower().strip(),))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_project_item(row)
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return None

    def list_projects(self) -> List[ProjectItem]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
                rows = cursor.fetchall()
                return [self._row_to_project_item(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return []

    def update_project(self, project_id: str, update: ProjectUpdate) -> Optional[ProjectItem]:
        try:
            existing = self.get_project(project_id)
            if not existing:
                return None

            now_iso = datetime.now().isoformat()
            new_name = update.name if update.name is not None else existing.name
            new_desc = update.description if update.description is not None else existing.description
            new_stack = update.tech_stack if update.tech_stack is not None else existing.tech_stack
            new_status = update.status if update.status is not None else existing.status
            new_decisions = update.decisions if update.decisions is not None else existing.decisions
            new_issues = update.known_issues if update.known_issues is not None else existing.known_issues
            new_tasks = update.pending_tasks if update.pending_tasks is not None else existing.pending_tasks
            new_updates = update.recent_updates if update.recent_updates is not None else existing.recent_updates

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE projects
                    SET name = ?, description = ?, tech_stack = ?, status = ?, decisions = ?, known_issues = ?, pending_tasks = ?, recent_updates = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    new_name, new_desc, json.dumps(new_stack), new_status,
                    json.dumps(new_decisions), json.dumps(new_issues),
                    json.dumps(new_tasks), json.dumps(new_updates),
                    now_iso, project_id.lower().strip()
                ))
                conn.commit()
                return self.get_project(project_id)
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            return None

    def delete_project(self, project_id: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM projects WHERE id = ?", (project_id.lower().strip(),))
                cursor.execute("DELETE FROM memories WHERE project_id = ?", (project_id.lower().strip(),))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            return False

    # ==================== CONVERSATION SUMMARIES ====================

    def add_summary(self, session_id: str, summary: str, key_points: List[str] = None, turn_count: int = 0) -> int:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO conversation_summaries (session_id, summary, key_points, turn_count)
                    VALUES (?, ?, ?, ?)
                """, (session_id, summary.strip(), json.dumps(key_points or []), turn_count))
                conn.commit()
                return cursor.lastrowid or 0
        except Exception as e:
            logger.error(f"Failed to add summary: {e}")
            return 0

    def get_summaries(self, session_id: Optional[str] = None, limit: int = 10) -> List[ConversationSummaryItem]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if session_id:
                    cursor.execute("""
                        SELECT * FROM conversation_summaries WHERE session_id = ? ORDER BY id DESC LIMIT ?
                    """, (session_id, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM conversation_summaries ORDER BY id DESC LIMIT ?
                    """, (limit,))
                rows = cursor.fetchall()
                items = []
                for r in rows:
                    items.append(ConversationSummaryItem(
                        id=r["id"],
                        session_id=r["session_id"],
                        summary=r["summary"],
                        key_points=json.loads(r["key_points"]) if r["key_points"] else [],
                        turn_count=r["turn_count"],
                        created_at=r["created_at"]
                    ))
                return items
        except Exception as e:
            logger.error(f"Failed to get summaries: {e}")
            return []

    # ==================== STATS ====================

    def get_memory_stats(self) -> Dict[str, Any]:
        """Aggregate counts across memory categories, projects, and summaries."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Total memories
                cursor.execute("SELECT COUNT(*) FROM memories")
                total_memories = cursor.fetchone()[0]

                # Category breakdown
                cursor.execute("SELECT category, COUNT(*) FROM memories GROUP BY category")
                cat_rows = cursor.fetchall()
                categories = {r[0]: r[1] for r in cat_rows}

                # Project count
                cursor.execute("SELECT COUNT(*) FROM projects")
                total_projects = cursor.fetchone()[0]

                # Summaries count
                cursor.execute("SELECT COUNT(*) FROM conversation_summaries")
                total_summaries = cursor.fetchone()[0]

                # Messages count
                cursor.execute("SELECT COUNT(*) FROM messages")
                total_messages = cursor.fetchone()[0]

                return {
                    "total_memories": total_memories,
                    "categories": categories,
                    "total_projects": total_projects,
                    "total_summaries": total_summaries,
                    "total_messages": total_messages,
                    "vector_index_ready": semantic_search.is_embedding_available,
                    "embedding_model": settings.MEMORY_EMBEDDING_MODEL
                }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {
                "total_memories": 0,
                "categories": {},
                "total_projects": 0,
                "total_summaries": 0,
                "total_messages": 0,
                "vector_index_ready": False
            }

    # ==================== HELPERS ====================

    def _row_to_memory_item(self, row: Any) -> MemoryItem:
        d = dict(row)
        tags = json.loads(d["tags"]) if d.get("tags") else []
        meta = json.loads(d["metadata"]) if d.get("metadata") else {}
        return MemoryItem(
            id=d["id"],
            category=MemoryCategory(d["category"]),
            content=d["content"],
            project_id=d.get("project_id"),
            tags=tags,
            importance=float(d.get("importance", 1.0)),
            similarity=d.get("similarity"),
            metadata=meta,
            created_at=str(d.get("created_at")),
            updated_at=str(d.get("updated_at"))
        )

    def _row_to_project_item(self, row: Any) -> ProjectItem:
        d = dict(row)
        return ProjectItem(
            id=d["id"],
            name=d["name"],
            description=d.get("description", ""),
            tech_stack=json.loads(d["tech_stack"]) if d.get("tech_stack") else [],
            status=d.get("status", "active"),
            decisions=json.loads(d["decisions"]) if d.get("decisions") else [],
            known_issues=json.loads(d["known_issues"]) if d.get("known_issues") else [],
            pending_tasks=json.loads(d["pending_tasks"]) if d.get("pending_tasks") else [],
            recent_updates=json.loads(d["recent_updates"]) if d.get("recent_updates") else [],
            created_at=str(d.get("created_at")),
            updated_at=str(d.get("updated_at"))
        )

# Global singleton instance
long_term_memory = LongTermMemory()
LongTermMemoryDB = LongTermMemory
