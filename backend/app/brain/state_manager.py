from enum import Enum
from typing import List, Dict, Any
from datetime import datetime
import asyncio

class NovaState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"

class ActivityEvent:
    def __init__(self, title: str, category: str, detail: str, level: str = "INFO"):
        self.timestamp = datetime.now().isoformat()
        self.title = title
        self.category = category  # e.g. "AI", "SYSTEM", "CONVERSATION", "TASK"
        self.detail = detail
        self.level = level  # "INFO", "WARN", "LIVE", "SUCCESS", "ERROR"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "title": self.title,
            "category": self.category,
            "detail": self.detail,
            "level": self.level
        }

class StateManager:
    """Tracks current assistant state, transitions, and recent activities."""
    
    def __init__(self):
        self.current_state: NovaState = NovaState.IDLE
        self.status_message: str = "NOVA SYSTEM ONLINE"
        self._activities: List[ActivityEvent] = [
            ActivityEvent("Core Initialization", "SYSTEM", "NOVA Neural Engine v0.1 initialized", "LIVE"),
            ActivityEvent("Memory Bank", "SYSTEM", "SQLite neural memory ready", "INFO"),
            ActivityEvent("Hardware Link", "SYSTEM", "psutil telemetry stream established", "INFO")
        ]
        self._lock = asyncio.Lock()

    def get_state(self) -> NovaState:
        return self.current_state

    def set_state(self, state: NovaState, status_message: str = "") -> None:
        self.current_state = state
        if status_message:
            self.status_message = status_message
        else:
            defaults = {
                NovaState.IDLE: "NOVA SYSTEM ONLINE",
                NovaState.LISTENING: "AWAITING VOCAL / TEXT INPUT",
                NovaState.THINKING: "PROCESSING NEURAL INFERENCE",
                NovaState.EXECUTING: "EXECUTING DIRECTIVE",
                NovaState.SPEAKING: "TRANSMITTING RESPONSE",
                NovaState.ERROR: "ANOMALY DETECTED"
            }
            self.status_message = defaults.get(state, "SYSTEM READY")

    def add_activity(self, title: str, category: str, detail: str, level: str = "INFO"):
        evt = ActivityEvent(title, category, detail, level)
        self._activities.insert(0, evt)
        # Keep recent 50
        if len(self._activities) > 50:
            self._activities = self._activities[:50]

    def get_activities(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._activities]

    def get_status_payload(self) -> Dict[str, Any]:
        return {
            "state": self.current_state.value,
            "status_message": self.status_message,
            "timestamp": datetime.now().isoformat()
        }

state_manager = StateManager()
