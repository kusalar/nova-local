import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.memory.memory_models import MemoryCategory, MemoryCreate
from app.memory.project_memory import project_memory

logger = logging.getLogger("nova.memory.extractor")

class MemoryExtractor:
    """
    Extracts structured memories, projects, preferences, and tasks from conversation turns.
    Includes security filters against credentials, passwords, and API keys.
    """

    # Regex patterns for sensitive credentials
    SENSITIVE_PATTERNS = [
        re.compile(r"(?i)(password|passwd|pwd)[\s:=]+([^\s,;]+)"),
        re.compile(r"(?i)(api[_-]?key|secret|token|bearer)[\s:=]+([^\s,;]{8,})"),
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),          # OpenAI style keys
        re.compile(r"ghp_[a-zA-Z0-9]{20,}"),         # GitHub personal access tokens
        re.compile(r"ey[a-zA-Z0-9_-]{15,}\.ey[a-zA-Z0-9_-]{15,}"), # JWT tokens
        re.compile(r"(?i)authorization:\s*bearer\s+[a-zA-Z0-9_\-\.]+"),
    ]

    # Explicit instruction patterns
    EXPLICIT_REMEMBER_PATTERNS = [
        re.compile(r"(?i)^(?:hey\s+nova,?\s*)?remember\s+(?:that\s+)?(.+)$"),
        re.compile(r"(?i)^(?:hey\s+nova,?\s*)?save\s+(?:this\s+)?(?:as\s+a\s+)?(?:project\s+detail|decision|note)?:?\s*(.+)$"),
        re.compile(r"(?i)^(?:hey\s+nova,?\s*)?please\s+remember\s+(.+)$"),
        re.compile(r"(?i)^(?:hey\s+nova,?\s*)?don'?t\s+forget\s+(?:that\s+)?(.+)$"),
    ]

    FORGET_PATTERNS = [
        re.compile(r"(?i)^(?:hey\s+nova,?\s*)?forget\s+(?:about\s+)?(.+)$"),
        re.compile(r"(?i)^(?:hey\s+nova,?\s*)?delete\s+(?:the\s+)?memory\s+(?:about\s+)?(.+)$"),
        re.compile(r"(?i)^(?:hey\s+nova,?\s*)?purge\s+(?:the\s+)?memory\s+(?:of\s+)?(.+)$"),
    ]

    # Project tech stack extraction pattern
    # e.g. "I'm building HireLens AI using FastAPI and React"
    PROJECT_BUILD_PATTERN = re.compile(
        r"(?i)(?:i(?:'m| am)\s+(?:building|developing|working on)|my project is)\s+([A-Z0-9a-z\s_-]+?)\s+(?:using|with)\s+([A-Z0-9a-z\s,_\-+/]+)"
    )

    def contains_sensitive_info(self, text: str) -> bool:
        """Check if text contains passwords, API keys, or private tokens."""
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def sanitize_text(self, text: str) -> str:
        """Redact sensitive credentials if found."""
        sanitized = text
        for pattern in self.SENSITIVE_PATTERNS:
            sanitized = pattern.sub("[REDACTED_CREDENTIAL]", sanitized)
        return sanitized

    def parse_explicit_directives(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect direct commands to remember or forget."""
        return self.parse_explicit_directive(text)

    def parse_explicit_directive(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect direct commands to remember or forget."""
        trimmed = text.strip()

        # Check forget
        for pat in self.FORGET_PATTERNS:
            m = pat.match(trimmed)
            if m:
                target = m.group(1).strip().rstrip(".?!")
                return {"action": "forget", "target": target}

        # Check remember
        for pat in self.EXPLICIT_REMEMBER_PATTERNS:
            m = pat.match(trimmed)
            if m:
                fact = m.group(1).strip().rstrip(".?!")
                return {"action": "remember", "content": fact}

        return None

    def extract_from_text(
        self,
        text: str,
        detected_project: Optional[str] = None
    ) -> List[MemoryCreate]:
        """
        Extract meaningful memory items using local rules and heuristics.
        Does not store passwords or API keys.
        """
        if self.contains_sensitive_info(text):
            logger.warning("Potential sensitive credentials detected in text. Redacting before extraction.")
            text = self.sanitize_text(text)

        memories: List[MemoryCreate] = []
        lower = text.lower()

        # 1. Explicit Directives
        directive = self.parse_explicit_directives(text)
        if directive and directive.get("action") == "remember":
            content = directive.get("content", "").strip()
            if content:
                # Determine category
                cat = MemoryCategory.KNOWLEDGE_MEMORY
                proj = detected_project or project_memory.detect_project_in_text(content)
                if proj:
                    cat = MemoryCategory.PROJECT_MEMORY
                elif any(p in lower for p in ["i like", "i prefer", "my favorite", "i code in", "i use", "my name"]):
                    cat = MemoryCategory.USER_PROFILE

                memories.append(MemoryCreate(
                    category=cat,
                    content=content,
                    project_id=proj,
                    importance=2.5,
                    tags=["explicit", proj or "general"]
                ))
                return memories

        # 2. Project Creation / Tech Stack Extraction
        # e.g., "I'm building HireLens AI using FastAPI and React"
        m_proj = self.PROJECT_BUILD_PATTERN.search(text)
        if m_proj:
            proj_name = m_proj.group(1).strip()
            tech_str = m_proj.group(2).strip().rstrip(".?!")
            tech_tokens = [t.strip() for t in re.split(r"[,/]|(?:\s+and\s+)", tech_str) if t.strip()]

            # Create or update project record
            proj_item = project_memory.get_or_create_project(proj_name, tech_tokens)
            memories.append(MemoryCreate(
                category=MemoryCategory.PROJECT_MEMORY,
                content=f"{proj_item.name} uses {', '.join(tech_tokens)}.",
                project_id=proj_item.id,
                tags=["project", "tech_stack", proj_item.id],
                importance=2.0
            ))

        # 3. User Preferences Extraction
        pref_matches = re.findall(
            r"(?i)(?:i prefer|i always use|my preferred|i like)\s+([a-zA-Z0-9\s_-]+)",
            text
        )
        for pref in pref_matches:
            pref_clean = pref.strip().rstrip(".?!")
            if len(pref_clean) > 3 and not any(w in pref_clean for w in ["to", "that", "this"]):
                memories.append(MemoryCreate(
                    category=MemoryCategory.USER_PROFILE,
                    content=f"User preference: prefers {pref_clean}.",
                    tags=["preference", "user_profile"],
                    importance=1.5
                ))

        # 4. Task / Deadline Detection
        task_match = re.search(r"(?i)(?:i need to|i have to|task:?)\s+([a-zA-Z0-9\s_-]+?)(?:\s+by\s+([a-zA-Z0-9\s:]+))?[.!?]?$", text)
        if task_match:
            task_desc = task_match.group(1).strip()
            deadline = task_match.group(2).strip() if task_match.group(2) else None
            if len(task_desc) > 4:
                content = f"Pending task: {task_desc}" + (f" (Deadline: {deadline})" if deadline else "")
                memories.append(MemoryCreate(
                    category=MemoryCategory.TASK_MEMORY,
                    content=content,
                    project_id=detected_project,
                    tags=["task", detected_project or "personal"],
                    importance=1.8,
                    metadata={"deadline": deadline} if deadline else {}
                ))

        return memories

# Global singleton
memory_extractor = MemoryExtractor()
