import asyncio
import random
import logging
from typing import Callable, Any, Optional, List
from datetime import datetime

from app.database import db_manager, backup_manager
from app.brain.state_manager import state_manager, NovaState

logger = logging.getLogger("nova.reliability.supervisor")

class SubsystemSupervisor:
    """
    Supervises startup sequencing, stale workflow/task reconciliation,
    approval expiration on restart, and graceful application shutdown.
    """

    def __init__(self):
        self._is_shutting_down = False
        self._background_tasks: List[asyncio.Task] = []

    def register_background_task(self, task: asyncio.Task):
        """Track long-running background tasks for graceful cancellation."""
        self._background_tasks.append(task)
        task.add_done_callback(lambda t: self._background_tasks.remove(t) if t in self._background_tasks else None)

    async def on_startup(self):
        """
        Controlled startup sequence executed during FastAPI lifespan.
        """
        logger.info("Starting NOVA v0.9 Subsystem Supervisor sequence...")
        
        # 1. Database Integrity Verification
        try:
            integrity = db_manager.check_integrity()
            if not integrity.get("healthy"):
                logger.error(f"FATAL: Database integrity failure on startup: {integrity.get('messages')}")
            else:
                logger.info("Database integrity verified successfully.")
                
            # Perform automated pre-startup backup if none exists in last 24h
            backups = backup_manager.list_backups()
            if not backups:
                logger.info("Creating initial database baseline backup...")
                backup_manager.create_backup(trigger="initial_startup", description="Initial database baseline backup")
        except Exception as e:
            logger.error(f"Error during database startup check: {e}")

        # 2. Reconcile Stale Workflows and Expire Pending Approvals
        self._reconcile_stale_workflows()

        # 3. Reconcile Stale Tasks and Expire Task Approvals
        self._reconcile_stale_tasks()

        # 4. Clean up Voice Pending Approvals
        try:
            from app.voice.audio_manager import audio_manager
            audio_manager.pending_voice_task_id = None
            audio_manager.pending_voice_task_expiry = 0.0
            audio_manager.pending_voice_workflow_id = None
            audio_manager.pending_voice_workflow_step_id = None
            audio_manager.pending_voice_workflow_expiry = 0.0
            logger.info("Voice pending approvals cleared for clean session start.")
        except Exception as e:
            logger.debug(f"Voice cleanup note: {e}")

        logger.info("NOVA Subsystem Supervisor startup sequence complete.")

    def _reconcile_stale_workflows(self):
        """
        Detects workflows left in RUNNING or PENDING_APPROVAL from prior sessions
        and marks them safely as CANCELLED/EXPIRED so they never resume without fresh authorization.
        """
        try:
            from app.agents.workflow_logger import workflow_logger
            from app.agents.agent_schemas import WorkflowStatus, WorkflowStepStatus

            workflow_summaries = workflow_logger.list_workflows(limit=100)
            stale_count = 0
            for w_dict in workflow_summaries:
                status_str = w_dict.get("status")
                if status_str in ("RUNNING", "PENDING_APPROVAL"):
                    wf = workflow_logger.get_workflow(w_dict["workflow_id"])
                    if not wf:
                        continue
                    wf.status = WorkflowStatus.CANCELLED
                    wf.requires_approval = False
                    wf.pending_approval_step_id = None
                    wf.approval_reason = "Application restarted. Prior approval expired; fresh user authorization required."
                    wf.completed_at = datetime.now().isoformat()
                    
                    # Also update any pending steps
                    for s in wf.steps:
                        if s.status in (WorkflowStepStatus.RUNNING, WorkflowStepStatus.PENDING_APPROVAL):
                            s.status = WorkflowStepStatus.CANCELLED
                            s.error = "Interrupted by application restart."
                            s.completed_at = datetime.now().isoformat()

                    workflow_logger.save_workflow(wf)
                    stale_count += 1

            if stale_count > 0:
                logger.info(f"Reconciled {stale_count} stale/abandoned workflow(s) on startup.")
        except Exception as e:
            logger.warning(f"Error reconciling stale workflows: {e}")

    def _reconcile_stale_tasks(self):
        """
        Detects tasks left in EXECUTING or PENDING_APPROVAL from prior sessions
        and marks them safely as CANCELLED.
        """
        try:
            from app.tools.execution_logger import execution_logger
            from app.tools.tool_schemas import TaskStatus, StepStatus

            task_summaries = execution_logger.list_tasks(limit=100)
            stale_count = 0
            for t_dict in task_summaries:
                status_str = t_dict.get("status")
                if status_str in ("EXECUTING", "PENDING_APPROVAL"):
                    t = execution_logger.get_task(t_dict["task_id"])
                    if not t:
                        continue
                    t.status = TaskStatus.CANCELLED
                    t.requires_confirmation = False
                    t.confirmation_reason = "Application restarted; approval expired."
                    t.completed_at = datetime.now().isoformat()

                    for s in t.steps:
                        if s.status in (StepStatus.RUNNING, StepStatus.PENDING):
                            s.status = StepStatus.CANCELLED
                            s.completed_at = datetime.now().isoformat()

                    execution_logger.save_task(t)
                    stale_count += 1

            if stale_count > 0:
                logger.info(f"Reconciled {stale_count} stale/abandoned task(s) on startup.")
        except Exception as e:
            logger.warning(f"Error reconciling stale tasks: {e}")

    async def on_shutdown(self):
        """
        Controlled shutdown sequence executed during FastAPI lifespan termination.
        """
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        logger.info("Executing controlled NOVA shutdown sequence...")

        # 1. Stop Automation Engine
        try:
            from app.automation import automation_manager
            logger.info("Halting automation scheduler...")
            automation_manager.shutdown()
        except Exception as e:
            logger.warning(f"Error halting automation manager: {e}")

        # 2. Stop Audio Manager & Voice Pipeline
        try:
            from app.voice.audio_manager import audio_manager
            logger.info("Stopping audio manager and releasing sounddevice stream...")
            audio_manager.stop()
        except Exception as e:
            logger.warning(f"Error stopping audio manager: {e}")

        # 3. Disconnect WebSocket Subscribers
        try:
            from app.voice.audio_manager import audio_manager
            if audio_manager._ws_subscribers:
                logger.info(f"Disconnecting {len(audio_manager._ws_subscribers)} WebSocket client(s)...")
                for ws in list(audio_manager._ws_subscribers):
                    try:
                        await ws.close(code=1000, reason="Server shutting down")
                    except Exception:
                        pass
                audio_manager._ws_subscribers.clear()
        except Exception as e:
            logger.warning(f"Error disconnecting WebSockets: {e}")

        # 4. Cancel Remaining Background Tasks
        if self._background_tasks:
            logger.info(f"Cancelling {len(self._background_tasks)} background task(s)...")
            for t in self._background_tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()

        state_manager.set_state(NovaState.IDLE, "NOVA SYSTEM OFFLINE")
        logger.info("NOVA shutdown sequence completed successfully.")

    @staticmethod
    async def retry_with_backoff(
        func: Callable[[], Any],
        max_retries: int = 3,
        initial_delay: float = 0.5,
        backoff_multiplier: float = 2.0,
        max_delay: float = 5.0,
        retry_exceptions: tuple = (Exception,)
    ) -> Any:
        """
        Bounded retry utility with exponential backoff and jitter.
        Prevents infinite retry storms.
        """
        delay = initial_delay
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()
            except retry_exceptions as e:
                last_exception = e
                if attempt == max_retries:
                    logger.warning(f"Retry failed after {max_retries} attempts: {e}")
                    raise e
                # Jitter between 0% and 50% of delay
                jitter = random.uniform(0, 0.5 * delay)
                sleep_time = min(delay + jitter, max_delay)
                logger.debug(f"Attempt {attempt}/{max_retries} failed ({e}). Retrying in {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)
                delay *= backoff_multiplier

        if last_exception:
            raise last_exception

subsystem_supervisor = SubsystemSupervisor()
