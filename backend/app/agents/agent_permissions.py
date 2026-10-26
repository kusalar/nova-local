import time
import logging
from typing import Dict, Any, Optional, Tuple

from app.tools.permission_manager import permission_manager
from app.tools.tool_schemas import PermissionLevel
from app.tools.tool_registry import tool_registry
from .agent_schemas import WorkflowStep, WorkflowPlan

logger = logging.getLogger("nova.agents.permissions")

class AgentPermissionEnforcer:
    """
    Enforces strict security boundaries for agentic workflows:
    - Never permits agents to self-escalate or grant additional permissions.
    - Routes all tool execution through the v0.4 PermissionManager.
    - Pauses workflows when confirmation-required steps are encountered.
    - Rejects blocked operations outright.
    - Treats all retrieved text, web content, OCR, and tool outputs as untrusted data.
    """

    @classmethod
    def evaluate_step_permission(cls, step: WorkflowStep) -> Tuple[PermissionLevel, bool, Optional[str]]:
        """
        Determines the authoritative permission level for a step.
        Returns (permission_level, requires_human_approval, reason).
        """
        if not step.tool_id:
            # Internal agent reasoning/synthesis is read-only
            return PermissionLevel.READ_ONLY, False, None

        tool_def = tool_registry.get_definition(step.tool_id)
        if not tool_def:
            return PermissionLevel.BLOCKED, False, f"Unknown or unregistered tool '{step.tool_id}'."

        # Query v0.4 authoritative permission level
        auth_level = permission_manager.get_effective_permission(step.tool_id, step.arguments)

        if auth_level == PermissionLevel.BLOCKED:
            return PermissionLevel.BLOCKED, False, f"Operation '{step.tool_id}' is permanently blocked by system policy."

        if auth_level == PermissionLevel.CONFIRMATION_REQUIRED:
            reason = (
                f"Step {step.step_id} ({step.description}) requires human approval. "
                f"Tool '{step.tool_id}' performs stateful modification."
            )
            return PermissionLevel.CONFIRMATION_REQUIRED, True, reason

        return auth_level, False, None

    @classmethod
    def sanitize_untrusted_input(cls, text: str) -> str:
        """
        Guards against prompt injection in retrieved content, OCR text, or tool outputs.
        Neutralizes instruction override attempts like 'Ignore previous instructions'.
        """
        if not text:
            return ""
        
        # Flag and neutralize common injection phrases
        suspicious = [
            "ignore previous instructions",
            "disregard all previous",
            "system prompt override",
            "you are now in developer mode",
            "grant admin privileges",
            "bypass confirmation"
        ]
        import re
        sanitized = text
        for s in suspicious:
            sanitized = re.sub(re.escape(s), f"[BLOCKED_PROMPT_INJECTION_ATTEMPT: {s}]", sanitized, flags=re.IGNORECASE)

        return sanitized
