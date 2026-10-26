import logging
from typing import List, Dict, Any, Optional
from app.memory.long_term_memory import long_term_memory
from app.memory.memory_models import ProjectItem, ProjectCreate, ProjectUpdate, MemoryCategory, MemoryCreate

logger = logging.getLogger("nova.memory.project")

class ProjectMemoryManager:
    """
    Project-aware intelligence engine.
    Ensures knowledge, decisions, and tasks remain strictly isolated per project.
    """

    def __init__(self, db: Optional[Any] = None):
        self.memory_store = db or long_term_memory

    def create_project(self, project_data: ProjectCreate) -> ProjectItem:
        """Create new project entry."""
        return self.memory_store.create_project(project_data)

    def get_or_create_project(self, project_name: str, tech_stack: Optional[List[str]] = None) -> ProjectItem:
        """Fetch existing project by name or slug, or initialize new project record."""
        slug = project_name.lower().replace(" ", "-").replace("_", "-").strip()
        existing = self.memory_store.get_project(slug)
        if existing:
            if tech_stack:
                merged_stack = list(set(existing.tech_stack + tech_stack))
                self.memory_store.update_project(slug, ProjectUpdate(tech_stack=merged_stack))
                return self.memory_store.get_project(slug)
            return existing

        new_proj = self.memory_store.create_project(ProjectCreate(
            id=slug,
            name=project_name.strip(),
            description=f"Project record for {project_name.strip()}",
            tech_stack=tech_stack or []
        ))
        return new_proj

    def add_project_decision(self, project_id: str, decision: str) -> bool:
        """Record an important architectural or technical decision for a project."""
        proj = self.memory_store.get_project(project_id)
        if not proj:
            return False

        decisions = proj.decisions.copy()
        if decision not in decisions:
            decisions.append(decision)
            self.memory_store.update_project(project_id, ProjectUpdate(decisions=decisions))
            
            # Also store as searchable memory item
            self.memory_store.create_memory(MemoryCreate(
                category=MemoryCategory.PROJECT_MEMORY,
                content=f"Decision for {proj.name}: {decision}",
                project_id=project_id,
                tags=["decision", proj.id],
                importance=2.0
            ))
            return True
        return False

    def add_project_tech_stack(self, project_id: str, technologies: List[str]) -> bool:
        """Append frameworks or tools to project stack."""
        proj = self.memory_store.get_project(project_id)
        if not proj:
            return False

        current = set(proj.tech_stack)
        new_techs = [t for t in technologies if t not in current]
        if new_techs:
            updated_stack = proj.tech_stack + new_techs
            self.memory_store.update_project(project_id, ProjectUpdate(tech_stack=updated_stack))
            
            self.memory_store.create_memory(MemoryCreate(
                category=MemoryCategory.PROJECT_MEMORY,
                content=f"{proj.name} uses {', '.join(technologies)}.",
                project_id=project_id,
                tags=["tech_stack", proj.id],
                importance=1.5
            ))
            return True
        return False

    def add_pending_task(self, project_id: str, task: str) -> bool:
        proj = self.memory_store.get_project(project_id)
        if not proj:
            return False

        tasks = proj.pending_tasks.copy()
        if task not in tasks:
            tasks.append(task)
            self.memory_store.update_project(project_id, ProjectUpdate(pending_tasks=tasks))
            return True
        return False

    def get_project_context_string(self, project_id: str) -> str:
        """Construct structured intelligence block for model prompt injection."""
        proj = self.memory_store.get_project(project_id)
        if not proj:
            return ""

        parts = [f"PROJECT '{proj.name.upper()}':"]
        if proj.description:
            parts.append(f"- Description: {proj.description}")
        if proj.tech_stack:
            parts.append(f"- Tech Stack: {', '.join(proj.tech_stack)}")
        if proj.status:
            parts.append(f"- Status: {proj.status}")
        if proj.decisions:
            parts.append(f"- Key Decisions: {'; '.join(proj.decisions[:4])}")
        if proj.pending_tasks:
            parts.append(f"- Pending Tasks: {'; '.join(proj.pending_tasks[:3])}")
        if proj.known_issues:
            parts.append(f"- Known Issues: {'; '.join(proj.known_issues[:3])}")

        return "\n".join(parts)

    def detect_project_in_text(self, text: str) -> Optional[str]:
        """Scan user text for known project names or slugs."""
        lower = text.lower()
        projects = self.memory_store.list_projects()
        for p in projects:
            if p.id in lower or p.name.lower() in lower:
                return p.id
        return None

# Global singleton
project_memory = ProjectMemoryManager()
