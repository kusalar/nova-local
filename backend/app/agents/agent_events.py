import uuid
import logging
from typing import Optional, Dict, Any

from .agent_schemas import WorkflowEvent, EventType, AgentRole
from .workflow_logger import workflow_logger

logger = logging.getLogger("nova.agents.events")

class AgentEventBus:
    """
    Central event bus for agentic workflows:
    - Persists audit events to SQLite via WorkflowLogger.
    - Broadcasts live WebSocket events to connected desktop clients.
    """

    @classmethod
    def emit(
        cls,
        workflow_id: str,
        event_type: EventType,
        message: str,
        step_id: Optional[int] = None,
        agent_role: Optional[AgentRole] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> WorkflowEvent:
        event = WorkflowEvent(
            event_id=f"evt_{uuid.uuid4().hex[:10]}",
            workflow_id=workflow_id,
            step_id=step_id,
            event_type=event_type,
            agent_role=agent_role,
            message=message,
            payload=payload or {}
        )

        # 1. Log to persistent database
        workflow_logger.log_event(event)

        # 2. Broadcast to desktop WebSocket clients
        try:
            from app.voice.audio_manager import audio_manager
            audio_manager.broadcast_ws_event("agent_workflow_event", event.dict())
        except Exception as e:
            logger.debug(f"Could not broadcast workflow event: {e}")

        return event
