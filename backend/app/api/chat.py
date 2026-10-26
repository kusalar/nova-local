from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, AsyncIterator
import json
import logging

from app.ai.model_manager import model_manager
from app.ai.inference_config import inference_config
from app.ai.inference_tracer import new_request_id
from app.brain.state_manager import state_manager, NovaState
from app.memory.sqlite_memory import memory_bank
from app.memory.memory_manager import memory_manager
from app.config import settings

logger = logging.getLogger("nova.api.chat")

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt or directive")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Recent turn history")
    model: Optional[str] = Field(default=None, description="Optional override model name")
    session_id: Optional[str] = Field(default="default", description="Memory session identifier")
    project_id: Optional[str] = Field(default=None, description="Optional active project scope")
    profile: Optional[str] = Field(default="text", description="Inference profile: text or voice")

class StateUpdateRequest(BaseModel):
    state: NovaState
    message: Optional[str] = None


def trim_history(history: Optional[List[ChatMessage]], max_turns: int) -> List[Dict[str, str]]:
    """Keep only the last N user/assistant turns. Drops extra system blobs."""
    rows: List[Dict[str, str]] = []
    for h in (history or []):
        role = (h.role or "").strip()
        content = (h.content or "").strip()
        if role in ("user", "assistant") and content:
            rows.append({"role": role, "content": content})
    keep = max(0, max_turns) * 2
    if keep and len(rows) > keep:
        rows = rows[-keep:]
    return rows


def _prepare_turn(payload: ChatRequest) -> Dict[str, Any]:
    """Shared pre-inference work. Does not call Ollama or run embeddings extract."""
    user_text = payload.message.strip()
    session_id = payload.session_id or "default"
    profile = payload.profile or "text"

    state_manager.set_state(NovaState.THINKING, "PROCESSING NEURAL INFERENCE")
    state_manager.add_activity(
        title="Prompt Received",
        category="CONVERSATION",
        detail=user_text[:60] + ("..." if len(user_text) > 60 else ""),
        level="INFO"
    )

    memory_bank.add_message(role="user", content=user_text, session_id=session_id)

    explicit_answer = memory_manager.handle_explicit_memory_query(user_text)

    from app.personalization import personalization_manager
    detected_pref = personalization_manager.preferences.detect_preference_in_directive(user_text)
    if detected_pref and not explicit_answer:
        explicit_answer = f"I have recorded your preference for {detected_pref.key.replace('_', ' ')}: '{detected_pref.value}'."

    resolved_ctx = personalization_manager.context.resolve_context(
        user_query=user_text,
        session_id=session_id,
        explicit_project_id=payload.project_id
    )

    compact = profile == "voice"
    memory_context, detected_proj = memory_manager.build_augmented_context(
        user_query=user_text,
        session_id=session_id,
        current_project=resolved_ctx.active_project_id or payload.project_id,
        compact=compact,
        max_items=2 if compact else 4,
    )

    from app.security.content_sanitizer import content_sanitizer

    system_prompt = settings.SYSTEM_PROMPT
    if profile == "voice":
        system_prompt = (
            system_prompt
            + " Spoken replies must be 1-3 short sentences. No markdown, lists, or code fences."
        )
    enrichment_blocks = []
    if memory_context:
        untrusted_mem = content_sanitizer.wrap_untrusted_content(memory_context, "retrieved_memory")
        enrichment_blocks.append(untrusted_mem)
    if resolved_ctx.formatted_instructions and not compact:
        enrichment_blocks.append(f"=== PERSONALIZATION DIRECTIVES ===\n{resolved_ctx.formatted_instructions}")

    if enrichment_blocks:
        system_prompt = f"{system_prompt}\n\n" + "\n\n".join(enrichment_blocks) + "\n================================"

    max_turns = (
        inference_config.max_history_turns_voice if compact else inference_config.max_history_turns
    )
    history_messages = trim_history(payload.history, max_turns)
    history_messages.append({"role": "user", "content": user_text})

    return {
        "user_text": user_text,
        "session_id": session_id,
        "profile": profile,
        "explicit_answer": explicit_answer,
        "clarification_prompt": resolved_ctx.clarification_prompt if resolved_ctx.clarification_needed else None,
        "detected_proj": detected_proj,
        "system_prompt": system_prompt,
        "history_messages": history_messages,
        "request_id": new_request_id(),
    }


