from typing import Dict, Any, Optional, List
from datetime import datetime

class AgentContext:
    """
    Shared execution context passed across workflow steps and specialized agents.
    Maintains workflow objective, project memory state, intermediate variables,
    evidence log, and visual observations.
    """

    def __init__(
        self,
        workflow_id: str,
        objective: str,
        project_id: Optional[str] = None,
        project_context: Optional[str] = None
    ):
        self.workflow_id = workflow_id
        self.objective = objective
        self.project_id = project_id
        self.project_context = project_context or ""
        self.step_results: Dict[int, Dict[str, Any]] = {}
        self.variables: Dict[str, Any] = {}
        self.visual_context: Optional[str] = None
        self.evidence_log: List[str] = []
        self.unresolved_issues: List[str] = []
        self.created_at = datetime.now().isoformat()

    def record_step_result(self, step_id: int, result: Dict[str, Any]):
        """Saves a step's execution result and extracts useful variables."""
        self.step_results[step_id] = result
        
        # Extract verifiable evidence
        if result.get("success") and (result.get("data") or result.get("output") or result.get("message")):
            summary = str(result.get("data") or result.get("output") or result.get("message"))
            self.evidence_log.append(f"Step {step_id}: {summary[:200]}")

        # Merge key variables from result into shared context
        if isinstance(result.get("data"), dict):
            for k, v in result["data"].items():
                self.variables[k] = v

    def get_context_summary(self) -> str:
        """Constructs a compact context string for agent prompt injection."""
        parts = [f"OBJECTIVE: {self.objective}"]
        if self.project_id:
            parts.append(f"PROJECT: {self.project_id}")
        if self.project_context:
            parts.append(f"PROJECT CONTEXT:\n{self.project_context[:600]}")
        if self.visual_context:
            parts.append(f"VISUAL CONTEXT:\n{self.visual_context[:400]}")
        if self.evidence_log:
            parts.append("EVIDENCE COLLECTED:\n- " + "\n- ".join(self.evidence_log[-5:]))
        return "\n\n".join(parts)
