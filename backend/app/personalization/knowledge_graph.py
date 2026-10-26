import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings
from .personalization_schemas import (
    GraphEntity, GraphRelation, EntityType, RelationType, KnowledgeGraphView
)

logger = logging.getLogger("nova.personalization.graph")

class PersonalKnowledgeGraph:
    """
    Lightweight local relationship graph stored in SQLite.
    Models entities (Projects, Technologies, Tasks, Decisions, Workflows, Preferences)
    and edges (USES, HAS_TASK, HAS_DECISION, BELONGS_TO, REFERENCES, APPLIES_TO).
    Preserves strict project isolation and tracks confidence & provenance.
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
                    CREATE TABLE IF NOT EXISTS knowledge_graph_entities (
                        id TEXT PRIMARY KEY,
                        entity_type TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        metadata TEXT DEFAULT '{}',
                        project_id TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_graph_relations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_id TEXT NOT NULL,
                        relation_type TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        source TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(source_id, relation_type, target_id)
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_src ON knowledge_graph_relations(source_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_tgt ON knowledge_graph_relations(target_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_proj ON knowledge_graph_entities(project_id)")
                conn.commit()
                logger.info("PersonalKnowledgeGraph tables initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing Knowledge Graph tables: {e}")

    # ==================== ENTITIES ====================

    def add_entity(self, entity: GraphEntity) -> GraphEntity:
        now_iso = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge_graph_entities (
                    id, entity_type, name, description, metadata, project_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity.id,
                entity.entity_type.value if isinstance(entity.entity_type, EntityType) else entity.entity_type,
                entity.name,
                entity.description,
                json.dumps(entity.metadata or {}),
                entity.project_id,
                entity.created_at or now_iso,
                now_iso
            ))
            conn.commit()
            return entity

    def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_graph_entities WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_entity(row)

    def list_entities(
        self,
        entity_type: Optional[EntityType] = None,
        project_id: Optional[str] = None,
        include_global: bool = False
    ) -> List[GraphEntity]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM knowledge_graph_entities WHERE 1=1"
            params: List[Any] = []

            if entity_type:
                query += " AND entity_type = ?"
                params.append(entity_type.value if isinstance(entity_type, EntityType) else entity_type)
            if project_id:
                if include_global:
                    query += " AND (project_id = ? OR project_id IS NULL)"
                else:
                    query += " AND project_id = ?"
                params.append(project_id)

            query += " ORDER BY entity_type ASC, name ASC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_entity(r) for r in rows]

    def delete_entity(self, entity_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_graph_relations WHERE source_id = ? OR target_id = ?", (entity_id, entity_id))
            cursor.execute("DELETE FROM knowledge_graph_entities WHERE id = ?", (entity_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== RELATIONS ====================

    def add_relation(
        self,
        source_id: str,
        relation_type: RelationType,
        target_id: str,
        confidence: float = 1.0,
        source: str = "project_memory"
    ) -> GraphRelation:
        now_iso = datetime.utcnow().isoformat()
        rel_str = relation_type.value if isinstance(relation_type, RelationType) else relation_type
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge_graph_relations (
                    source_id, relation_type, target_id, confidence, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (source_id, rel_str, target_id, confidence, source, now_iso))
            conn.commit()
            rid = cursor.lastrowid or 0
            return GraphRelation(
                id=rid,
                source_id=source_id,
                relation_type=relation_type,
                target_id=target_id,
                confidence=confidence,
                source=source,
                created_at=now_iso
            )

    def delete_relation(self, relation_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_graph_relations WHERE id = ?", (relation_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_relations(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relation_type: Optional[RelationType] = None
    ) -> List[GraphRelation]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM knowledge_graph_relations WHERE 1=1"
            params: List[Any] = []

            if source_id:
                query += " AND source_id = ?"
                params.append(source_id)
            if target_id:
                query += " AND target_id = ?"
                params.append(target_id)
            if relation_type:
                query += " AND relation_type = ?"
                params.append(relation_type.value if isinstance(relation_type, RelationType) else relation_type)

            query += " ORDER BY id DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_relation(r) for r in rows]

    def get_entity_subgraph(self, entity_id: str) -> Dict[str, Any]:
        """Returns entity, its incoming/outgoing relations, and connected entities."""
        entity = self.get_entity(entity_id)
        if not entity:
            return {"entity": None, "relations": [], "connected_entities": []}

        outgoing = self.list_relations(source_id=entity_id)
        incoming = self.list_relations(target_id=entity_id)
        all_rels = outgoing + incoming

        connected_ids = set()
        for r in outgoing:
            connected_ids.add(r.target_id)
        for r in incoming:
            connected_ids.add(r.source_id)

        connected_entities = []
        for cid in connected_ids:
            ce = self.get_entity(cid)
            if ce:
                connected_entities.append(ce)

        return {
            "entity": entity,
            "outgoing_relations": outgoing,
            "incoming_relations": incoming,
            "connected_entities": connected_entities
        }

    def get_full_graph_view(self, project_id: Optional[str] = None) -> KnowledgeGraphView:
        entities = self.list_entities(project_id=project_id)
        entity_ids = {e.id for e in entities}
        all_rels = self.list_relations()
        filtered_rels = [r for r in all_rels if r.source_id in entity_ids or r.target_id in entity_ids] if project_id else all_rels

        return KnowledgeGraphView(
            entities=entities,
            relations=filtered_rels,
            total_entities=len(entities),
            total_relations=len(filtered_rels)
        )

    def sync_from_existing_memory(self):
        """
        Populates graph non-destructively from v0.3 project memory,
        v0.6 workflows, and v0.7 automations without duplicating facts.
        """
        try:
            from app.memory.project_memory import project_memory
            projects = project_memory.list_projects()
            for p in projects:
                proj_entity_id = f"project:{p.id}"
                self.add_entity(GraphEntity(
                    id=proj_entity_id,
                    entity_type=EntityType.PROJECT,
                    name=p.name,
                    description=p.description or "",
                    project_id=p.id
                ))

                # Tech stack
                for tech in p.tech_stack:
                    tech_id = f"tech:{tech.lower().replace(' ', '_')}"
                    self.add_entity(GraphEntity(
                        id=tech_id,
                        entity_type=EntityType.TECHNOLOGY,
                        name=tech
                    ))
                    self.add_relation(proj_entity_id, RelationType.USES, tech_id, confidence=1.0, source="project_memory")

                # Pending tasks
                for idx, task_text in enumerate(p.pending_tasks):
                    task_id = f"task:{p.id}_{idx}"
                    self.add_entity(GraphEntity(
                        id=task_id,
                        entity_type=EntityType.TASK,
                        name=task_text[:60],
                        description=task_text,
                        project_id=p.id
                    ))
                    self.add_relation(proj_entity_id, RelationType.HAS_TASK, task_id, confidence=1.0, source="project_memory")

                # Decisions
                for idx, dec_text in enumerate(p.decisions):
                    dec_id = f"decision:{p.id}_{idx}"
                    self.add_entity(GraphEntity(
                        id=dec_id,
                        entity_type=EntityType.DECISION,
                        name=dec_text[:60],
                        description=dec_text,
                        project_id=p.id
                    ))
                    self.add_relation(proj_entity_id, RelationType.HAS_DECISION, dec_id, confidence=1.0, source="project_memory")

            logger.info("Knowledge Graph successfully synchronized with project memory.")
        except Exception as e:
            logger.error(f"Error synchronizing Knowledge Graph: {e}")

    def clear_graph(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_graph_relations")
            cursor.execute("DELETE FROM knowledge_graph_entities")
            conn.commit()
            logger.info("Knowledge Graph wiped.")

    def _row_to_entity(self, row: sqlite3.Row) -> GraphEntity:
        d = dict(row)
        etype_str = d["entity_type"]
        etype = EntityType(etype_str) if etype_str in EntityType._value2member_map_ else EntityType.PROJECT
        return GraphEntity(
            id=d["id"],
            entity_type=etype,
            name=d["name"],
            description=d["description"] or "",
            metadata=json.loads(d["metadata"]) if d["metadata"] else {},
            project_id=d["project_id"],
            created_at=d["created_at"],
            updated_at=d["updated_at"]
        )

    def _row_to_relation(self, row: sqlite3.Row) -> GraphRelation:
        d = dict(row)
        rtype_str = d["relation_type"]
        rtype = RelationType(rtype_str) if rtype_str in RelationType._value2member_map_ else RelationType.RELATES_TO
        return GraphRelation(
            id=d["id"],
            source_id=d["source_id"],
            relation_type=rtype,
            target_id=d["target_id"],
            confidence=float(d["confidence"] or 1.0),
            source=d["source"],
            created_at=d["created_at"]
        )

# Global singleton
knowledge_graph = PersonalKnowledgeGraph()
