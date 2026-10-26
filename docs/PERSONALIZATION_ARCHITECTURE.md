# NOVA v0.8 — Personalization & Adaptive Intelligence Architecture

## 1. Architectural Overview

NOVA v0.8 introduces a local, offline-first Adaptive Intelligence and Personalization Engine designed to make NOVA context-aware, personalized, and consistent across sessions without requiring external cloud telemetry or larger language models.

```
                      +---------------------------------------+
                      |       USER DIRECTIVES & VOICE         |
                      |  (Chat, Voice, Desktop UI, Feedback)  |
                      +-------------------+-------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        PERSONALIZATION MANAGER (Facade)                           |
+-----------------------------------------------------------------------------------+
|  1. Preference Engine        - Explicit CRUD, precedence over inferred, conflict |
|                                resolution, directive detection                    |
|  2. Context Resolver         - Multi-tier priority resolution, ambiguity guard,   |
|                                project isolation enforcement                      |
|  3. Knowledge Graph Engine   - SQLite entity-relationship network (8 entity types,|
|                                8 relation types), memory auto-sync                |
|  4. Recommendation Engine    - Evidence-backed suggestions for failed workflows,  |
|                                pending tasks, scheduled checks (non-autonomous)   |
|  5. Feedback Loop Manager    - Records useful/dismiss/correction feedback,        |
|                                prevents repetition of dismissed advice            |
|  6. Privacy & Policy Guard   - Master toggles, zero-cloud enforcement, data wipe  |
+-----------------------------------------------------------------------------------+
       |                       |                       |                     |
       v                       v                       v                     v
+--------------+       +---------------+       +---------------+      +-------------+
|    v0.3      |       |     v0.5      |       |     v0.6      |      |    v0.7     |
|   Memory     |       | Visual/Window |       | Multi-Agent   |      | Automations |
| (FastEmbed)  |       |   (OCR/UI)    |       |  (Workflows)  |      | (Scheduler) |
+--------------+       +---------------+       +---------------+      +-------------+
```

---

## 2. Core Subsystems

### 2.1 Preference Engine (`preference_engine.py`)
- **Explicit vs. Inferred Precedence**: Explicit directives configured through UI or natural language ("Remember that I prefer concise answers") are given high confidence ($1.0$) and cannot be overwritten by inferred patterns.
- **Natural Language Directive Detection**: Regex pattern matching identifies statements such as "I prefer X", "keep explanations concise", or "don't speak notifications", extracting and applying explicit preferences immediately.
- **Conflict Handling**: Detects conflicting directives across same keys and requests clarification or flags contradiction rather than silently oscillating.
- **Prompt Injection**: Injects active user preferences into model system prompts (`chat.py`) before inference, instructing Ollama to adapt response length, explanation depth, and communication tone.

### 2.2 Context Resolver (`context_resolver.py`)
Adheres to strict 5-tier context precedence:
1. **Current Explicit User Instruction**: Direct project keywords or commands in the immediate turn.
2. **Explicit Project Selection**: Project manually selected by user in the UI.
3. **Reliable Active Workflow Context**: Project currently being executed in an active DAG workflow from v0.6.
4. **Relevant Saved Project Memory**: High-similarity semantic hits from v0.3 persistent memory.
5. **Other Permitted Historical Context**: Fallback interaction patterns.

**Ambiguity Guard**: When a query mentions multiple project candidates (e.g., *"compare Nova and HireLens"*), the context resolver sets `clarification_needed = True` and returns a structured clarification prompt asking the user which project context to isolate, preventing cross-project memory contamination.

### 2.3 Intelligent Recommendation Engine (`recommendation_engine.py`)
Generates actionable recommendations with verifiable supporting evidence:
- **Failed Workflows**: Detects recent failures in v0.6 execution records and suggests re-execution or investigation.
- **Unfinished Tasks**: Identifies pending project tasks in memory and suggests prioritization.
- **Approaching Deadlines**: Evaluates v0.7 reminders and alerts on upcoming obligations.
- **Stale Projects**: Recommends project health checks for frequently used repositories lacking recent diagnostics.

**Safety Guarantee**: Recommendations are strictly advisory. They *never* execute actions autonomously; execution requires standard v0.4 permissions and v0.6 approval checkpoints.

### 2.4 User Feedback Loop (`feedback_manager.py`)
Supports positive reinforcement, permanent dismissals, and explicit corrections:
- `useful`: Increases recommendation confidence.
- `dismiss_permanent`: Adds signature to `dismissed_recommendation_hashes`, permanently silencing the advice.
- `preference_correction`: Updates explicit preferences and logs correction history.
- `association_incorrect`: Removes spurious graph relationships.

---

## 3. Context & Reasoning Integration

In `backend/app/api/chat.py`, when a user sends a prompt:
1. `context_resolver.resolve_context(message)` determines project isolation.
2. If `clarification_needed`, NOVA responds directly with the clarification prompt.
3. Relevant project memory is retrieved exclusively from `active_project`.
4. `preference_engine.format_preferences_for_prompt()` generates active style rules.
5. Inferred interaction cues are asynchronously evaluated post-response.

---

## 4. Hardware Optimization

Targeting resource-constrained systems (Intel Core i3, 12 GB RAM, integrated graphics):
- **Zero Additional Models**: Relies on existing local Ollama instance (`qwen3:4b` / `gemma2:2b`).
- **SQLite Single-File Storage**: Non-destructive, zero-latency local queries.
- **Bounded Recommendation Runs**: Limited to $20$ items per sweep to avoid CPU spikes.
- **No Background Thread Stalls**: Database reads and writes are asynchronous or fast indexed queries.
