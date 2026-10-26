# NOVA v0.6 — Agent Orchestration Architecture

## 1. System Overview

NOVA v0.6 introduces **Advanced Agentic Workflows & Multi-Agent Orchestration**, transitioning NOVA from single-turn tool execution into a bounded, autonomous multi-agent operational assistant. 

The architecture is explicitly bounded and designed for offline-first Windows 11 desktop environments, respecting low-power hardware constraints (Intel Core i3-1115G4, 12 GB RAM) by using **logical personas over a shared local Ollama instance** rather than loading multiple heavyweight LLM processes simultaneously.

```
                                  +------------------------------------+
                                  |    USER OBJECTIVE / VOICE INTENT   |
                                  +------------------------------------+
                                                    |
                                                    v
                                  +------------------------------------+
                                  |      AGENT ORCHESTRATOR FACADE     |
                                  +------------------------------------+
                                         /          |          \
                                        v           v           v
                    +-----------------------+ +------------+ +----------------------+
                    | AGENT PLANNER ENGINE  | | SCHEDULER  | | EVENT BUS & WS STREAM|
                    | (Templates & LLM DAG) | | (Max 2 ||) | | (Persistent SQLite)  |
                    +-----------------------+ +------------+ +----------------------+
                                                    |
                                                    v
                                  +------------------------------------+
                                  |      WORKFLOW EXECUTION ENGINE     |
                                  |   (DAG Step Loop, Retries, Pauses) |
                                  +------------------------------------+
                                                    |
                        +---------------------------+---------------------------+
                        |                           |                           |
                        v                           v                           v
              [ READ-ONLY GATES ]        [ CONFIRMATION REQUIRED ]       [ BLOCKED POLICY ]
              (Automatic Progress)       (Human Approval Checkpoint)     (Outright Rejection)
                        |                           |                           |
                        +---------------------------+---------------------------+
                                                    |
                                                    v
                                  +------------------------------------+
                                  |     SPECIALIZED AGENT PERSONAS     |
                                  +------------------------------------+
                                   /       |         |        |       \
                                  v        v         v        v        v
                             RESEARCH  DEVELOPER  SYSTEM    VISION   MEMORY
                                  \        |         |        |       /
                                   v       v         v        v      v
                                  +------------------------------------+
                                  |  v0.4 TOOLS & v0.5 VISION MANAGERS |
                                  +------------------------------------+
                                                    |
                                                    v
                                  +------------------------------------+
                                  |  REFLECTION & VERIFICATION ENGINE  |
                                  | (Hallucination Prevention Reports) |
                                  +------------------------------------+
```

---

## 2. Core Modules (`backend/app/agents/`)

| Module | Responsibility |
|---|---|
| `agent_orchestrator.py` | Central entry point; coordinates planning, execution dispatch, voice intent routing, and status inspection. |
| `agent_planner.py` | Decomposes high-level natural-language requests into structured DAG steps using deterministic templates first, falling back to local Ollama. |
| `agent_scheduler.py` | Validates DAG dependencies, prevents cycles, and limits parallel execution strictly to independent `READ_ONLY` tasks (max 2 parallel). |
| `workflow_manager.py` | Stateful execution loop, DAG step traversal, human approval checkpoint pausing, and timeout management. |
| `agent_registry.py` | Discovers, registers, and tracks operational status (`IDLE`, `BUSY`, `PAUSED`, `ERROR`) of all 5 logical agents. |
| `agent_base.py` | Abstract `BaseAgent` class providing persona prompts, shared local Ollama inference, and bounded reflection hooks. |
| `specialized_agents.py` | Concrete personas: `ResearchAgent`, `DeveloperAgent`, `SystemAgent`, `VisionAgent`, `MemoryAgent`. |
| `agent_permissions.py` | Security gatekeeper enforcing v0.4 permission levels and neutralizing prompt-injection patterns in untrusted inputs. |
| `agent_reflection.py` | Compares tool execution results against expected step goals, enforcing that success claims are backed by verifiable evidence. |
| `workflow_logger.py` | SQLite persistence for `agent_workflows`, `agent_workflow_steps`, `agent_events`, and crash/restart recovery. |
| `agent_events.py` | Audit event bus broadcasting live WebSocket updates to the frontend HUD. |

---

## 3. The Five Specialized Agents

