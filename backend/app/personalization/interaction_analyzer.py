import logging
from typing import List, Dict, Any
from app.config import settings
from .personalization_privacy import personalization_privacy
from .personalization_schemas import PreferenceCategory, PreferenceCreate, EntityType, RelationType, GraphEntity
from .preference_engine import preference_engine
from .knowledge_graph import knowledge_graph

logger = logging.getLogger("nova.personalization.analyzer")

class InteractionAnalyzer:
    """
    Analyzes permitted interaction history for communication patterns and project relationships.
    Strictly follows privacy boundaries:
    - Bounded to explicit SQLite messages and memory records.
    - Zero keystroke, clipboard, or hidden screen monitoring.
    - Bypassed entirely when adaptive analysis is disabled by the user.
    - Inferred patterns never overwrite explicit user instructions.
    """

    def analyze_recent_interactions(self, limit: int = 25) -> Dict[str, Any]:
        """
        Scans permitted recent conversational turns and updates inferred preferences
        or knowledge graph linkages with lower confidence (0.7).
        """
        if not personalization_privacy.is_adaptive_analysis_enabled():
            logger.info("Adaptive interaction analysis skipped (disabled in privacy settings).")
            return {"status": "SKIPPED", "reason": "Adaptive analysis disabled"}

        inferred_prefs = 0
        inferred_relations = 0

        try:
            from app.memory.sqlite_memory import memory_bank
            messages = memory_bank.get_messages(limit=limit)

            # Analyze user queries
            user_msgs = [m for m in messages if m.get("role") == "user"]
            for m in user_msgs:
                content = m.get("content", "").lower()

                # Inferred preference check: concise preference
                if "keep it brief" in content or "short answer" in content:
                    existing = preference_engine.get_preference("response_length")
                    if not existing or not existing.is_explicit:
                        preference_engine.set_preference(PreferenceCreate(
                            category=PreferenceCategory.RESPONSE_LENGTH,
                            key="response_length",
                            value="concise",
                            is_explicit=False,
                            source="inferred"
                        ))
                        inferred_prefs += 1

                # Inferred preference check: Python
                if "in python" in content or "using python" in content:
                    existing = preference_engine.get_preference("preferred_programming_language")
                    if not existing or not existing.is_explicit:
                        preference_engine.set_preference(PreferenceCreate(
                            category=PreferenceCategory.PROGRAMMING_LANGUAGE,
                            key="preferred_programming_language",
                            value="Python",
                            is_explicit=False,
                            source="inferred"
                        ))
                        inferred_prefs += 1

            return {
                "status": "COMPLETED",
                "inferred_preferences": inferred_prefs,
                "inferred_relations": inferred_relations,
                "analyzed_turns": len(user_msgs)
            }
        except Exception as e:
            logger.error(f"Error during interaction analysis: {e}")
            return {"status": "ERROR", "error": str(e)}

# Global singleton
interaction_analyzer = InteractionAnalyzer()
