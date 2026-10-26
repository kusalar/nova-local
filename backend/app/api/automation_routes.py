from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
import logging

from app.automation import (
    automation_manager,
    AutomationRule,
    AutomationCreate,
    AutomationUpdate,
    AutomationHistoryRecord,
    NotificationItem,
    ReminderItem,
    ReminderCreate,
    AutomationStatusResponse,
)

logger = logging.getLogger("nova.api.automation")
router = APIRouter(tags=["Automations & Intelligence"])

# ==================== AUTOMATIONS CRUD ====================

@router.get("/automations", response_model=List[AutomationRule])
async def list_automations():
    """Retrieve all configured automation rules."""
    return automation_manager.list_automations()

@router.post("/automations", response_model=AutomationRule)
async def create_automation(data: AutomationCreate):
    """Create a new proactive automation rule."""
    try:
        return automation_manager.create_automation(data)
    except Exception as e:
        logger.error(f"Failed to create automation: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/automations/{automation_id}", response_model=AutomationRule)
async def get_automation(automation_id: str):
    """Get details of a specific automation rule."""
    rule = automation_manager.get_automation(automation_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation not found")
    return rule

@router.patch("/automations/{automation_id}", response_model=AutomationRule)
async def update_automation(automation_id: str, updates: AutomationUpdate):
    """Edit an existing automation rule."""
    rule = automation_manager.update_automation(automation_id, updates)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation not found")
    return rule

@router.delete("/automations/{automation_id}")
async def delete_automation(automation_id: str):
    """Delete an automation rule and its associated history."""
    success = automation_manager.delete_automation(automation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Automation not found")
    return {"status": "deleted", "id": automation_id}

@router.post("/automations/{automation_id}/enable", response_model=AutomationRule)
async def enable_automation(automation_id: str):
    """Enable a scheduled or event-driven automation rule."""
    rule = automation_manager.enable_automation(automation_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation not found")
    return rule

@router.post("/automations/{automation_id}/disable", response_model=AutomationRule)
async def disable_automation(automation_id: str):
    """Disable an automation rule."""
    rule = automation_manager.disable_automation(automation_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation not found")
    return rule

@router.post("/automations/{automation_id}/run")
async def run_automation(automation_id: str):
    """Manually trigger immediate execution of an automation rule."""
    try:
        result = await automation_manager.run_automation_now(automation_id)
        return {"status": "dispatched", "result": result}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error executing automation '{automation_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/automations/{automation_id}/history", response_model=List[AutomationHistoryRecord])
async def get_automation_history(automation_id: str, limit: int = Query(default=50, ge=1, le=200)):
    """Retrieve execution audit logs for a specific automation rule."""
    return automation_manager.get_history(automation_id=automation_id, limit=limit)

# ==================== GLOBAL STATUS & CONTROLS ====================

@router.get("/automation/status", response_model=AutomationStatusResponse)
async def get_automation_status():
    """Retrieve high-level status of the automation engine."""
    return automation_manager.get_status()

@router.post("/automation/pause-all")
async def pause_all_automations():
    """Globally pause all automation triggers and scheduled runs."""
    automation_manager.pause_all()
    return {"status": "paused", "message": "All automations globally paused."}

@router.post("/automation/resume-all")
async def resume_all_automations():
    """Resume all automation triggers and schedules."""
    automation_manager.resume_all()
    return {"status": "active", "message": "Global automation pause removed."}

@router.get("/automation/templates")
async def get_templates():
    """Fetch pre-configured routine templates for common personal automations."""
    return automation_manager.get_templates()

# ==================== NOTIFICATIONS ====================

@router.get("/notifications", response_model=List[NotificationItem])
async def list_notifications(unread_only: bool = Query(default=False), limit: int = Query(default=50, ge=1, le=100)):
    """Retrieve in-app notifications."""
    return automation_manager.list_notifications(unread_only=unread_only, limit=limit)

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int):
    """Mark a notification as read."""
    success = automation_manager.mark_notification_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "updated", "id": notification_id, "read": True}

@router.post("/notifications/{notification_id}/dismiss")
async def dismiss_notification(notification_id: int):
    """Dismiss a notification from the active notification list."""
    success = automation_manager.dismiss_notification(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "dismissed", "id": notification_id}

@router.post("/notifications/{notification_id}/snooze")
async def snooze_notification(notification_id: int, minutes: Optional[int] = Body(default=15, embed=True)):
    """Snooze a notification for a specified duration in minutes."""
    success = automation_manager.snooze_notification(notification_id, minutes=minutes)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "snoozed", "id": notification_id, "minutes": minutes}

@router.get("/notifications/preferences")
async def get_notification_preferences():
    """Retrieve notification delivery preferences."""
    return automation_manager.notifications.get_preferences()

@router.patch("/notifications/preferences")
async def update_notification_preferences(data: Dict[str, Any]):
    """Update notification delivery preferences (TTS, desktop alerts, snooze defaults)."""
    return automation_manager.notifications.update_preferences(data)

# ==================== REMINDERS ====================

@router.get("/reminders", response_model=List[ReminderItem])
async def list_reminders(pending_only: bool = Query(default=True)):
    """List pending or all smart reminders."""
    return automation_manager.list_reminders(pending_only=pending_only)

@router.post("/reminders", response_model=ReminderItem)
async def create_reminder(data: ReminderCreate):
    """Create a new smart reminder."""
    return automation_manager.add_reminder(data)

@router.post("/reminders/{reminder_id}/complete")
async def complete_reminder(reminder_id: int):
    """Mark a reminder as completed."""
    success = automation_manager.complete_reminder(reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"status": "completed", "id": reminder_id}

@router.post("/reminders/{reminder_id}/snooze")
async def snooze_reminder(reminder_id: int, until_iso: str = Body(..., embed=True)):
    """Snooze a reminder until a specified ISO timestamp."""
    success = automation_manager.snooze_reminder(reminder_id, until_iso=until_iso)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"status": "snoozed", "id": reminder_id, "until": until_iso}

@router.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int):
    """Delete a reminder."""
    success = automation_manager.delete_reminder(reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"status": "deleted", "id": reminder_id}
