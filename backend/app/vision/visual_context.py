from typing import Optional, Tuple
from .vision_schemas import WindowInfo, OcrResult
from app.memory.project_memory import project_memory

class VisualContextBuilder:
    """
    Constructs compact, structured desktop context for LLM prompt injection.
    Blends active window awareness, sanitized OCR text, and long-term project memory.
    """

    @classmethod
    def build_context_prompt(
        cls,
        window_info: Optional[WindowInfo],
        ocr_result: Optional[OcrResult],
        project_id: Optional[str] = None,
        max_ocr_chars: int = 2500
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Builds a concise context string and resolves matching project memory if applicable.
        """
        resolved_project_id = project_id
        project_context_str = ""

        # Auto-detect project from window title if not explicitly provided
        if not resolved_project_id and window_info and window_info.title:
            detected = project_memory.detect_project_in_text(window_info.title)
            if detected:
                resolved_project_id = detected

        # If still not found, check OCR text for known project mentions
        if not resolved_project_id and ocr_result and ocr_result.full_text:
            detected = project_memory.detect_project_in_text(ocr_result.full_text[:500])
            if detected:
                resolved_project_id = detected

        if resolved_project_id:
            project_context_str = project_memory.get_project_context_string(resolved_project_id)

        # Build visual section
        lines = ["[DESKTOP VISUAL INTELLIGENCE CONTEXT]"]

        if window_info:
            lines.append(f"Active Application: {window_info.app_name} (Process: {window_info.process_name})")
            lines.append(f"Window Title: \"{window_info.title}\"")
            if window_info.is_minimized:
                lines.append("Window State: Minimized")
        else:
            lines.append("Active Window: Undetected or Background")

        if project_context_str:
            lines.append("\nRelevant Project Memory:")
            lines.append(project_context_str)

        if ocr_result and ocr_result.full_text.strip():
            raw_text = ocr_result.full_text.strip()
            if len(raw_text) > max_ocr_chars:
                snippet = raw_text[:max_ocr_chars] + f"\n... [Truncated: {len(raw_text) - max_ocr_chars} additional characters]"
            else:
                snippet = raw_text

            lines.append(f"\nVisible Screen Content (Local OCR - {ocr_result.total_words} words detected):")
            lines.append("```")
            lines.append(snippet)
            lines.append("```")
        else:
            lines.append("\nVisible Screen Content: [No text detected on captured area]")

        context_string = "\n".join(lines)
        return context_string, resolved_project_id, project_context_str