def _persist_assistant(session_id: str, content: str, model: Optional[str], user_text: str, project_id: Optional[str]) -> None:
    memory_bank.add_message(role="assistant", content=content, session_id=session_id, model=model)
    try:
        memory_manager.process_turn_and_extract(
            user_query=user_text,
            session_id=session_id,
            project_id=project_id,
        )
    except Exception as err:
        logger.warning("Post-inference memory extract skipped: %s", err)


@router.post("")
async def chat_endpoint(payload: ChatRequest):
    """
    Process conversation prompt with NOVA AI engine, augmented with persistent memory.
    Transitions states through THINKING -> SPEAKING/ERROR -> IDLE.
    Logs interaction to SQLite memory and extracts persistent facts after inference.
    """
    prepared = _prepare_turn(payload)

    if prepared["clarification_prompt"]:
        state_manager.set_state(NovaState.IDLE, "AWAITING PROJECT CLARIFICATION")
        return {
            "response": prepared["clarification_prompt"],
            "session_id": prepared["session_id"],
            "detected_project": None,
            "clarification_needed": True
        }

    if prepared["explicit_answer"]:
        state_manager.set_state(NovaState.IDLE, "MEMORY RETRIEVAL COMPLETE")
        memory_bank.add_message(
            role="assistant",
            content=prepared["explicit_answer"],
            session_id=prepared["session_id"],
            model="nova-memory-engine"
        )
        return {
            "success": True,
            "response": prepared["explicit_answer"],
            "model": "nova-memory-engine",
            "state": NovaState.IDLE.value,
            "project_id": prepared["detected_proj"],
            "request_id": prepared["request_id"],
            "ollama_calls": 0,
        }

    from app.reliability.resource_coordinator import resource_coordinator

    try:
        async with resource_coordinator.acquire_inference_slot(timeout=180.0):
            result = await model_manager.chat(
                messages=prepared["history_messages"],
                model=payload.model,
                system_prompt=prepared["system_prompt"],
                profile=prepared["profile"],
                request_id=prepared["request_id"],
            )

        if result.get("success"):
            response_content = result.get("content", "")
            state_manager.set_state(NovaState.SPEAKING, "TRANSMITTING RESPONSE")
            state_manager.add_activity(
                title="Response Synthesized",
                category="AI",
                detail=f"Inference completed via {result.get('model')}",
                level="SUCCESS"
            )
            _persist_assistant(
                prepared["session_id"],
                response_content,
                result.get("model"),
                prepared["user_text"],
                payload.project_id,
            )
            return {
                "success": True,
                "response": response_content,
                "model": result.get("model"),
                "state": NovaState.SPEAKING.value,
                "project_id": prepared["detected_proj"],
                "memories_extracted": 0,
                "metrics": result.get("metrics"),
                "request_id": result.get("request_id") or prepared["request_id"],
                "ollama_calls": 1,
            }

        error_msg = result.get("content", "Neural inference engine error.")
        state_manager.set_state(NovaState.ERROR, "NEURAL OFFLINE / MODEL MISSING")
        state_manager.add_activity(
            title="AI Inference Warning",
            category="AI",
            detail=result.get("error_type", "OLLAMA_ERROR"),
            level="WARN"
        )
        return {
            "success": False,
            "error_type": result.get("error_type", "INFERENCE_ERROR"),
            "response": error_msg,
            "model": result.get("model"),
            "state": NovaState.ERROR.value,
            "request_id": prepared["request_id"],
        }

    except Exception as e:
        state_manager.set_state(NovaState.ERROR, "INTERNAL EXCEPTION")
        state_manager.add_activity(
            title="Internal Fault",
            category="SYSTEM",
            detail=str(e),
            level="ERROR"
        )
        return {
            "success": False,
            "error_type": "INTERNAL_EXCEPTION",
            "response": f"NOVA encountered an unexpected system exception: {str(e)}",
            "state": NovaState.ERROR.value
        }


