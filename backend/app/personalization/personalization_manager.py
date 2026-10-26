import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .personalization_schemas import (
    UserPreference, PreferenceCreate, PreferenceUpdate, PreferenceCategory,
    Recommendation, FeedbackRecord, ResolvedContext, KnowledgeGraphView,
    PersonalizationStatus, PrivacySettings
)
from .preference_engine import preference_engine
from .knowledge_graph import knowledge_graph
from .context_resolver import context_resolver
from .recommendation_engine import recommendation_engine
from .feedback_manager import feedback_manager
from .interaction_analyzer import interaction_analyzer
from .personalization_privacy import personalization_privacy

logger = logging.getLogger("nova.personalization.manager")

class PersonalizationManager:
    """
    Central coordinator for NOVA v0.8 Adaptive Intelligence & Personalization.
    Coordinates preferences, knowledge graph, context resolution,
    recommendations, feedback loops, and privacy controls.
    """

    def __init__(self):
        self.preferences = preference_engine
        self.graph = knowledge_graph
        self.context = context_resolver
        self.recommendations = recommendation_engine
        self.feedback = feedback_manager
        self.analyzer = interaction_analyzer
        self.privacy = personalization_privacy
        self._last_refreshed: Optional[str] = None

    def initialize(self):
        """Initializes knowledge graph sync and generates initial recommendations."""
        logger.info("Initializing PersonalizationManager...")
        try:
            self.graph.sync_from_existing_memory()
            self.recommendations.generate_recommendations()
            self._last_refreshed = datetime.utcnow().isoformat()
            logger.info("PersonalizationManager initialized successfully.")
        except Exception as e:
            logger.error(f"Error during personalization initialization: {e}")

    def refresh(self) -> Dict[str, Any]:
        """Re-syncs knowledge graph, runs adaptive analysis, and refreshes recommendations."""
        if not self.privacy.is_enabled():
            return {"status": "DISABLED", "message": "Personalization is currently disabled."}

        self.graph.sync_from_existing_memory()
        analysis_res = self.analyzer.analyze_recent_interactions()
        recs = self.recommendations.generate_recommendations()
        self._last_refreshed = datetime.utcnow().isoformat()

        return {
            "status": "REFRESHED",
            "active_recommendations": len(recs),
            "analysis_result": analysis_res,
            "timestamp": self._last_refreshed
        }

    # ==================== STATUS & PRIVACY ====================

    def get_status(self) -> PersonalizationStatus:
        all_prefs = self.preferences.list_preferences()
        explicit = sum(1 for p in all_prefs if p.is_explicit)
        inferred = len(all_prefs) - explicit
        recs = self.recommendations.list_recommendations(active_only=True)
        entities = self.graph.list_entities()
        relations = self.graph.list_relations()

        return PersonalizationStatus(
            enabled=self.privacy.is_enabled(),
            adaptive_analysis_enabled=self.privacy.is_adaptive_analysis_enabled(),
            recommendations_enabled=self.privacy.is_recommendations_enabled(),
            total_preferences=len(all_prefs),
            explicit_preferences_count=explicit,
            inferred_preferences_count=inferred,
            active_recommendations_count=len(recs),
            graph_entities_count=len(entities),
            graph_relations_count=len(relations),
            last_refreshed_at=self._last_refreshed
        )

    def enable(self):
        self.privacy.set_enabled(True)

    def disable(self):
        self.privacy.set_enabled(False)

    # ==================== VOICE DIRECTIVES ====================

    def handle_voice_personalization_command(self, transcript: str) -> Tuple[bool, str]:
        """
        Processes natural-language voice directives for personalization:
        - "Hey NOVA, what do you know about my current project?"
        - "Hey NOVA, remember that I prefer concise answers."
        - "Hey NOVA, why are you recommending this?"
        - "Hey NOVA, show my saved preferences."
        - "Hey NOVA, disable personalization."
        - "Hey NOVA, remove that preference."
        """
        import re
        lower_q = transcript.lower().strip()
        cleaned_q = re.sub(r"^(hey\s+nova\b[,:]?\s*|nova\b[,:]?\s*)", "", lower_q).strip()

        # 1. Enable / Disable
        if any(w in cleaned_q for w in ["disable personalization", "turn off personalization", "stop personalizing"]):
            self.disable()
            return True, "Personalization and adaptive learning have been disabled."
        if any(w in cleaned_q for w in ["enable personalization", "turn on personalization", "resume personalization"]):
            self.enable()
            return True, "Personalization and adaptive learning have been enabled."

        # 2. What do you know about my current project?
        if "what do you know about my" in cleaned_q or "tell me about my project" in cleaned_q or "current project" in cleaned_q:
            ctx = self.context.resolve_context(transcript)
            if ctx.clarification_needed and ctx.clarification_prompt:
                return True, ctx.clarification_prompt
            if ctx.active_project_id:
                tasks_info = f" with {len(ctx.relevant_tasks)} pending tasks" if ctx.relevant_tasks else ""
                proj_name = ctx.project_name or ctx.active_project_id
                return True, f"You are working on project {proj_name}{tasks_info}."
            return True, "I do not see an active project in our immediate context. You can specify a project by name."

        # 3. Explicit Preference: Remember that I prefer...
        detected_pref = self.preferences.detect_preference_in_directive(cleaned_q)
        if detected_pref:
            val = detected_pref.value
            return True, f"I have recorded your preference for {detected_pref.key.replace('_', ' ')}: {val}."

        # 4. Why are you recommending this?
        if any(w in cleaned_q for w in ["why are you recommending this", "why this recommendation", "reason for recommendation"]):
            recs = self.recommendations.list_recommendations(active_only=True, limit=1)
            if recs:
                rec = recs[0]
                evid = " ".join(rec.supporting_evidence[:2])
                return True, f"I recommended '{rec.title}' because {rec.reason}. Supporting evidence: {evid}"
            return True, "There are currently no active recommendations to explain."

        # 5. Show my saved preferences
        if any(w in cleaned_q for w in ["show my saved preferences", "show my preferences", "list my preferences", "what are my preferences"]):
            prefs = self.preferences.list_preferences()
            if not prefs:
                return True, "You do not have any saved preferences yet."
            items = [f"{p.key.replace('_', ' ')} is {p.value}" for p in prefs[:4]]
            return True, f"Your saved preferences include: {', '.join(items)}."

        # 6. Verbal Feedback & Removals
        handled_fb, resp_fb = self.feedback.process_voice_feedback(cleaned_q)
        if handled_fb:
            return True, resp_fb

        return False, ""

# Global singleton
personalization_manager = PersonalizationManager()
