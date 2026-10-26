import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from .automation_schemas import (
    AutomationRule, AutomationCreate, AutomationUpdate,
    AutomationStatus, AutomationActionType, TriggerType
)
from .automation_logger import automation_logger

logger = logging.getLogger("nova.automation.registry")

class AutomationRegistry:
    """
    Manages in-memory registration and CRUD operations for personal automation rules.
    Synchronizes persistently with SQLite through AutomationLogger.
    """

    def __init__(self):
        self._rules_cache: Dict[str, AutomationRule] = {}
        self.reload()

    def reload(self):
        """Loads all rules from persistent database into in-memory cache."""
        rules = automation_logger.list_automations()
        self._rules_cache = {r.id: r for r in rules}
        logger.info(f"Loaded {len(self._rules_cache)} automations into registry cache.")

    def create_automation(self, data: AutomationCreate) -> AutomationRule:
        rule_id = data.id or f"auto_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.utcnow().isoformat()

        rule = AutomationRule(
            id=rule_id,
            name=data.name,
            description=data.description or "",
            enabled=data.enabled,
            status=AutomationStatus.ACTIVE if data.enabled else AutomationStatus.DISABLED,
            autonomy_level=data.autonomy_level,
            trigger_config=data.trigger_config,
            action_type=data.action_type,
            workflow_objective=data.workflow_objective,
            action_payload=data.action_payload or {},
            retry_policy=data.retry_policy,
            created_at=now_iso,
            updated_at=now_iso
        )

        automation_logger.save_automation(rule)
        self._rules_cache[rule.id] = rule
        return rule

    def get_automation(self, automation_id: str) -> Optional[AutomationRule]:
        return self._rules_cache.get(automation_id) or automation_logger.get_automation(automation_id)

    def list_automations(self) -> List[AutomationRule]:
        return list(self._rules_cache.values())

    def update_automation(self, automation_id: str, updates: AutomationUpdate) -> Optional[AutomationRule]:
        rule = self.get_automation(automation_id)
        if not rule:
            return None

        update_dict = updates.dict(exclude_unset=True)
        for key, val in update_dict.items():
            if val is not None:
                setattr(rule, key, val)

        rule.updated_at = datetime.utcnow().isoformat()
        if updates.enabled is not None:
            rule.status = AutomationStatus.ACTIVE if updates.enabled else AutomationStatus.DISABLED

        automation_logger.save_automation(rule)
        self._rules_cache[rule.id] = rule
        return rule

    def delete_automation(self, automation_id: str) -> bool:
        if automation_id in self._rules_cache:
            del self._rules_cache[automation_id]
        return automation_logger.delete_automation(automation_id)

    def set_enabled(self, automation_id: str, enabled: bool) -> Optional[AutomationRule]:
        rule = self.get_automation(automation_id)
        if not rule:
            return None
        rule.enabled = enabled
        rule.status = AutomationStatus.ACTIVE if enabled else AutomationStatus.DISABLED
        rule.updated_at = datetime.utcnow().isoformat()
        automation_logger.save_automation(rule)
        self._rules_cache[rule.id] = rule
        return rule

# Global singleton
automation_registry = AutomationRegistry()
