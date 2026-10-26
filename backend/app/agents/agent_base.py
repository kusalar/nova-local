from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from .agent_schemas import (
    AgentRole, AgentStatus, AgentMetadata, WorkflowStep,
    ReflectionEvaluation
)
from app.ai.model_manager import model_manager
from app.tools.tool_registry import tool_registry

logger = logging.getLogger("nova.agents.base")

class BaseAgent(ABC):
    """
    Abstract base class for all specialized NOVA agents.
    All agents operate as logical personas over the shared local Ollama model provider,
    ensuring zero unnecessary RAM overhead.
    """

    def __init__(self, metadata: AgentMetadata):
        self.metadata = metadata

    @property
    def role(self) -> AgentRole:
        return self.metadata.role

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def allowed_tools(self) -> List[str]:
        return self.metadata.allowed_tools

    @property
    def capabilities(self) -> List[str]:
        return self.metadata.capabilities

    def can_handle(self, step: WorkflowStep) -> bool:
        """Determines if this agent can execute the given step."""
        if step.assigned_agent == self.role:
            return True
        if step.tool_id and step.tool_id in self.metadata.allowed_tools:
            return True
        return False

    @abstractmethod
    async def execute_step(self, step: WorkflowStep, context: Any) -> Dict[str, Any]:
        """Executes the assigned workflow step using tools, reasoning, or vision."""
        pass

    async def reflect(self, step: WorkflowStep, result: Dict[str, Any], context: Any) -> ReflectionEvaluation:
        """
        Bounded reflection and self-evaluation after step execution.
        Verifies that actual tool execution output supports the intended step outcome.
        """
        is_error = bool(result.get("error")) or result.get("success") is False
        evidence_str = str(result.get("data") or result.get("output") or result.get("message") or "")
        
        # Bounded evaluation
        goal_satisfied = not is_error and len(evidence_str) > 0

        action = "CONTINUE" if goal_satisfied else ("RETRY" if step.retry_policy.retry_count < step.retry_policy.max_retries else "PAUSE")

        return ReflectionEvaluation(
            step_id=step.step_id,
            success=not is_error,
            evidence=evidence_str[:400] if len(evidence_str) > 400 else evidence_str,
            goal_satisfied=goal_satisfied,
            requires_clarification=is_error and step.retry_policy.retry_count >= step.retry_policy.max_retries,
            can_proceed=goal_satisfied,
            suggested_action=action
        )

    async def _query_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Helper to invoke the shared local Ollama model with role-specific system prompt."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = await model_manager.chat(messages=messages, model=model_manager.active_model)
        return response.get("content", "")
