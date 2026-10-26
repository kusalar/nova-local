from typing import Dict, List, Optional
import logging

from .agent_schemas import AgentRole, AgentMetadata
from .agent_base import BaseAgent
from .specialized_agents import (
    ResearchAgent, DeveloperAgent, SystemAgent, VisionAgent, MemoryAgent
)

logger = logging.getLogger("nova.agents.registry")

class AgentRegistry:
    """
    Registry and lifecycle coordinator for all specialized agents in NOVA v0.6.
    """

    def __init__(self):
        self._agents: Dict[AgentRole, BaseAgent] = {}
        self._register_default_agents()

    def _register_default_agents(self):
        agents = [
            ResearchAgent(),
            DeveloperAgent(),
            SystemAgent(),
            VisionAgent(),
            MemoryAgent()
        ]
        for ag in agents:
            self._agents[ag.role] = ag
        logger.info(f"AgentRegistry initialized with {len(self._agents)} specialized agents.")

    def get_agent(self, role: AgentRole) -> Optional[BaseAgent]:
        """Fetch agent instance by logical role."""
        return self._agents.get(role)

    def get_agent_for_role(self, role: AgentRole) -> Optional[BaseAgent]:
        """Alias for get_agent."""
        return self.get_agent(role)

    def list_agents(self) -> List[AgentMetadata]:
        """List metadata for all active agents."""
        return [ag.metadata for ag in self._agents.values()]

    def get_agent_for_tool(self, tool_id: str) -> Optional[BaseAgent]:
        """Find an agent authorized to execute a specific tool."""
        for ag in self._agents.values():
            if tool_id in ag.metadata.allowed_tools:
                return ag
        return self._agents.get(AgentRole.SYSTEM)

    def get_authorized_agent_for_tool(self, tool_id: str) -> Optional[BaseAgent]:
        """Alias for get_agent_for_tool."""
        return self.get_agent_for_tool(tool_id)

# Global singleton
agent_registry = AgentRegistry()
