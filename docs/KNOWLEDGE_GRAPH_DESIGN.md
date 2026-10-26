# NOVA v0.8 — Personal Knowledge Graph Design

## 1. Overview

The Personal Knowledge Graph in NOVA v0.8 is a lightweight, local entity-relationship network embedded directly into SQLite (`nova_memory.db`). It avoids the heavy memory overhead and external network requirements of graph databases (like Neo4j or ArangoDB) while providing rich relational querying between user projects, technologies, decisions, and workflows.

---

## 2. SQLite Schema Design

### 2.1 Table: `knowledge_graph_entities`
```sql
CREATE TABLE IF NOT EXISTS knowledge_graph_entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    project_id TEXT,
    properties TEXT,
    confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_kg_entities_type ON knowledge_graph_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_kg_entities_proj ON knowledge_graph_entities(project_id);
```

### 2.2 Table: `knowledge_graph_relations`
```sql
CREATE TABLE IF NOT EXISTS knowledge_graph_relations (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    project_id TEXT,
    confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_id) REFERENCES knowledge_graph_entities(id) ON DELETE CASCADE,
    FOREIGN KEY(target_id) REFERENCES knowledge_graph_entities(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_kg_rel_source ON knowledge_graph_relations(source_id);
CREATE INDEX IF NOT EXISTS idx_kg_rel_target ON knowledge_graph_relations(target_id);
CREATE INDEX IF NOT EXISTS idx_kg_rel_proj ON knowledge_graph_relations(project_id);
CREATE INDEX IF NOT EXISTS idx_kg_rel_type ON knowledge_graph_relations(relation_type);
```

---

## 3. Entity & Relation Taxonomy

### Supported Entity Types
1. **`project`**: Workspace repositories and top-level projects (e.g., `Nova`, `HireLens`).
2. **`technology`**: Frameworks, runtimes, languages, and tools (e.g., `FastAPI`, `React`, `SQLite`).
3. **`task`**: High-level development goals, pending features, or bug fixes.
4. **`decision`**: Architectural decisions, patterns, or choices agreed upon during chat sessions.
5. **`document`**: Specification docs, design records, or guidelines.
6. **`workflow`**: Multi-agent DAG workflows defined in v0.6.
7. **`preference`**: Inferred or explicit communication and interaction preferences.
8. **`knowledge_item`**: Curated system notes or memory snippets.

### Supported Relation Types
- `USES`: e.g. `(Nova) --[USES]--> (FastAPI)`
- `HAS_TASK`: e.g. `(Nova) --[HAS_TASK]--> (Implement Personalization)`
- `HAS_DECISION`: e.g. `(Nova) --[HAS_DECISION]--> (Use SQLite over Neo4j)`
- `BELONGS_TO`: e.g. `(Workflow: Test Suite) --[BELONGS_TO]--> (Nova)`
- `REFERENCES`: e.g. `(Doc: Architecture) --[REFERENCES]--> (Nova)`
- `APPLIES_TO`: e.g. `(Preference: Concise Answers) --[APPLIES_TO]--> (Global)`
- `DEPENDS_ON`: e.g. `(Task: Frontend UI) --[DEPENDS_ON]--> (Task: REST API)`
- `RELATED_TO`: e.g. `(Technology: Vite) --[RELATED_TO]--> (Technology: React)`

---

## 4. Deduplication & Idempotency

Entities and relations generate deterministic keys to prevent duplicates:
- Entity ID format: `{entity_type}:{normalized_name}:{project_id or 'global'}`
- Relation ID format: `{source_id}->{relation_type}->{target_id}`

Re-registering an entity with identical properties updates the timestamp and merges attributes rather than creating duplicate entries.

---

## 5. Memory Synchronization

`KnowledgeGraphEngine.sync_with_memory_records()` scans persistent SQLite memories from v0.3:
- Creates `project` nodes for each distinct project tag.
- Extracts recognized technologies and architecture decisions.
- Establishes `USES` and `HAS_DECISION` relationships automatically.
- Retains project isolation boundaries by scoping `project_id` attributes on all created entities.