All agents inherit from `BaseAgent` and share the single running Ollama model (`model_manager.active_model`), avoiding redundant GPU/RAM utilization:

### 1. Research Agent (`AgentRole.RESEARCH`)
- **Focus**: Analyzing project documentation, extracting specifications, synthesizing findings, and identifying missing information.
- **Allowed Tools**: `file_read_text`, `folder_list_contents`, `file_get_metadata`, `file_search_name`, `file_search_extension`, `browser_search_web`.
- **Boundaries**: Strictly read-only; never performs state mutations or executes commands.

### 2. Developer Agent (`AgentRole.DEVELOPER`)
- **Focus**: Inspecting code repositories, parsing `package.json` / `pyproject.toml`, evaluating test output, diagnosing bugs, and proposing structural improvements.
- **Allowed Tools**: `file_read_text`, `folder_list_contents`, `file_get_metadata`, `file_search_name`, `file_search_extension`, `file_copy`, `file_move`, `app_open`, `app_detect_installed`.
- **Boundaries**: Never silently modifies code; any write operation requires human confirmation.

### 3. System Agent (`AgentRole.SYSTEM`)
- **Focus**: Monitoring CPU, RAM, disk, battery metrics; launching approved applications; organizing files and folders.
- **Allowed Tools**: `system_cpu_ram`, `system_battery_info`, `system_disk_usage`, `system_network_status`, `system_volume_get`, `system_volume_set`, `system_lock_workstation`, `app_open`, `app_detect_installed`, `file_open_default`, `folder_open_explorer`, `folder_create`, `file_rename`, `file_move`, `file_copy`, `file_read_text`, `folder_list_contents`, `file_get_metadata`, `folder_organize_preview`.
- **Boundaries**: Strictly constrained to registered tool registry; no arbitrary shell execution or raw CMD/PowerShell.

### 4. Vision Agent (`AgentRole.VISION`)
- **Focus**: Visual screen capture, local Windows OCR text extraction, on-screen error diagnosis, active window context correlation.
- **Allowed Tools**: `vision_capture`, `vision_ocr`, `vision_analyze`, `vision_windows`.
- **Boundaries**: Read-only visual understanding; zero hidden continuous video recording; automatic PII/credential redaction.

### 5. Memory Agent (`AgentRole.MEMORY`)
- **Focus**: Retrieving persistent project decisions, historical workflow outcomes, and saving completed workflow summaries to SQLite.
- **Allowed Tools**: `memory_search`, `memory_store`, `memory_summary`, `project_context`.
- **Boundaries**: Preserves project isolation; explicitly redacts sensitive arguments (tokens, passwords, API keys) before storing.

---

## 4. Deterministic Planning & Template Acceleration

To ensure predictable latency on i3 hardware, `AgentPlanner` evaluates deterministic patterns before querying Ollama:

1. **Project Inspection & Tests**: Triggered by queries like *"Inspect my NOVA project and run its tests"*. Decomposes into project context resolution, repository inspection, test config reading, test execution analysis, improvement report synthesis, and memory persistence.
2. **On-Screen Error Analysis**: Triggered by queries like *"Analyze the error on my screen and explain how to fix it"*. Decomposes into visual capture & OCR, memory issue correlation, and technical fix formulation.
3. **Hardware Health Diagnostics**: Triggered by queries like *"Inspect system health and resource consumption"*. Decomposes into CPU/RAM collection, disk allocation query, and synthetic report.
4. **Folder Organization & Maintenance**: Triggered by queries like *"Organize my downloads"*. Decomposes into directory scanning, categorization proposal, and human-approval gated organization preview.

If an objective does not match a deterministic pattern, `AgentPlanner` uses Ollama with strict JSON schemas, constraining the generated plan to a maximum of 12 steps.

---

## 5. Bounded Execution Constraints

- **Maximum Steps**: Hard limit of 12 steps per workflow.
- **Parallelism**: Maximum 2 concurrent read-only tasks. All tasks requiring confirmation or state mutations execute sequentially.
- **Retry Policy**: Maximum 2 retries per eligible step with exponential backoff. Destructive tasks are never automatically retried.
- **Timeouts**: Individual steps default to 45 seconds; overall workflow timeout is configurable (default 300 seconds).
- **Restart Recovery**: If backend crashes or restarts, all running workflows are safely marked `PAUSED`, and pending steps marked `PENDING_APPROVAL`, preventing runaway execution on reboot.
