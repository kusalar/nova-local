# NOVA Persistent Intelligence & Memory Architecture (v0.3)

NOVA v0.3 introduces an offline, privacy-first, persistent memory subsystem for the NOVA desktop AI assistant on Windows. Designed to run efficiently on low-power consumer hardware (Intel Core i3, 12 GB RAM, integrated graphics), all embeddings, vector indexes, and heuristics execute 100% locally with zero cloud dependencies.

---

## 1. System Architecture Overview

```
                      +---------------------------------------+
                      |       USER / VOICE INTERACTION        |
                      +---------------------------------------+
                                          |
                   +----------------------+----------------------+
                   |                                             |
                   v                                             v
        [Text / REST / Tauri UI]                     [Vosk Offline Speech STT]
                   |                                             |
                   +----------------------+----------------------+
                                          |
                                          v
                         +---------------------------------+
                         |      NOVA Memory Manager        |
                         +---------------------------------+
                                    |            |
             +----------------------+            +-----------------------+
             |                                                           |
             v                                                           v
  [1. Context Augmentation]                                  [2. Autonomous Extraction]
  - Project Scope Detection                                   - Tech Stacks & Decisions
  - Dense Vector Semantic Search                              - User Preferences & Profile
  - TF-IDF Lexical Fallback                                   - Task Deadlines & Reminders
  - Recent Conversation Summaries                             - Security Filter & Redaction
             |                                                           |
             v                                                           v
   +-------------------+                                       +-------------------+
   | Enriched System   |                                       | Local SQLite      |
   | Prompt to Ollama  |                                       | nova_memory.db    |
   +-------------------+                                       +-------------------+
```

---

## 2. Memory Categories

NOVA v0.3 manages five structured memory categories:

1. **User Profile (`user_profile`)**
   - User interaction styles, preferences, preferred programming languages, tools, and habits.
2. **Project Intelligence (`project_memory`)**
   - Autonomous knowledge bases for specific software projects (e.g. `nova`, `hirelens`).
   - Tracks project name, description, tech stack, architecture decisions, known issues, and pending tasks.
   - **Project Isolation**: Enforces strict boundaries so details from one project never pollute another.
3. **Conversation Memory (`conversation_memory`)**
   - Session summaries, milestones, and high-level context blocks generated across turns.
4. **Task Memory (`task_memory`)**
   - Actionable deliverables, pending tasks, and completion states.
5. **Knowledge Memory (`knowledge_memory`)**
   - Explicitly retained facts, notes, and technical references.

---

## 3. Storage & Non-Destructive Database Schema

Persistent state is maintained in `nova_memory.db` using SQLite with WAL mode. Existing tables (`messages`) from v0.1 and v0.2 are preserved without data loss.

### New Schema Tables

```sql
-- 1. Structured Knowledge Nodes with BLOB Embeddings
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
);

-- 2. Multi-Project Knowledge Workspaces
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
);

-- 3. Conversation Summaries
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_points TEXT DEFAULT '[]',
    decisions TEXT DEFAULT '[]',
    turn_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tasks and Deadlines
CREATE TABLE IF NOT EXISTS memory_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    deadline TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Fast Indexing
CREATE INDEX IF NOT EXISTS idx_mem_category ON memories (category);
CREATE INDEX IF NOT EXISTS idx_mem_project ON memories (project_id);
CREATE INDEX IF NOT EXISTS idx_summary_session ON conversation_summaries (session_id);
```

---

## 4. Semantic Search & Embeddings

- **Primary Vector Engine**: `fastembed` with `BAAI/bge-small-en-v1.5` (~30MB ONNX Runtime model on CPU). Generates 384-dimensional dense vectors with cosine similarity matching in sub-15ms.
- **Graceful Lexical Fallback**: If ONNX embedding dependencies fail, the engine automatically falls back to `scikit-learn` TF-IDF cosine similarity and substring word-token matching.
- **Context Injection Limit**: The top 4 most relevant memories and top 2 user profile entries are formatted into a concise block, avoiding token exhaustion in local Ollama contexts.

---

## 5. Security & Sensitive Information Guardrails

`MemoryExtractor` inspects incoming conversational turns and proactively prevents credentials from entering memory:
- Regex redaction of OpenAI keys (`sk-...`), GitHub personal access tokens (`ghp_...`), JWT tokens, Bearer headers, and plain-text passwords.
- Refuses to store credentials into `nova_memory.db`.

---

## 6. Memory REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/memory` | List memories with category, project, and limit filters |
| `GET` | `/api/memory/stats` | Aggregated memory counts, project counts, and embedding model info |
| `GET` | `/api/memory/search?q={query}` | Perform semantic retrieval against stored knowledge |
| `GET` | `/api/memory/projects` | List all tracked project workspaces |
| `GET` | `/api/memory/projects/{id}` | Retrieve deep project intelligence (tech stack, decisions, tasks) |
| `POST` | `/api/memory` | Create a new memory fact |
| `PATCH` | `/api/memory/{id}` | Update an existing memory item |
| `DELETE` | `/api/memory/{id}` | Permanently delete a memory node |
| `POST` | `/api/memory/extract` | Auto-extract facts, tech stacks, and tasks from unstructured text |
| `POST` | `/api/memory/summarize` | Summarize a session transcript |
| `POST` | `/api/memory/forget` | Forget or delete specific memories by query or keyword |
