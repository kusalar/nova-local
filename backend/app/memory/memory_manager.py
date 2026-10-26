import logging
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings
from app.memory.long_term_memory import long_term_memory
from app.memory.project_memory import project_memory, ProjectMemoryManager
from app.memory.memory_extractor import memory_extractor
from app.memory.conversation_summarizer import conversation_summarizer
from app.memory.memory_models import MemoryCategory, MemoryCreate, MemoryItem

logger = logging.getLogger("nova.memory.manager")

class MemoryManager:
    """
    Central memory intelligence coordinator.
    Augments conversation prompts with relevant persistent context,
    manages multi-project isolation, and extracts useful knowledge.
    """

    def __init__(self, db: Optional[Any] = None):
        self.store = db or long_term_memory
        self.projects = ProjectMemoryManager(db=self.store) if db else project_memory
        self.extractor = memory_extractor
        self.summarizer = conversation_summarizer

    def build_augmented_context(
        self,
        user_query: str,
        session_id: str = "default",
        current_project: Optional[str] = None,
        compact: bool = False,
        user_message: Optional[str] = None,
        max_items: int = 4,
    ) -> Tuple[str, Optional[str]]:
        """
        Construct a concise, high-relevance memory context block for model prompt injection.
        Returns: (context_string, detected_project_id)

        compact=True skips embedding search and session summaries so voice turns
        do not compete with Ollama on CPU. user_message/max_items are accepted
        for the voice call-site.
        """
        query = user_query or user_message or ""
        context_sections = []
        
        # 1. Project Detection & Project Intelligence Block
        proj_id = current_project or self.projects.detect_project_in_text(query)
        if proj_id and not compact:
            proj_context = self.projects.get_project_context_string(proj_id)
            if proj_context:
                context_sections.append(f"[Active Project Intelligence]\n{proj_context[:400]}")

        # 2. Memory retrieval
        if compact:
            candidates = self.store.list_memories(limit=12)
            qwords = {w for w in query.lower().split() if len(w) > 3}
            scored = []
            for m in candidates:
                hits = sum(1 for w in qwords if w in (m.content or "").lower())
                if hits:
                    scored.append((hits, m))
            scored.sort(key=lambda x: x[0], reverse=True)
            relevant_memories = [m for _, m in scored[: min(2, max_items)]]
        else:
            relevant_memories = self.store.search_memories(
                query=query,
                project_id=proj_id,
                limit=min(4, max_items),
                threshold=settings.MEMORY_SIMILARITY_THRESHOLD
            )
        if relevant_memories:
            mem_lines = [f"- {(m.content or '')[:180]}" for m in relevant_memories]
            context_sections.append("[Relevant Knowledge & Decisions]\n" + "\n".join(mem_lines))

        # 3. User Preferences (Top 2 general profile memories)
        user_profiles = self.store.list_memories(category=MemoryCategory.USER_PROFILE, limit=2)
        if user_profiles:
            prof_lines = [f"- {(p.content or '')[:160]}" for p in user_profiles]
            context_sections.append("[User Profile Context]\n" + "\n".join(prof_lines))

        # 4. Recent Conversation Summary (skip on compact voice path)
        if not compact:
            summaries = self.store.get_summaries(session_id=session_id, limit=1)
            if summaries:
                context_sections.append(f"[Historical Session Summary]\n{summaries[0].summary[:400]}")

        if not context_sections:
            return "", proj_id

        full_context = "\n\n".join(context_sections)
        return full_context, proj_id

    def process_turn_and_extract(
        self,
        user_query: str,
        session_id: str = "default",
        project_id: Optional[str] = None
    ) -> List[MemoryItem]:
        """
        Analyze conversation turn, extract useful facts, and record in persistent memory.
        """
        extracted = self.extractor.extract_from_text(user_query, detected_project=project_id)
        saved_items = []
        for item in extracted:
            saved = self.store.create_memory(item)
            if saved:
                saved_items.append(saved)
                logger.info(f"Saved persistent memory: [{saved.category.value}] {saved.content}")
        return saved_items

    def handle_explicit_memory_query(self, user_query: str) -> Optional[str]:
        """
        Inspect if query is an explicit memory directive:
        e.g., 'What do you remember about me?', 'What do you know about HireLens?', 'Forget ...'
        """
        lower = user_query.lower().strip()
        
        # Check explicit forget
        directive = self.extractor.parse_explicit_directives(user_query)
        if directive and directive.get("action") == "forget":
            target = directive.get("target", "")
            count = self.store.forget_memories(target)
            return f"I have forgotten {count} memory record(s) matching '{target}'."

        # Check explicit "What do you remember / know"
        if any(lower.startswith(prefix) for prefix in ["what do you remember", "what do you know", "tell me what you remember"]):
            # Check if asking about project
            proj_id = self.projects.detect_project_in_text(user_query)
            if proj_id:
                proj = self.store.get_project(proj_id)
                if proj:
                    parts = [f"Here is what I remember about {proj.name}:"]
                    if proj.tech_stack:
                        parts.append(f"• Tech Stack: {', '.join(proj.tech_stack)}")
                    if proj.status:
                        parts.append(f"• Status: {proj.status}")
                    if proj.decisions:
                        parts.append(f"• Decisions: {'; '.join(proj.decisions)}")
                    if proj.pending_tasks:
                        parts.append(f"• Pending Tasks: {'; '.join(proj.pending_tasks)}")
                    return "\n".join(parts)

            # Check general user profile memories
            mems = self.store.list_memories(limit=10)
            if mems:
                items_str = "\n".join([f"• [{m.category.value}] {m.content}" for m in mems[:5]])
                return f"Here are key facts currently in my neural memory bank:\n{items_str}"
            else:
                return "My memory bank is currently empty. You can tell me to remember facts anytime!"

        return None

# Global singleton
memory_manager = MemoryManager()
