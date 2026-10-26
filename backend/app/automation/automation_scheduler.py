import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from .automation_schemas import (
    AutomationRule, AutomationStatus, TriggerType, ScheduleType, ScheduleConfig
)
from .automation_logger import automation_logger
from .automation_permissions import automation_permissions
from .automation_executor import automation_executor

logger = logging.getLogger("nova.automation.scheduler")

class AutomationScheduler:
    """
    Lightweight, timezone-aware local scheduler for NOVA v0.7:
    - Handles ONCE, DAILY, WEEKLY, RECURRING intervals
    - Respects user-defined timezones
    - Recovers gracefully from missed execution windows on reboot
    - Guarantees zero duplicate executions and no heavy background polling
    """

    def __init__(self):
        self._loop_task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._check_interval: float = 5.0 # Check every 5 seconds for due tasks

    def start(self):
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._scheduler_loop())
        logger.info("AutomationScheduler started.")

    def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None
        logger.info("AutomationScheduler stopped.")

    def compute_next_run(self, rule: AutomationRule, from_dt: Optional[datetime] = None) -> Optional[str]:
        """Calculates the next ISO UTC datetime for a rule based on its schedule config."""
        cfg = rule.trigger_config
        if cfg.trigger_type != TriggerType.SCHEDULE or not cfg.schedule:
            return None

        sched = cfg.schedule
        tz_str = sched.timezone or "UTC"
        try:
            tz = ZoneInfo(tz_str)
        except Exception:
            tz = timezone.utc

        now_utc = from_dt or datetime.now(timezone.utc)
        now_local = now_utc.astimezone(tz)

        if sched.schedule_type == ScheduleType.ONCE:
            if sched.specific_datetime:
                try:
                    dt = datetime.fromisoformat(sched.specific_datetime.replace("Z", "+00:00"))
                    if dt > now_utc:
                        return dt.astimezone(timezone.utc).isoformat()
                    return None
                except Exception:
                    return None
            return None

        elif sched.schedule_type == ScheduleType.RECURRING:
            interval = sched.interval_seconds or 3600
            next_dt = now_utc + timedelta(seconds=interval)
            return next_dt.isoformat()

        elif sched.schedule_type == ScheduleType.DAILY:
            # Parse HH:MM
            time_str = sched.time_of_day or "08:00"
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0

            candidate = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now_local:
                candidate += timedelta(days=1)
            return candidate.astimezone(timezone.utc).isoformat()

        elif sched.schedule_type == ScheduleType.WEEKLY:
            time_str = sched.time_of_day or "10:00"
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            target_days = sched.days_of_week or [0] # 0 = Monday, 5 = Saturday, 6 = Sunday

            candidate = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # Find closest future day in target_days
            for day_offset in range(0, 8):
                test_dt = candidate + timedelta(days=day_offset)
                if test_dt.weekday() in target_days and test_dt > now_local:
                    return test_dt.astimezone(timezone.utc).isoformat()

            # Default to 7 days from now
            candidate += timedelta(days=7)
            return candidate.astimezone(timezone.utc).isoformat()

        return None

    def handle_restart_recovery(self, rules: List[AutomationRule]):
        """
        Runs on startup. Inspects next_run_at and last_run_at for missed runs.
        Catches up gracefully without duplicating executions.
        """
        now_utc = datetime.now(timezone.utc)
        logger.info(f"Running startup schedule recovery check for {len(rules)} automation rules...")

        for rule in rules:
            if not rule.enabled or rule.status != AutomationStatus.ACTIVE:
                continue

            if rule.trigger_config.trigger_type != TriggerType.SCHEDULE:
                continue

            # If rule has no next_run_at, initialize it
            if not rule.next_run_at:
                rule.next_run_at = self.compute_next_run(rule, now_utc)
                automation_logger.save_automation(rule)
                continue

            try:
                next_dt = datetime.fromisoformat(rule.next_run_at.replace("Z", "+00:00"))
                # If scheduled time passed while offline:
                if next_dt <= now_utc:
                    # Check if executed recently to prevent duplicate
                    should_catchup = True
                    if rule.last_run_at:
                        last_dt = datetime.fromisoformat(rule.last_run_at.replace("Z", "+00:00"))
                        # If already ran within the past 10 minutes, do not re-run
                        if (now_utc - last_dt).total_seconds() < 600:
                            should_catchup = False

                    if should_catchup and not automation_permissions.is_globally_paused():
                        logger.info(f"Executing missed scheduled automation on reboot: '{rule.id}'")
                        asyncio.create_task(automation_executor.execute_rule(rule))

                    # Recompute future next_run_at
                    rule.next_run_at = self.compute_next_run(rule, now_utc)
                    automation_logger.save_automation(rule)
            except Exception as e:
                logger.error(f"Error recovering rule '{rule.id}': {e}")
                rule.next_run_at = self.compute_next_run(rule, now_utc)
                automation_logger.save_automation(rule)

    async def _scheduler_loop(self):
        """Asynchronous low-overhead heartbeat loop."""
        while self._running:
            try:
                if not automation_permissions.is_globally_paused():
                    await self._evaluate_due_schedules()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)

            try:
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break

    async def _evaluate_due_schedules(self):
        """Checks rules whose next_run_at is <= current time."""
        now_utc = datetime.now(timezone.utc)
        rules = automation_logger.list_automations()

        for rule in rules:
            if not rule.enabled or rule.status != AutomationStatus.ACTIVE:
                continue

            if rule.trigger_config.trigger_type != TriggerType.SCHEDULE:
                continue

            if not rule.next_run_at:
                rule.next_run_at = self.compute_next_run(rule, now_utc)
                automation_logger.save_automation(rule)
                continue

            try:
                next_dt = datetime.fromisoformat(rule.next_run_at.replace("Z", "+00:00"))
                if next_dt <= now_utc:
                    # Advance next_run_at BEFORE execution to prevent duplicate triggers
                    rule.next_run_at = self.compute_next_run(rule, now_utc)
                    automation_logger.save_automation(rule)

                    logger.info(f"Scheduled time reached for automation: '{rule.id}'. Dispatching...")
                    asyncio.create_task(automation_executor.execute_rule(rule))
            except Exception as e:
                logger.error(f"Failed evaluating schedule for rule '{rule.id}': {e}")

# Global singleton
automation_scheduler = AutomationScheduler()