@router.post("/stream")
async def chat_stream_endpoint(payload: ChatRequest):
    """NDJSON stream of token events so the UI can render the first generated token immediately."""
    prepared = _prepare_turn(payload)

    async def event_gen() -> AsyncIterator[bytes]:
        def pack(obj: Dict[str, Any]) -> bytes:
            return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")

        if prepared["clarification_prompt"]:
            state_manager.set_state(NovaState.IDLE, "AWAITING PROJECT CLARIFICATION")
            yield pack({"type": "token", "content": prepared["clarification_prompt"]})
            yield pack({"type": "done", "success": True, "ollama_calls": 0, "request_id": prepared["request_id"]})
            return

        if prepared["explicit_answer"]:
            state_manager.set_state(NovaState.IDLE, "MEMORY RETRIEVAL COMPLETE")
            memory_bank.add_message(
                role="assistant",
                content=prepared["explicit_answer"],
                session_id=prepared["session_id"],
                model="nova-memory-engine"
            )
            yield pack({"type": "token", "content": prepared["explicit_answer"], "model": "nova-memory-engine"})
            yield pack({"type": "done", "success": True, "ollama_calls": 0, "request_id": prepared["request_id"]})
            return

        from app.reliability.resource_coordinator import resource_coordinator
        collected: List[str] = []
        final_model = payload.model
        try:
            async with resource_coordinator.acquire_inference_slot(timeout=180.0):
                async for event in model_manager.chat_stream(
                    messages=prepared["history_messages"],
                    model=payload.model,
                    system_prompt=prepared["system_prompt"],
                    profile=prepared["profile"],
                    request_id=prepared["request_id"],
                ):
                    if event.get("type") == "token":
                        collected.append(event.get("content") or "")
                    if event.get("model"):
                        final_model = event.get("model")
                    yield pack(event)
                    if event.get("type") in ("done", "error"):
                        break
            text = "".join(collected)
            if text and (not event or event.get("type") != "error"):
                state_manager.set_state(NovaState.SPEAKING, "TRANSMITTING RESPONSE")
                _persist_assistant(
                    prepared["session_id"],
                    text,
                    final_model,
                    prepared["user_text"],
                    payload.project_id,
                )
        except Exception as e:
            yield pack({"type": "error", "error_type": "INTERNAL_EXCEPTION", "content": str(e)})

    return StreamingResponse(event_gen(), media_type="application/x-ndjson")


@router.post("/cancel")
async def cancel_inference():
    cancelled = model_manager.cancel_active()
    return {"success": True, "cancelled_request_id": cancelled}


@router.get("/history")
async def get_history(session_id: str = "default", limit: int = 50):
    """Retrieve persistent conversation history from SQLite."""
    messages = memory_bank.get_messages(session_id=session_id, limit=limit)
    return {
        "session_id": session_id,
        "count": len(messages),
        "messages": messages
    }

@router.delete("/history")
async def clear_history(session_id: str = "default"):
    """Purge conversation history."""
    memory_bank.clear_session(session_id=session_id)
    state_manager.set_state(NovaState.IDLE, "MEMORY PURGED — SYSTEM READY")
    state_manager.add_activity(
        title="Memory Purged",
        category="CONVERSATION",
        detail=f"Cleared history for session '{session_id}'",
        level="INFO"
    )
    return {"success": True, "message": "Conversation history cleared."}

@router.post("/state")
async def update_state(payload: StateUpdateRequest):
    """Explicitly set assistant state (e.g. LISTENING when mic tapped)."""
    state_manager.set_state(payload.state, payload.message or "")
    return {
        "success": True,
        "state": state_manager.get_state().value,
        "message": state_manager.status_message
    }
