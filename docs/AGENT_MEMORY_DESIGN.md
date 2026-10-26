# NOVA v0.6 — Agent Memory & State Persistence Design

## 1. Architectural Overview

NOVA v0.6 integrates directly with the existing v0.3 persistent memory layer (`SQLite`, `fastembed`, `BAAI/bge-small-en-v1.5`, and `project_memory`). Agent workflows do not create isolated memory silos; instead, they enrich the global NOVA knowledge base while maintaining strict project isolation and credential filtering.

```
                           +-------------------------------+
                           |      WORKFLOW EXECUTION       |
                           +-------------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v (Operational State)                         v (Semantic Milestones)
       +-------------------------+                   +-------------------------+
       |   WORKFLOW LOGGER DB    |                   |   LONG-TERM MEMORY DB   |
       |  (Tables: workflows,    |                   |  (Embeddings & Semantic |
       |   steps, events, etc.)  |                   |   Project Associations) |
       +-------------------------+                   +-------------------------+
                    |                                             |
                    +----------------------+----------------------+
                                           |
                                           v
                           +-------------------------------+
                           |     MEMORY AGENT RETRIEVAL    |
                           |  (Context Injection for Next  |
                           |       Workflow Iteration)     |
                           +-------------------------------+
```

---

## 2. Retention Policies: What is Stored vs Excluded

### Retained Information:
1. **High-Level Objective**: The original user prompt and resolved project scope (`project_id`).
2. **Execution Steps & Dependencies**: Chronological DAG steps, assigned agent roles, requested tools, and final step status (`COMPLETED`, `FAILED`, `CANCELLED`).
3. **Verifiable Evidence Items**: Compact outputs from tools (e.g. CPU percentages, disk allocation, test results).
4. **Synthesized Technical Report**: Reflection summary, key findings, and recommended next steps.
5. **Human Approval Records**: Audit trail of who approved or rejected a confirmation-required step and timestamp.

### Strictly Excluded (Never Stored):
1. **Intermediate LLM Streaming Tokens**: Discarded upon step finalization to minimize database bloat.
2. **Credentials and Secrets**: Any field matching passwords, bearer tokens, API keys, private certificates, or `.env` content is scrubbed via `PermissionManager.redact_sensitive_data()`.
3. **Full Raw Screen Buffers**: Ephemeral screenshot files are cleaned up according to v0.5 retention policy; only OCR text summaries and window titles are persisted.

---

## 3. SQLite Database Schema Migrations

The database migration executes safely on startup in `WorkflowLogger._migrate()`, adding five specialized tables to `nova_memory.db`:

### 1. `agent_workflows`
Stores high-level workflow state and lifecycle timestamps:
```sql
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
);
```

### 2. `agent_workflow_steps`
Stores individual DAG task execution records:
```sql
CREATE TABLE IF NOT EXISTS agent_workflow_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,
    step_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    assigned_agent TEXT NOT NULL,
    tool_id TEXT,
    arguments TEXT,
    dependencies TEXT,
    permission_level TEXT NOT NULL,
    expected_output TEXT,
    timeout_seconds INTEGER DEFAULT 45,
    retry_policy TEXT,
    status TEXT NOT NULL,
    result TEXT,
    error TEXT,
    started_at DATETIME,
    completed_at DATETIME,
    reflection TEXT,
    FOREIGN KEY(workflow_id) REFERENCES agent_workflows(workflow_id)
);
```

### 3. `agent_events`
Stores fine-grained audit events emitted by `AgentEventBus`:
```sql
CREATE TABLE IF NOT EXISTS agent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    workflow_id TEXT NOT NULL,
    step_id INTEGER,
    event_type TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent_role TEXT,
    message TEXT NOT NULL,
    payload TEXT,
    FOREIGN KEY(workflow_id) REFERENCES agent_workflows(workflow_id)
);
```

### 4. `workflow_approvals`
Tracks operator confirmation checkpoints:
```sql
CREATE TABLE IF NOT EXISTS workflow_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,
    step_id INTEGER NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT,
    decided_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(workflow_id) REFERENCES agent_workflows(workflow_id)
);
```

### 5. `workflow_summaries`
Maintains concise indexed summaries for fast historical querying:
```sql
CREATE TABLE IF NOT EXISTS workflow_summaries (
    workflow_id TEXT PRIMARY KEY,
    objective TEXT NOT NULL,
    project_id TEXT,
    summary_text TEXT NOT NULL,
    completed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Cross-Workflow Context & Similarity Retrieval

When planning a new workflow for an existing project:
1. `MemoryAgent` queries previous workflow summaries associated with the target `project_id`.
2. Historical decisions, known failure modes, and test commands from past runs are injected into `AgentContext.project_context`.
3. This prevents repeated trial-and-error (e.g. rediscovering test configurations or re-scanning unorganized directories) and ensures persistent continuity across desktop sessions.
