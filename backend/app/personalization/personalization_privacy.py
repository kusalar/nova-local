import logging
from typing import Dict, Any
from .personalization_schemas import PrivacySettings

logger = logging.getLogger("nova.personalization.privacy")

class PersonalizationPrivacyManager:
    """
    Guarantees user privacy, local-only processing, and full user control
    over personalization, learning, and recommendations.
    Strictly forbids cloud telemetry, keystroke logging, and covert surveillance.
    """

    def __init__(self):
        self._enabled: bool = True
        self._adaptive_analysis_enabled: bool = True
        self._recommendations_enabled: bool = True

    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, val: bool):
        self._enabled = bool(val)
        logger.info(f"Personalization global master switch set to: {self._enabled}")

    def is_adaptive_analysis_enabled(self) -> bool:
        return self._enabled and self._adaptive_analysis_enabled

    def set_adaptive_analysis_enabled(self, val: bool):
        self._adaptive_analysis_enabled = bool(val)
        logger.info(f"Adaptive analysis set to: {self._adaptive_analysis_enabled}")

    def is_recommendations_enabled(self) -> bool:
        return self._enabled and self._recommendations_enabled

    def set_recommendations_enabled(self, val: bool):
        self._recommendations_enabled = bool(val)
        logger.info(f"Recommendations engine set to: {self._recommendations_enabled}")

    def get_privacy_settings(self) -> PrivacySettings:
        return PrivacySettings(
            local_only=True,
            no_cloud_sync=True,
            no_keystroke_monitoring=True,
            no_clipboard_monitoring=True,
            no_hidden_screen_storage=True,
            adaptive_analysis_enabled=self._adaptive_analysis_enabled,
            recommendations_enabled=self._recommendations_enabled
        )

    def update_privacy_settings(self, data: Dict[str, Any]) -> PrivacySettings:
        if "enabled" in data:
            self.set_enabled(bool(data["enabled"]))
        if "adaptive_analysis_enabled" in data:
            self.set_adaptive_analysis_enabled(bool(data["adaptive_analysis_enabled"]))
        if "recommendations_enabled" in data:
            self.set_recommendations_enabled(bool(data["recommendations_enabled"]))
        return self.get_privacy_settings()

    def clear_all_personalization_data(self):
        """Removes all learned and explicit personalization records safely."""
        from .preference_engine import preference_engine
        from .knowledge_graph import knowledge_graph
        from .recommendation_engine import recommendation_engine
        from .feedback_manager import feedback_manager

        preference_engine.clear_preferences()
        knowledge_graph.clear_graph()
        recommendation_engine.clear_recommendations()
        feedback_manager.clear_feedback()
        logger.info("All personalization data wiped per user privacy request.")

# Global singleton
personalization_privacy = PersonalizationPrivacyManager()
