import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from app.config import settings
from .personalization_schemas import (
    ResolvedContext, ContextResolutionSource
)
from .preference_engine import preference_engine
from .personalization_privacy import personalization_privacy

logger = logging.getLogger("nova.personalization.context")

class ContextResolver:
    """
    Context Resolution Engine following strict prioritization:
    1. Current explicit user instruction.
    2. Explicit project selection.
    3. Reliable active workflow context.
    4. Relevant saved project memory.
    5. Other permitted historical context.

    Strict rules:
    - Never infer an active project solely from weak keyword matches.
    - When context is ambiguous, ask for clarification instead of mixing project data.
    """

    def resolve_context(
        self,
        user_query: str,
        session_id: str = "default",
        explicit_project_id: Optional[str] = None
    ) -> ResolvedContext:
        """
        Synthesizes active context, respecting priority and privacy settings.
        """
        # If personalization is disabled globally, return minimal unpersonalized context
        if not personalization_privacy.is_enabled():
            return ResolvedContext(
                active_project_id=explicit_project_id,
                confidence=1.0,
                resolution_source=ContextResolutionSource.EXPLICIT_SELECTION if explicit_project_id else ContextResolutionSource.HISTORICAL
            )

        lower_q = user_query.lower()

        # -------------------------------------------------------------
        # 1. CURRENT EXPLICIT USER INSTRUCTION
        # -------------------------------------------------------------
        explicit_in_query, conflict = self._detect_explicit_project_in_query(user_query)
        if conflict:
            return ResolvedContext(
                clarification_needed=True,
                clarification_prompt=f"Your query references multiple projects ({', '.join(conflict)}). Which project would you like me to focus on?",
                resolution_source=ContextResolutionSource.AMBIGUOUS
            )

        if explicit_in_query:
            return self._build_context(
                project_id=explicit_in_query,
                source=ContextResolutionSource.EXPLICIT_INSTRUCTION,
                confidence=1.0,
                user_query=user_query,
                session_id=session_id
            )

        # -------------------------------------------------------------
        # 2. EXPLICIT PROJECT SELECTION (from UI/API parameter)
        # -------------------------------------------------------------
        if explicit_project_id:
            return self._build_context(
                project_id=explicit_project_id,
                source=ContextResolutionSource.EXPLICIT_SELECTION,
                confidence=1.0,
                user_query=user_query,
                session_id=session_id
            )

        # -------------------------------------------------------------
        # 3. RELIABLE ACTIVE WORKFLOW CONTEXT
        # -------------------------------------------------------------
        active_wf_proj = self._get_active_workflow_project()
        if active_wf_proj:
            return self._build_context(
                project_id=active_wf_proj,
                source=ContextResolutionSource.ACTIVE_WORKFLOW,
                confidence=0.95,
                user_query=user_query,
                session_id=session_id
            )

        # -------------------------------------------------------------
        # 4. RELEVANT SAVED PROJECT MEMORY
        # -------------------------------------------------------------
        strong_proj_match = self._match_registered_project(user_query)
        if strong_proj_match:
            return self._build_context(
                project_id=strong_proj_match,
                source=ContextResolutionSource.SAVED_MEMORY,
                confidence=0.85,
                user_query=user_query,
                session_id=session_id
            )

        # -------------------------------------------------------------
        # 5. HISTORICAL / GENERAL CONTEXT
        # -------------------------------------------------------------
        return self._build_context(
            project_id=None,
            source=ContextResolutionSource.HISTORICAL,
            confidence=0.5,
            user_query=user_query,
            session_id=session_id
        )

    def _detect_explicit_project_in_query(self, user_query: str) -> Tuple[Optional[str], Optional[List[str]]]:
        """Looks for direct explicit statements like 'for project X', 'in project X'."""
        patterns = [
            r"(?:in|for|on|about)\s+project\s+([a-zA-Z0-9_\-]+)",
            r"(?:in|for|on|about)\s+the\s+([a-zA-Z0-9_\-]+)\s+project",
            r"\bproject\s+([a-zA-Z0-9_\-]+)"
        ]
        found = []
        for pat in patterns:
            matches = re.findall(pat, user_query, flags=re.IGNORECASE)
            for m in matches:
                slug = m.strip().lower()
                if slug not in found:
                    found.append(slug)

        if len(found) > 1:
            return None, found
        elif len(found) == 1:
            return found[0], None
        return None, None

    def _match_registered_project(self, user_query: str) -> Optional[str]:
        """Matches against known registered projects using strong word boundaries, avoiding weak substring matches."""
        try:
            from app.memory.project_memory import project_memory
            projects = project_memory.list_projects()
            lower = user_query.lower()
            for p in projects:
                # Require complete word match
                pattern = rf"\b{re.escape(p.id.lower())}\b|\b{re.escape(p.name.lower())}\b"
                if re.search(pattern, lower):
                    return p.id
        except Exception:
            pass
        return None

    def _get_active_workflow_project(self) -> Optional[str]:
        """Checks if a workflow is actively executing or pending with a known project."""
        try:
            from app.agents.workflow_logger import workflow_logger
            recent = workflow_logger.list_workflows(limit=3)
            for w in recent:
                if w.get("status") in ("RUNNING", "PENDING_APPROVAL") and w.get("project_id"):
                    return w.get("project_id")
        except Exception:
            pass
        return None

    def _build_context(
        self,
        project_id: Optional[str],
        source: ContextResolutionSource,
        confidence: float,
        user_query: str,
        session_id: str
    ) -> ResolvedContext:
        """Assembles rich context sections including memory, tasks, workflows, and preferences."""
        sections = []
        project_name = None
        memories: List[str] = []
        tasks: List[str] = []
        workflows: List[str] = []
        applied_prefs: List[str] = []

        # 1. Project details from v0.3 project memory
        if project_id:
            try:
                from app.memory.project_memory import project_memory
                proj = project_memory.get_project(project_id)
                if proj:
                    project_name = proj.name
                    tasks = proj.pending_tasks
                    proj_summary = f"[Project Context: {proj.name}]\n- Tech Stack: {', '.join(proj.tech_stack) if proj.tech_stack else 'None specified'}\n- Pending Tasks: {len(proj.pending_tasks)}"
                    sections.append(proj_summary)
            except Exception as e:
                logger.debug(f"Could not load project {project_id}: {e}")

        # 2. Semantic Memories
        try:
            from app.memory.long_term_memory import long_term_memory
            found = long_term_memory.search_memories(
                query=user_query,
                project_id=project_id,
                limit=3,
                threshold=settings.MEMORY_SIMILARITY_THRESHOLD
            )
            if found:
                memories = [m.content for m in found]
                sections.append("[Relevant Knowledge]\n" + "\n".join([f"- {m}" for m in memories]))
        except Exception as e:
            logger.debug(f"Semantic memory search error: {e}")

        # 3. Active Preferences
        pref_instructions = preference_engine.format_prompt_instructions(project_id=project_id)
        if pref_instructions:
            sections.append(pref_instructions)
            applied_prefs = [line.strip() for line in pref_instructions.splitlines() if line.startswith("-")]

        # 4. Formatted Instructions
        formatted = "\n\n".join(sections) if sections else ""

        return ResolvedContext(
            active_project_id=project_id,
            project_name=project_name,
            confidence=confidence,
            resolution_source=source,
            relevant_memories=memories,
            relevant_tasks=tasks,
            recent_workflows=workflows,
            applied_preferences=applied_prefs,
            formatted_instructions=formatted
        )

# Global singleton
context_resolver = ContextResolver()
