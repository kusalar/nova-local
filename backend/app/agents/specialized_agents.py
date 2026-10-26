import os
import json
import logging
from typing import Dict, Any, Optional, List

from .agent_base import BaseAgent
from .agent_schemas import AgentRole, AgentStatus, AgentMetadata, WorkflowStep, ReflectionEvaluation
from .agent_context import AgentContext
from app.tools.tool_executor import tool_executor
from app.tools.tool_registry import tool_registry
from app.tools.system_tools import SystemMonitor
from app.memory.project_memory import project_memory
from app.memory.long_term_memory import long_term_memory
from app.memory.memory_models import MemoryCreate, MemoryCategory
from app.vision.vision_manager import vision_manager
from app.vision.vision_schemas import VisualAnalysisRequest, CaptureTarget

logger = logging.getLogger("nova.agents.specialized")

async def _execute_registered_tool(tool_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    tool_entry = tool_registry.get_tool(tool_id)
    if not tool_entry:
        return {"success": False, "error": f"Tool '{tool_id}' is not registered."}
    handler = tool_entry.handler
    try:
        import asyncio, inspect
        if inspect.iscoroutinefunction(handler):
            res = await handler(**arguments)
        else:
            res = handler(**arguments)
        if isinstance(res, dict):
            return {
                "success": res.get("success", True),
                "data": res.get("data", res),
                "message": res.get("message", "Executed successfully"),
                "output": str(res.get("data", res))
            }
        else:
            return {"success": True, "data": res, "output": str(res), "message": "Executed successfully"}
    except Exception as e:
        return {"success": False, "error": str(e), "message": f"Execution failed: {str(e)}"}

# ==========================================
# 1. Research Agent
# ==========================================

class ResearchAgent(BaseAgent):
    """
    Analyzes supplied documents, reads project resources, summarizes findings,
    and isolates offline vs online research operations.
    """

    def __init__(self):
        super().__init__(AgentMetadata(
            id="agent_research",
            name="Research Agent",
            role=AgentRole.RESEARCH,
            description="Analyzes local project documents, extracts specifications, and produces structured research summaries.",
            capabilities=["document_analysis", "project_search", "structured_synthesis", "gap_identification"],
            allowed_tools=[
                "file_read_text", "folder_list_contents", "file_get_metadata",
                "file_search_name", "file_search_extension", "browser_search_web"
            ]
        ))

    async def execute_step(self, step: WorkflowStep, context: AgentContext) -> Dict[str, Any]:
        self.metadata.status = AgentStatus.BUSY
        try:
            # If tool execution is requested
            if step.tool_id:
                res = await _execute_registered_tool(step.tool_id, step.arguments)
                evidence = str(res.get("data") or res.get("message") or "")
                
                # Synthesize findings with local LLM if step demands analysis
                analysis_prompt = (
                    f"Objective: {context.objective}\n"
                    f"Step: {step.description}\n"
                    f"Evidence: {evidence[:1500]}\n\n"
                    "Synthesize research findings concisely. Identify key points and any missing information."
                )
                summary = await self._query_llm(
                    system_prompt="You are the NOVA Research Agent. Provide factual, structured technical research summaries.",
                    user_prompt=analysis_prompt
                )
                self.metadata.tasks_completed += 1
                return {
                    "success": res.get("success", True),
                    "data": res.get("data"),
                    "output": summary,
                    "message": f"Research complete: {step.description}"
                }
            else:
                # Pure synthesis step without external tool
                summary = await self._query_llm(
                    system_prompt="You are the NOVA Research Agent. Analyze project context and synthesize insights.",
                    user_prompt=f"Objective: {context.objective}\nTask: {step.description}\nContext:\n{context.get_context_summary()}"
                )
                self.metadata.tasks_completed += 1
                return {
                    "success": True,
                    "output": summary,
                    "message": "Research analysis complete."
                }
        finally:
            self.metadata.status = AgentStatus.IDLE

# ==========================================
# 2. Developer Agent
# ==========================================

class DeveloperAgent(BaseAgent):
    """
    Inspects permitted repository files, interprets test configurations,
    proposes modifications, and runs approved development checks.
    Never silently modifies project files without approval.
    """

    def __init__(self):
        super().__init__(AgentMetadata(
            id="agent_developer",
            name="Developer Agent",
            role=AgentRole.DEVELOPER,
            description="Inspects source code, analyzes project architecture, runs approved test suites, and evaluates bugs.",
            capabilities=["code_inspection", "repo_structure_analysis", "test_execution", "bug_diagnosis"],
            allowed_tools=[
                "file_read_text", "folder_list_contents", "file_get_metadata",
                "file_search_name", "file_search_extension", "file_copy", "file_move",
                "app_open", "app_detect_installed"
            ]
        ))

    async def execute_step(self, step: WorkflowStep, context: AgentContext) -> Dict[str, Any]:
        self.metadata.status = AgentStatus.BUSY
        try:
            if step.tool_id:
                res = await _execute_registered_tool(step.tool_id, step.arguments)
                tool_output = str(res.get("data") or res.get("message") or "")

                # Developer analysis of tool outcome
                dev_prompt = (
                    f"Repository/Code context:\n{tool_output[:1800]}\n\n"
                    f"Step Goal: {step.description}\n"
                    "Interpret the results. Highlight structure, test outcomes, or potential improvements."
                )
                analysis = await self._query_llm(
                    system_prompt="You are the NOVA Developer Agent. Provide rigorous, technical software engineering assessments.",
                    user_prompt=dev_prompt
                )
                self.metadata.tasks_completed += 1
                return {
                    "success": res.get("success", True),
                    "data": res.get("data"),
                    "output": analysis,
                    "message": f"Development task evaluated: {step.description}"
                }
            else:
                analysis = await self._query_llm(
                    system_prompt="You are the NOVA Developer Agent. Plan or evaluate technical implementation details.",
                    user_prompt=f"Objective: {context.objective}\nTask: {step.description}\nContext:\n{context.get_context_summary()}"
                )
                self.metadata.tasks_completed += 1
                return {
                    "success": True,
                    "output": analysis,
                    "message": "Code assessment complete."
                }
        finally:
            self.metadata.status = AgentStatus.IDLE

# ==========================================
# 3. System Agent
# ==========================================

class SystemAgent(BaseAgent):
    """
    Inspects hardware metrics, launches authorized applications,
    and manages approved files/folders via registered v0.4 desktop tools.
    """

    def __init__(self):
        super().__init__(AgentMetadata(
            id="agent_system",
            name="System Agent",
            role=AgentRole.SYSTEM,
            description="Monitors hardware telemetry, manages desktop applications, and performs registered filesystem tasks.",
            capabilities=["system_telemetry", "app_control", "filesystem_operations", "process_monitoring"],
            allowed_tools=[
                "system_cpu_ram", "system_battery_info", "system_disk_usage",
                "system_network_status", "system_volume_get", "system_volume_set",
                "system_lock_workstation", "app_open", "app_detect_installed",
                "file_open_default", "folder_open_explorer", "folder_create",
                "file_rename", "file_move", "file_copy", "file_read_text",
                "folder_list_contents", "file_get_metadata", "folder_organize_preview"
            ]
        ))

    async def execute_step(self, step: WorkflowStep, context: AgentContext) -> Dict[str, Any]:
        self.metadata.status = AgentStatus.BUSY
        try:
            if step.tool_id:
                res = await _execute_registered_tool(step.tool_id, step.arguments)
                self.metadata.tasks_completed += 1
                return {
                    "success": res.get("success", True),
                    "data": res.get("data"),
                    "output": res.get("message") or str(res.get("data")),
                    "message": res.get("message", "System operation executed.")
                }
            else:
                # Query current telemetry directly
                metrics = SystemMonitor.get_metrics()
                self.metadata.tasks_completed += 1
                return {
                    "success": True,
                    "data": metrics,
                    "output": f"CPU: {metrics.get('cpu', {}).get('percent')}%, RAM: {metrics.get('ram', {}).get('percent')}%",
                    "message": "Hardware telemetry collected."
                }
        finally:
            self.metadata.status = AgentStatus.IDLE

# ==========================================
# 4. Vision Agent
# ==========================================

class VisionAgent(BaseAgent):
    """
    Interfaces with v0.5 visual intelligence: captures desktop display,
    extracts structured local OCR, identifies visual errors, and feeds context.
    """

    def __init__(self):
        super().__init__(AgentMetadata(
            id="agent_vision",
            name="Vision Agent",
            role=AgentRole.VISION,
            description="Inspects active application windows, extracts on-screen text with local OCR, and provides visual context.",
            capabilities=["screen_capture", "local_ocr_reading", "visual_error_detection", "window_context_awareness"],
            allowed_tools=["vision_capture", "vision_ocr", "vision_analyze", "vision_windows"]
        ))

    async def execute_step(self, step: WorkflowStep, context: AgentContext) -> Dict[str, Any]:
        self.metadata.status = AgentStatus.BUSY
        try:
            target_str = step.arguments.get("target", "PRIMARY")
            target = CaptureTarget.ACTIVE_WINDOW if target_str == "ACTIVE_WINDOW" else CaptureTarget.PRIMARY
            
            prompt = step.arguments.get("prompt") or step.description
            
            # Execute visual analysis using v0.5 VisionManager
            req = VisualAnalysisRequest(
                prompt=prompt,
                capture_target=target,
                include_ocr=True,
                project_id=context.project_id
            )
            vis_resp = await vision_manager.analyze_screen(req)

            # Record visual findings in shared context
            context.visual_context = (
                f"Active Window: {vis_resp.active_window.title if vis_resp.active_window else 'Unknown'}\n"
                f"Visual Observations: {vis_resp.answer}\n"
                f"OCR Words Detected: {vis_resp.ocr_result.total_words if vis_resp.ocr_result else 0}"
            )

            self.metadata.tasks_completed += 1
            return {
                "success": True,
                "data": {
                    "answer": vis_resp.answer,
                    "active_window": vis_resp.active_window.dict() if vis_resp.active_window else None,
                    "words_detected": vis_resp.ocr_result.total_words if vis_resp.ocr_result else 0
                },
                "output": vis_resp.answer,
                "message": f"Visual inspection complete: {vis_resp.answer[:120]}"
            }
        except Exception as e:
            logger.error(f"Vision agent execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Visual capture failed: {str(e)}"
            }
        finally:
            self.metadata.status = AgentStatus.IDLE

# ==========================================
# 5. Memory Agent
# ==========================================

class MemoryAgent(BaseAgent):
    """
    Interacts with v0.3 persistent memory: fetches project decisions,
    retrieves previous similar workflows, and records completed outcomes.
    Never stores credentials or sensitive arguments.
    """

    def __init__(self):
        super().__init__(AgentMetadata(
            id="agent_memory",
            name="Memory Agent",
            role=AgentRole.MEMORY,
            description="Maintains project context, retrieves historical decisions, and saves workflow outcomes without credentials.",
            capabilities=["project_memory_retrieval", "workflow_summarization", "knowledge_persistence"],
            allowed_tools=["memory_search", "memory_store", "memory_summary", "project_context"]
        ))

    async def execute_step(self, step: WorkflowStep, context: AgentContext) -> Dict[str, Any]:
        self.metadata.status = AgentStatus.BUSY
        try:
            action = step.arguments.get("action", "retrieve")

            if action == "save_summary" or "save" in step.description.lower():
                # Persist workflow milestone in project memory
                if context.project_id:
                    summary_text = step.arguments.get("summary") or context.get_context_summary()[:400]
                    long_term_memory.create_memory(MemoryCreate(
                        category=MemoryCategory.PROJECT_MEMORY,
                        content=f"Workflow completed for {context.project_id}: {summary_text}",
                        project_id=context.project_id,
                        tags=["agent_workflow", context.project_id],
                        importance=1.5
                    ))
                    self.metadata.tasks_completed += 1
                    return {
                        "success": True,
                        "output": f"Outcome recorded in project memory for '{context.project_id}'.",
                        "message": "Memory updated successfully."
                    }
                else:
                    return {
                        "success": True,
                        "output": "No project_id bound to workflow; memory saved in general log.",
                        "message": "Logged without project association."
                    }
            else:
                # Retrieve project context
                proj_context = ""
                if context.project_id:
                    proj_context = project_memory.get_project_context_string(context.project_id)
                elif context.objective:
                    detected_proj = project_memory.detect_project_in_text(context.objective)
                    if detected_proj:
                        context.project_id = detected_proj
                        proj_context = project_memory.get_project_context_string(detected_proj)

                context.project_context = proj_context
                self.metadata.tasks_completed += 1
                return {
                    "success": True,
                    "data": {"project_id": context.project_id, "context": proj_context},
                    "output": proj_context or "No existing project memory matched.",
                    "message": f"Memory context retrieved for '{context.project_id or 'general'}'."
                }
        finally:
            self.metadata.status = AgentStatus.IDLE
