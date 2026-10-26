import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .automation_schemas import NotificationType, NotificationItem, NotificationCreate
from .automation_logger import automation_logger

logger = logging.getLogger("nova.automation.notifications")

class NotificationPreferences:
    def __init__(self):
        self.tts_enabled: bool = False
        self.speak_sensitive_content: bool = False
        self.desktop_notifications_enabled: bool = True
        self.default_snooze_minutes: int = 15

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tts_enabled": self.tts_enabled,
            "speak_sensitive_content": self.speak_sensitive_content,
            "desktop_notifications_enabled": self.desktop_notifications_enabled,
            "default_snooze_minutes": self.default_snooze_minutes
        }

    def update(self, data: Dict[str, Any]):
        if "tts_enabled" in data:
            self.tts_enabled = bool(data["tts_enabled"])
        if "speak_sensitive_content" in data:
            self.speak_sensitive_content = bool(data["speak_sensitive_content"])
        if "desktop_notifications_enabled" in data:
            self.desktop_notifications_enabled = bool(data["desktop_notifications_enabled"])
        if "default_snooze_minutes" in data:
            self.default_snooze_minutes = int(data["default_snooze_minutes"])

class NotificationManager:
    """
    Unified Notification Center for NOVA v0.7:
    - In-app notification queuing & SQLite persistence
    - Real-time WebSocket broadcasting
    - Optional Piper TTS announcements with sensitivity gating
    - Snooze, dismiss, and mark read workflows
    """

    def __init__(self):
        self.preferences = NotificationPreferences()

    def send_notification(
        self,
        notif_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        speak_aloud: bool = False,
        is_sensitive: bool = False
    ) -> NotificationItem:
        """Creates and dispatches a notification across configured channels."""
        # 1. Save to SQLite persistent storage
        item = automation_logger.add_notification(
            notif_type=notif_type,
            title=title,
            message=message,
            data=data
        )

        # 2. Broadcast via WebSocket to connected frontend clients
        try:
            from app.voice.audio_manager import audio_manager
            audio_manager.broadcast_ws_event("notification_created", item.dict())
        except Exception as e:
            logger.debug(f"Could not broadcast notification over WS: {e}")

        # 3. Optional Piper TTS audio playback (respecting privacy boundaries)
        should_speak = speak_aloud or self.preferences.tts_enabled
        if should_speak:
            if is_sensitive and not self.preferences.speak_sensitive_content:
                logger.info(f"Notification '{title}' contains sensitive content and speak_sensitive_content is disabled. Skipping TTS.")
            else:
                self._speak_aloud(f"{title}. {message}")

        return item

    def _speak_aloud(self, text: str):
        try:
            from app.voice.audio_manager import audio_manager
            # Keep spoken notifications concise
            concise_text = text[:180] + ("..." if len(text) > 180 else "")
            audio_manager._speak_response(concise_text, agent_name="notification-center")
        except Exception as e:
            logger.warning(f"Failed to play notification audio via Piper TTS: {e}")

    def list_notifications(self, unread_only: bool = False, limit: int = 50) -> List[NotificationItem]:
        return automation_logger.list_notifications(unread_only=unread_only, limit=limit)

    def mark_read(self, notification_id: int) -> bool:
        res = automation_logger.mark_notification_read(notification_id)
        if res:
            try:
                from app.voice.audio_manager import audio_manager
                audio_manager.broadcast_ws_event("notification_updated", {"id": notification_id, "read": True})
            except Exception:
                pass
        return res

    def dismiss(self, notification_id: int) -> bool:
        res = automation_logger.dismiss_notification(notification_id)
        if res:
            try:
                from app.voice.audio_manager import audio_manager
                audio_manager.broadcast_ws_event("notification_dismissed", {"id": notification_id})
            except Exception:
                pass
        return res

    def snooze(self, notification_id: int, minutes: Optional[int] = None) -> bool:
        mins = minutes if minutes is not None else self.preferences.default_snooze_minutes
        snooze_time = datetime.utcnow() + timedelta(minutes=mins)
        res = automation_logger.snooze_notification(notification_id, snooze_time.isoformat())
        if res:
            try:
                from app.voice.audio_manager import audio_manager
                audio_manager.broadcast_ws_event("notification_snoozed", {"id": notification_id, "until": snooze_time.isoformat()})
            except Exception:
                pass
        return res

    def get_preferences(self) -> Dict[str, Any]:
        return self.preferences.to_dict()

    def update_preferences(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.preferences.update(data)
        return self.preferences.to_dict()

# Global singleton
notification_manager = NotificationManager()
