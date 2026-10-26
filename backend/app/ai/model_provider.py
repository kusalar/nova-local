from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class ModelProvider(ABC):
    """Abstract base class for all AI model providers in NOVA."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g. 'Ollama', 'Local', 'Mock')."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider backend is reachable and ready."""
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models for this provider."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Send a conversation history and receive a generated assistant response.
        
        Returns dict with:
        {
            "content": str,
            "model": str,
            "done": bool,
            "raw": Any
        }
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Return diagnostic health and status info."""
        pass
