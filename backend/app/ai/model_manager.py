from typing import List, Dict, Any, Optional, AsyncIterator
import logging
from app.ai.model_provider import ModelProvider
from app.ai.ollama_provider import OllamaProvider
from app.config import settings

logger = logging.getLogger("nova.ai.manager")

class ModelManager:
    """
    Coordinates AI model providers and manages active models in NOVA.
    Allows dynamic model selection, fallback handling, and status interrogation.
    """

    def __init__(self):
        self.default_provider: ModelProvider = OllamaProvider()
        self.active_provider: ModelProvider = self.default_provider
        self.active_model: str = settings.DEFAULT_MODEL
        self._providers: Dict[str, ModelProvider] = {
            "ollama": self.default_provider
        }

    def register_provider(self, key: str, provider: ModelProvider) -> None:
        self._providers[key] = provider

    def set_active_provider(self, key: str) -> bool:
        if key in self._providers:
            self.active_provider = self._providers[key]
            return True
        return False

    def set_active_model(self, model_name: str) -> None:
        self.active_model = model_name

    async def get_status(self) -> Dict[str, Any]:
        """Returns provider status, active model, and list of available models."""
        provider_health = await self.active_provider.health_check()
        provider_health["active_model"] = self.active_model
        return provider_health

    def _format_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        formatted_messages: List[Dict[str, str]] = []
        has_system = any(m.get("role") == "system" for m in messages)
        if not has_system:
            sys_content = system_prompt or settings.SYSTEM_PROMPT
            formatted_messages.append({"role": "system", "content": sys_content})
        formatted_messages.extend(messages)
        return formatted_messages

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        profile: str = "text",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Prepares messages with system context and queries active model provider.
        """
        target_model = model or self.active_model
        formatted_messages = self._format_messages(messages, system_prompt)
        return await self.active_provider.chat(
            messages=formatted_messages,
            model=target_model,
            profile=profile,
            request_id=request_id,
        )

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        profile: str = "text",
        request_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        target_model = model or self.active_model
        formatted_messages = self._format_messages(messages, system_prompt)
        provider = self.active_provider
        stream_fn = getattr(provider, "chat_stream", None)
        if stream_fn is None:
            result = await provider.chat(formatted_messages, model=target_model, profile=profile, request_id=request_id)
            if result.get("success"):
                yield {"type": "token", "content": result.get("content", ""), "model": target_model, "request_id": request_id}
                yield {"type": "done", "content": "", "model": target_model, "metrics": result.get("metrics", {}), "request_id": request_id}
            else:
                yield {"type": "error", **result, "request_id": request_id}
            return
        async for event in stream_fn(
            formatted_messages,
            model=target_model,
            profile=profile,
            request_id=request_id,
        ):
            yield event

    def cancel_active(self) -> Optional[str]:
        provider = self.active_provider
        fn = getattr(provider, "cancel_active", None)
        if fn:
            return fn()
        return None

# Global singleton instance
model_manager = ModelManager()
