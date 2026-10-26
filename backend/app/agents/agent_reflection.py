import logging
from typing import Dict, Any, Optional, List
from .agent_schemas import WorkflowStep, ReflectionEvaluation, WorkflowReport, WorkflowStatus, WorkflowPlan
from .agent_context import AgentContext
from app.ai.model_manager import model_manager

logger = logging.getLogger("nova.agents.reflection")

class AgentReflectionEngine:
    """
    Evaluates step and workflow outcomes against ground-truth tool execution evidence.
    Prevents hallucinated success claims and recommends continuation, retry, or pause.
    """

    @classmethod
    async def evaluate_step(
        cls,
        step: WorkflowStep,
        result: Dict[str, Any],
        context: AgentContext
    ) -> ReflectionEvaluation:
        """
        Evaluates an individual step's actual outcome against its expected output.
        """
        tool_success = result.get("success", False)
        error_msg = result.get("error") or ""
        evidence_text = str(result.get("data") or result.get("output") or result.get("message") or "")

        # If tool returned explicit failure
        if not tool_success or error_msg:
            can_retry = step.retry_policy.retry_count < step.retry_policy.max_retries
            return ReflectionEvaluation(
                step_id=step.step_id,
                success=False,
                evidence=f"Execution error: {error_msg or 'Tool reported non-success'}",
                goal_satisfied=False,
                requires_clarification=not can_retry,
                can_proceed=False,
                suggested_action="RETRY" if can_retry else "PAUSE"
            )

        # Ground-truth verification: Ensure output is non-empty and verifiable
        has_verifiable_evidence = len(evidence_text.strip()) > 0
        goal_satisfied = tool_success and has_verifiable_evidence

        return ReflectionEvaluation(
            step_id=step.step_id,
            success=True,
            evidence=evidence_text[:300],
            goal_satisfied=goal_satisfied,
            requires_clarification=False,
            can_proceed=True,
            suggested_action="CONTINUE"
        )

    @classmethod
    async def generate_workflow_report(
        cls,
        plan: WorkflowPlan,
        context: AgentContext,
        duration_seconds: float
    ) -> WorkflowReport:
        """
        Synthesizes a final technical report comparing actual execution evidence against
        the user's original high-level objective.
        """
        total = len(plan.steps)
        successful = sum(1 for s in plan.steps if s.status.value == "COMPLETED")
        failed = sum(1 for s in plan.steps if s.status.value == "FAILED")
        
        evidence_items = list(context.evidence_log)
        unresolved = list(context.unresolved_issues)

        for s in plan.steps:
            if s.error and s.error not in unresolved:
                unresolved.append(f"Step {s.step_id} ({s.description}): {s.error}")

        # Construct structured summary prompt for Ollama
        evidence_block = "\n- ".join(evidence_items) if evidence_items else "No direct evidence collected."
        unresolved_block = "\n- ".join(unresolved) if unresolved else "None"

        summary_prompt = (
            f"ORIGINAL OBJECTIVE: {plan.objective}\n\n"
            f"EXECUTION METRICS:\n"
            f"- Total Steps: {total}\n"
            f"- Successful: {successful}\n"
            f"- Failed/Skipped: {total - successful}\n\n"
            f"VERIFIABLE TOOL EVIDENCE:\n- {evidence_block[:1500]}\n\n"
            f"UNRESOLVED ISSUES:\n- {unresolved_block[:600]}\n\n"
            "Provide a concise, factual executive summary of the workflow. "
            "Highlight what was completed, key findings, and concrete next steps. "
            "Ground every claim strictly in the verifiable evidence above."
        )

        try:
            messages = [
                {"role": "system", "content": "You are NOVA Orchestration Intelligence. Provide factual, evidence-backed workflow reports."},
                {"role": "user", "content": summary_prompt}
            ]
            llm_res = await model_manager.chat(messages=messages, model=model_manager.active_model)
            summary_text = llm_res.get("content", f"Workflow execution completed with {successful}/{total} successful steps.")
        except Exception as e:
            logger.warning(f"Failed to query LLM for report summary: {e}")
            summary_text = f"Workflow completed. {successful} of {total} steps executed successfully."

        return WorkflowReport(
            workflow_id=plan.workflow_id,
            objective=plan.objective,
            status=plan.status,
            duration_seconds=round(duration_seconds, 2),
            total_steps=total,
            successful_steps=successful,
            failed_steps=failed,
            summary=summary_text,
            key_findings=[e[:120] for e in evidence_items[:4]],
            verifiable_evidence=evidence_items,
            unresolved_issues=unresolved,
            project_memory_updated=bool(plan.project_id),
            completed_at=plan.completed_at or ""
        )
