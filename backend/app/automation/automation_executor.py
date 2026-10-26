import asyncio
import logging
import os
import subprocess
import shlex
import psutil
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.config import settings
from .automation_schemas import (
    AutomationRule, AutomationActionType, NotificationType,
    AutonomyLevel, RetryPolicy
)
from .automation_logger import automation_logger
from .automation_permissions import automation_permissions
from .notification_manager import notification_manager

logger = logging.getLogger("nova.automation.executor")

class AutomationExecutor:
    """
    Executes automation actions while strictly honoring:
    - Autonomy levels & v0.4 security boundaries
    - v0.6 agent orchestrator reuse (max 2 parallel read-only workflows)
    - Verifiable evidence-based Daily Briefing & Project Health checks
    - Bounded retries and duplicate execution prevention
    """

    def __init__(self):
        # Concurrency limiter: max 2 parallel read-only automation workflows
        self._concurrency_semaphore = asyncio.Semaphore(2)
        self._active_runs: Dict[str, asyncio.Task] = {}

    def is_rule_running(self, automation_id: str) -> bool:
        task = self._active_runs.get(automation_id)
        return task is not None and not task.done()

    async def execute_rule(self, rule: AutomationRule) -> Dict[str, Any]:
        """Entry point for executing an automation rule safely."""
        # 1. Global pause and permission check
        can_run, reason = automation_permissions.can_rule_execute(rule)
        if not can_run:
            logger.warning(f"Automation '{rule.id}' cannot execute: {reason}")
            automation_logger.log_execution(
                automation_id=rule.id,
                trigger_type=rule.trigger_config.trigger_type.value,
                action_type=rule.action_type.value,
                status="SKIPPED",
                started_at=datetime.utcnow().isoformat(),
                completed_at=datetime.utcnow().isoformat(),
                result_summary=reason
            )
            return {"status": "SKIPPED", "reason": reason}

        # 2. Prevent duplicate execution
        if self.is_rule_running(rule.id):
            logger.info(f"Automation '{rule.id}' is already executing. Duplicate run prevented.")
            return {"status": "SKIPPED", "reason": "Already running"}

        # 3. Schedule execution as bounded async task
        task = asyncio.create_task(self._run_with_retries(rule))
        self._active_runs[rule.id] = task
        try:
            result = await task
            return result
        finally:
            self._active_runs.pop(rule.id, None)

    async def _run_with_retries(self, rule: AutomationRule) -> Dict[str, Any]:
        retries = 0
        max_retries = rule.retry_policy.max_retries
        last_error = None
        started_at = datetime.utcnow().isoformat()

        while retries <= max_retries:
            try:
                logger.info(f"Executing automation '{rule.id}' (Attempt {retries + 1}/{max_retries + 1})...")
                res = await self._dispatch_action(rule)
                
                # Update rule statistics
                rule.last_run_at = datetime.utcnow().isoformat()
                rule.run_count += 1
                automation_logger.save_automation(rule)

                automation_logger.log_execution(
                    automation_id=rule.id,
                    trigger_type=rule.trigger_config.trigger_type.value,
                    action_type=rule.action_type.value,
                    status=res.get("status", "SUCCESS"),
                    started_at=started_at,
                    completed_at=datetime.utcnow().isoformat(),
                    result_summary=res.get("summary", "Execution completed successfully."),
                    workflow_id=res.get("workflow_id")
                )
                return res

            except Exception as e:
                last_error = str(e)
                logger.error(f"Error during execution of automation '{rule.id}': {e}", exc_info=True)
                # If critical error (e.g. security validation, value error), stop immediately
                if rule.retry_policy.stop_on_critical and isinstance(e, (ValueError, PermissionError, FileNotFoundError)):
                    logger.warning(f"Critical error on automation '{rule.id}', aborting retries.")
                    break

                retries += 1
                if retries <= max_retries:
                    delay = min(rule.retry_policy.retry_delay_seconds, 60)
                    logger.info(f"Retrying automation '{rule.id}' in {delay} seconds...")
                    await asyncio.sleep(delay)

        # Max retries exceeded
        rule.failure_count += 1
        rule.last_run_at = datetime.utcnow().isoformat()
        automation_logger.save_automation(rule)

        automation_logger.log_execution(
            automation_id=rule.id,
            trigger_type=rule.trigger_config.trigger_type.value,
            action_type=rule.action_type.value,
            status="FAILED",
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat(),
            error_message=f"Failed after {max_retries + 1} attempts. Last error: {last_error}"
        )

        notification_manager.send_notification(
            notif_type=NotificationType.WORKFLOW_FAILED,
            title=f"Automation Failed: {rule.name}",
            message=f"Routine encountered repeated errors: {last_error}",
            data={"automation_id": rule.id, "error": last_error}
        )

        return {"status": "FAILED", "error": last_error}

    async def _dispatch_action(self, rule: AutomationRule) -> Dict[str, Any]:
        """Dispatches action to the appropriate specialized subsystem."""
        if rule.action_type == AutomationActionType.DAILY_BRIEFING:
            return await self._execute_daily_briefing(rule)
        elif rule.action_type == AutomationActionType.PROJECT_HEALTH:
            return await self._execute_project_health(rule)
        elif rule.action_type == AutomationActionType.REMINDER:
            return await self._execute_reminder_check(rule)
        elif rule.action_type == AutomationActionType.NOTIFICATION:
            return await self._execute_simple_notification(rule)
        elif rule.action_type == AutomationActionType.WORKFLOW:
            return await self._execute_orchestrator_workflow(rule)
        else:
            raise ValueError(f"Unsupported action type: {rule.action_type}")

    # ==================== 1. DAILY BRIEFING AGENT ====================

    async def _execute_daily_briefing(self, rule: AutomationRule) -> Dict[str, Any]:
        """
        Compiles an evidence-based daily briefing:
        - Pending memory tasks & project updates
        - Active reminders and deadlines
        - Recent workflow outcomes
        - Host system resource telemetry
        No facts are fabricated.
        """
        sections = []

        # 1. Host Telemetry (Actual psutil measurements)
        cpu_usage = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        sections.append(f"System Telemetry: CPU at {cpu_usage:.1f}%, RAM utilization at {mem.percent:.1f}%.")

        # 2. Reminders & Deadlines (from SQLite)
        reminders = automation_logger.list_reminders(pending_only=True)
        if reminders:
            sections.append(f"Active Reminders ({len(reminders)} pending):")
            for rem in reminders[:4]:
                due_str = f" [Due: {rem.due_at}]" if rem.due_at else ""
                sections.append(f"  • {rem.text}{due_str}")
        else:
            sections.append("Active Reminders: No pending tasks or reminders scheduled.")

        # 3. Project Memory Updates
        try:
            from app.memory.project_memory import project_memory
            projects = project_memory.list_projects()
            if projects:
                proj_summaries = []
                for p in projects[:3]:
                    pending = len(p.pending_tasks)
                    proj_summaries.append(f"{p.name} ({pending} pending tasks)")
                sections.append(f"Active Projects: {', '.join(proj_summaries)}.")
        except Exception as e:
            logger.debug(f"Could not load project memory for briefing: {e}")

        # 4. Recent Workflow History
        try:
            from app.agents.workflow_logger import workflow_logger
            recent_wfs = workflow_logger.list_workflows(limit=5)
            succeeded = sum(1 for w in recent_wfs if w.get("status") == "COMPLETED")
            failed = sum(1 for w in recent_wfs if w.get("status") == "FAILED")
            sections.append(f"Recent Workflows: {len(recent_wfs)} executed ({succeeded} succeeded, {failed} failed).")
        except Exception as e:
            logger.debug(f"Could not load workflow history for briefing: {e}")

        summary_text = "\n".join(sections)
        title = f"Daily Briefing - {datetime.utcnow().strftime('%A, %b %d')}"

        # Dispatch notification
        speak = bool(rule.action_payload.get("speak_aloud", False))
        notification_manager.send_notification(
            notif_type=NotificationType.DAILY_BRIEFING,
            title=title,
            message=summary_text,
            data={"rule_id": rule.id},
            speak_aloud=speak
        )

        return {
            "status": "SUCCESS",
            "summary": f"Daily briefing generated with {len(sections)} data sections.",
            "content": summary_text
        }

    # ==================== 2. PROJECT HEALTH MONITOR ====================

    async def _execute_project_health(self, rule: AutomationRule) -> Dict[str, Any]:
        """
        Inspects project workspace, verifies repository status, and runs approved test suites safely.
        Strictly forbids arbitrary shell execution or file modifications.
        """
        payload = rule.action_payload or {}
        workspace_path = payload.get("workspace_path") or settings.ROOT_DIR

        # Security check: resolve workspace path
        norm_workspace = os.path.abspath(workspace_path)
        if not os.path.exists(norm_workspace):
            raise FileNotFoundError(f"Registered workspace does not exist: {workspace_path}")

        report_lines = [f"Project Health Assessment: {norm_workspace}"]

        # 1. Inspect Project Configuration
        has_git = os.path.exists(os.path.join(norm_workspace, ".git"))
        has_backend = os.path.exists(os.path.join(norm_workspace, "backend"))
        has_frontend = os.path.exists(os.path.join(norm_workspace, "apps", "desktop"))
        report_lines.append(f"Structure: Git={'Yes' if has_git else 'No'}, Backend={'Yes' if has_backend else 'No'}, Frontend={'Yes' if has_frontend else 'No'}.")

        # 2. Git Status Check (Safe read-only check)
        git_status_str = "Git repository clean or unavailable."
        if has_git:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "git", "status", "--short",
                    cwd=norm_workspace,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
                changes = stdout.decode().strip().splitlines()
                if changes:
                    git_status_str = f"Working Tree: {len(changes)} modified/untracked files detected."
                else:
                    git_status_str = "Working Tree: Clean, all changes committed."
            except Exception as e:
                git_status_str = f"Git status inspection note: {e}"
        report_lines.append(git_status_str)

        # 3. Approved Test Runner Execution (if configured)
        test_run_success = True
        test_output_summary = "No automated tests requested."
        if payload.get("run_tests", False):
            raw_test_cmd = payload.get("test_command", "pytest backend/tests/test_health.py -q")
            # Strict validation: Only approved test runner prefixes allowed, no chaining
            valid_prefixes = ["pytest", "python -m unittest", "python -m pytest", "npm test"]
            if any(forbidden in raw_test_cmd for forbidden in [";", "&&", "||", "|", ">", "<", "`", "$", "rm", "del", "curl"]):
                raise ValueError(f"Unsafe command characters detected in test_command: {raw_test_cmd}")

            if not any(raw_test_cmd.strip().startswith(prefix) for prefix in valid_prefixes):
                raise ValueError(f"Disallowed test runner: {raw_test_cmd}. Must start with an approved test runner.")

            cmd_tokens = shlex.split(raw_test_cmd)
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd_tokens,
                    cwd=norm_workspace,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=45.0)
                exit_code = proc.returncode
                test_run_success = (exit_code == 0)
                out_snippet = stdout.decode().strip()[-300:] if stdout else ""
                test_output_summary = f"Test Suite Exit Code {exit_code}: {out_snippet}"
            except asyncio.TimeoutError:
                test_run_success = False
                test_output_summary = "Test suite timed out after 45 seconds."
            except Exception as e:
                test_run_success = False
                test_output_summary = f"Test execution error: {e}"

        report_lines.append(f"Test Execution: {test_output_summary}")
        full_report = "\n".join(report_lines)

        status_flag = "HEALTHY" if test_run_success else "WARNING"
        title = f"Project Health Report [{status_flag}]: {os.path.basename(norm_workspace)}"
        
        notification_manager.send_notification(
            notif_type=NotificationType.PROJECT_HEALTH_REPORT,
            title=title,
            message=full_report,
            data={"workspace": norm_workspace, "healthy": test_run_success}
        )

        return {
            "status": "SUCCESS" if test_run_success else "WARNING",
            "summary": f"Health assessment complete. Status: {status_flag}.",
            "report": full_report
        }

    # ==================== 3. SMART REMINDERS ====================

    async def _execute_reminder_check(self, rule: AutomationRule) -> Dict[str, Any]:
        """Checks pending reminders and notifies user of scheduled items."""
        reminders = automation_logger.list_reminders(pending_only=True)
        if not reminders:
            return {"status": "SUCCESS", "summary": "No pending reminders to deliver."}

        lines = [f"• {r.text} (ID: {r.id})" for r in reminders[:5]]
        msg = f"You have {len(reminders)} pending reminder(s):\n" + "\n".join(lines)

        speak = bool(rule.action_payload.get("speak_aloud", False))
        notification_manager.send_notification(
            notif_type=NotificationType.REMINDER,
            title="NOVA Task Reminder",
            message=msg,
            data={"pending_count": len(reminders)},
            speak_aloud=speak
        )

        return {
            "status": "SUCCESS",
            "summary": f"Delivered reminder alert for {len(reminders)} items."
        }

    # ==================== 4. SIMPLE NOTIFICATION ====================

    async def _execute_simple_notification(self, rule: AutomationRule) -> Dict[str, Any]:
        title = rule.action_payload.get("title", rule.name)
        message = rule.action_payload.get("message", rule.description)
        notification_manager.send_notification(
            notif_type=NotificationType.REMINDER,
            title=title,
            message=message,
            data={"rule_id": rule.id}
        )
        return {"status": "SUCCESS", "summary": f"Notification '{title}' delivered."}

    # ==================== 5. AGENT ORCHESTRATOR WORKFLOW ====================

    async def _execute_orchestrator_workflow(self, rule: AutomationRule) -> Dict[str, Any]:
        """
        Dispatches workflow via v0.6 AgentOrchestrator without creating a second workflow engine.
        Respects max 2 parallel read-only workflows and human confirmation gates.
        """
        from app.agents.agent_orchestrator import agent_orchestrator
        from app.agents.agent_schemas import WorkflowStatus

        objective = rule.workflow_objective or rule.description
        if not objective:
            raise ValueError(f"Automation '{rule.id}' has no workflow_objective defined.")

        async with self._concurrency_semaphore:
            logger.info(f"Dispatching orchestrator workflow for automation '{rule.id}': '{objective}'")
            plan = await agent_orchestrator.plan_workflow(objective, project_id=rule.trigger_config.project_id)

            # Check if workflow requires human approval
            if plan.requires_approval:
                plan.status = WorkflowStatus.PENDING_APPROVAL
                from app.agents.workflow_logger import workflow_logger
                workflow_logger.save_workflow(plan)

                notification_manager.send_notification(
                    notif_type=NotificationType.APPROVAL_REQUIRED,
                    title="Workflow Approval Required",
                    message=f"Automation '{rule.name}' formulated plan '{objective}'. Step {plan.pending_approval_step_id} requires confirmation.",
                    data={"workflow_id": plan.workflow_id, "step_id": plan.pending_approval_step_id}
                )
                return {
                    "status": "REQUIRES_APPROVAL",
                    "workflow_id": plan.workflow_id,
                    "summary": f"Workflow planned with {len(plan.steps)} steps; paused awaiting confirmation."
                }

            # Execute safe workflow
            exec_res = await agent_orchestrator.execute_workflow(plan)
            status_str = "SUCCESS" if exec_res.status == WorkflowStatus.COMPLETED else "FAILED"
            return {
                "status": status_str,
                "workflow_id": exec_res.workflow_id,
                "summary": f"Workflow finished with status: {exec_res.status.value}"
            }

# Global singleton
automation_executor = AutomationExecutor()
