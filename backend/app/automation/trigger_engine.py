import logging
import psutil
from typing import List, Dict, Any, Optional
from datetime import datetime
from .automation_schemas import TriggerType, AutomationRule, AutomationStatus
from .automation_logger import automation_logger
from .automation_permissions import automation_permissions

logger = logging.getLogger("nova.automation.triggers")

class TriggerEngine:
    """
    Evaluates event-driven automation triggers without expensive polling:
    - Host system resource thresholds (CPU/RAM)
    - Application launch/exit events
    - Workflow completion/failure events
    - Overdue tasks and deadlines
    Strictly follows privacy and security guidelines:
    NO secret keylogging, NO clipboard monitoring, NO hidden screen capture.
    """

    def __init__(self):
        self._last_known_processes = set()

    def evaluate_system_thresholds(self, rules: List[AutomationRule]) -> List[AutomationRule]:
        """Evaluates rules configured for system metric thresholds."""
        triggered = []
        cpu = None
        mem = None

        for rule in rules:
            if not rule.enabled or rule.status != AutomationStatus.ACTIVE:
                continue
            cfg = rule.trigger_config
            if cfg.trigger_type != TriggerType.SYSTEM_THRESHOLD or not cfg.system_metric:
                continue

            # Lazily sample metrics once if needed
            if cpu is None:
                cpu = psutil.cpu_percent(interval=0.0)
            if mem is None:
                mem = psutil.virtual_memory().percent

            current_val = cpu if "cpu" in cfg.system_metric.lower() else mem
            threshold = cfg.metric_threshold or 85.0
            op = cfg.metric_operator or ">"

            is_match = False
            if op == ">" and current_val > threshold:
                is_match = True
            elif op == ">=" and current_val >= threshold:
                is_match = True
            elif op == "<" and current_val < threshold:
                is_match = True
            elif op == "<=" and current_val <= threshold:
                is_match = True

            if is_match:
                logger.info(f"Threshold trigger matched for rule '{rule.id}': {cfg.system_metric}={current_val} {op} {threshold}")
                triggered.append(rule)

        return triggered

    def evaluate_workflow_event(self, rules: List[AutomationRule], workflow_id: str, outcome: str) -> List[AutomationRule]:
        """Evaluates rules triggered by another workflow completing or failing."""
        triggered = []
        for rule in rules:
            if not rule.enabled or rule.status != AutomationStatus.ACTIVE:
                continue
            cfg = rule.trigger_config
            if cfg.trigger_type != TriggerType.WORKFLOW_EVENT:
                continue

            # Check outcome match
            if cfg.workflow_outcome and cfg.workflow_outcome.upper() != outcome.upper():
                continue

            # Check pattern match if specified
            if cfg.workflow_id_pattern and cfg.workflow_id_pattern not in workflow_id:
                continue

            logger.info(f"Workflow event trigger matched for rule '{rule.id}': wf={workflow_id}, outcome={outcome}")
            triggered.append(rule)

        return triggered

    def evaluate_app_event(self, rules: List[AutomationRule], app_name: str, action: str) -> List[AutomationRule]:
        """Evaluates rules triggered by an application launch or closure."""
        triggered = []
        norm_app = app_name.lower().replace(".exe", "")
        for rule in rules:
            if not rule.enabled or rule.status != AutomationStatus.ACTIVE:
                continue
            cfg = rule.trigger_config
            if cfg.trigger_type != TriggerType.APP_EVENT or not cfg.app_name:
                continue

            rule_app = cfg.app_name.lower().replace(".exe", "")
            rule_act = (cfg.app_action or "launched").lower()

            if rule_app in norm_app and rule_act == action.lower():
                logger.info(f"App event trigger matched for rule '{rule.id}': {app_name} {action}")
                triggered.append(rule)

        return triggered

    def evaluate_overdue_tasks(self, rules: List[AutomationRule]) -> List[AutomationRule]:
        """Evaluates rules triggered by overdue memory tasks or reminders."""
        triggered = []
        now_iso = datetime.utcnow().isoformat()
        
        # Check if there are overdue pending reminders
        reminders = automation_logger.list_reminders(pending_only=True)
        overdue_items = [r for r in reminders if r.due_at and r.due_at <= now_iso]

        if not overdue_items:
            return []

        for rule in rules:
            if not rule.enabled or rule.status != AutomationStatus.ACTIVE:
                continue
            if rule.trigger_config.trigger_type == TriggerType.TASK_OVERDUE:
                logger.info(f"Task overdue trigger matched for rule '{rule.id}' ({len(overdue_items)} items overdue)")
                triggered.append(rule)

        return triggered

# Global singleton
trigger_engine = TriggerEngine()
