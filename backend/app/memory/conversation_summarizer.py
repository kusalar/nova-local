import logging
from typing import List, Dict, Any, Optional
from app.memory.long_term_memory import long_term_memory
from app.ai.model_manager import model_manager

logger = logging.getLogger("nova.memory.summarizer")

class ConversationSummarizer:
    """
    Summarizes conversation sessions to maintain long-term context
    without exceeding token context windows.
    """

    def __init__(self):
        self.memory_store = long_term_memory

    async def summarize_session(
        self,
        messages: List[Dict[str, str]],
        session_id: str = "default"
    ) -> Optional[str]:
        """
        Produce a concise summary of a message session and record in memory.
        """
        if not messages or len(messages) < 2:
            return None

        # Build transcript text
        transcript_lines = []
        for m in messages:
            role = m.get("role", "unknown").capitalize()
            content = m.get("content", "").strip()
            if content:
                transcript_lines.append(f"{role}: {content}")

        transcript_text = "\n".join(transcript_lines[-20:])  # last 20 messages

        # Attempt Ollama local summarization
        prompt = (
            "Summarize the following conversation in 2-3 concise sentences. "
            "Highlight any key decisions, project mentions, or tasks discussed:\n\n"
            f"{transcript_text}"
        )

        summary_text = ""
        try:
            res = await model_manager.chat([{"role": "user", "content": prompt}])
            if res.get("success"):
                summary_text = res.get("content", "").strip()
        except Exception as e:
            logger.warning(f"Ollama summarization unavailable: {e}")

        # Fallback heuristic summary if model unavailable
        if not summary_text:
            user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
            summary_text = (
                f"Conversation in session '{session_id}' covering: "
                + "; ".join(user_msgs[:3])
            )

        # Store in database
        self.memory_store.add_summary(
            session_id=session_id,
            summary=summary_text,
            turn_count=len(messages)
        )
        logger.info(f"Generated conversation summary for session '{session_id}'")
        return summary_text

# Global singleton
conversation_summarizer = ConversationSummarizer()
