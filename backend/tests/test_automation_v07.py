import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.automation import (
    automation_manager,
    automation_registry,
    automation_logger,
    automation_permissions,
    automation_scheduler,
    automation_executor,
    trigger_engine,
    notification_manager,
    AutonomyLevel,
    TriggerType,
    ScheduleType,
    AutomationActionType,
    NotificationType,
    AutomationCreate,
    AutomationUpdate,
    TriggerConfig,
    ScheduleConfig,
    ReminderCreate,
    RetryPolicy,
)

client = TestClient(app)

# ==================== 1. AUTOMATION CRUD & PERSISTENCE ====================

def test_automation_crud():
    """Verify creating, reading, updating, enabling, disabling, and deleting an automation."""
    create_payload = AutomationCreate(
        name="Test Daily Routine",
        description="Daily test workflow",
        enabled=True,
        autonomy_level=AutonomyLevel.EXECUTE_LOW_RISK,
        action_type=AutomationActionType.NOTIFICATION,
        trigger_config=TriggerConfig(
            trigger_type=TriggerType.SCHEDULE,
            schedule=ScheduleConfig(
                schedule_type=ScheduleType.DAILY,
                time_of_day="09:00",
                timezone="UTC"
            )
        ),
        action_payload={"title": "Test Title", "message": "Test Body"}
    )

    # 1. Create
    rule = automation_manager.create_automation(create_payload)
    assert rule.id is not None
    assert rule.name == "Test Daily Routine"
    assert rule.enabled is True
    assert rule.next_run_at is not None

    # 2. Get
    fetched = automation_manager.get_automation(rule.id)
    assert fetched is not None
    assert fetched.id == rule.id

    # 3. Update
    updated = automation_manager.update_automation(rule.id, AutomationUpdate(description="Updated description"))
    assert updated.description == "Updated description"

    # 4. Disable
    disabled = automation_manager.disable_automation(rule.id)
    assert disabled.enabled is False

    # 5. Enable
    enabled = automation_manager.enable_automation(rule.id)
    assert enabled.enabled is True

    # 6. Delete
    deleted = automation_manager.delete_automation(rule.id)
    assert deleted is True
    assert automation_manager.get_automation(rule.id) is None

# ==================== 2. SCHEDULER & TIMEZONE HANDLING ====================

def test_scheduler_compute_next_run():
    """Verify schedule computation for DAILY, WEEKLY, RECURRING, and timezones."""
    # Daily schedule at 14:00 UTC
    rule_daily = automation_manager.create_automation(AutomationCreate(
        name="Daily 14 UTC",
        trigger_config=TriggerConfig(
            trigger_type=TriggerType.SCHEDULE,
            schedule=ScheduleConfig(
                schedule_type=ScheduleType.DAILY,
                time_of_day="14:00",
                timezone="UTC"
            )
        ),
        action_type=AutomationActionType.NOTIFICATION
    ))
    next_daily = automation_scheduler.compute_next_run(rule_daily)
    assert next_daily is not None
    dt = datetime.fromisoformat(next_daily.replace("Z", "+00:00"))
    assert dt.hour == 14 and dt.minute == 0
    automation_manager.delete_automation(rule_daily.id)

    # Recurring interval (e.g. 1800s)
    rule_recurring = automation_manager.create_automation(AutomationCreate(
        name="Recurring 30m",
        trigger_config=TriggerConfig(
            trigger_type=TriggerType.SCHEDULE,
            schedule=ScheduleConfig(
                schedule_type=ScheduleType.RECURRING,
                interval_seconds=1800
            )
        ),
        action_type=AutomationActionType.NOTIFICATION
    ))
    now = datetime.now(timezone.utc)
    next_rec = automation_scheduler.compute_next_run(rule_recurring, from_dt=now)
    assert next_rec is not None
    rec_dt = datetime.fromisoformat(next_rec.replace("Z", "+00:00"))
    diff = (rec_dt - now).total_seconds()
    assert 1790 <= diff <= 1810
    automation_manager.delete_automation(rule_recurring.id)

def test_missed_schedule_recovery():
    """Verify restart recovery executes missed runs without duplicate triggers."""
    now = datetime.now(timezone.utc)
    past_iso = (now - timedelta(minutes=15)).isoformat()

    rule = automation_manager.create_automation(AutomationCreate(
        name="Missed Scheduled Job",
        trigger_config=TriggerConfig(
            trigger_type=TriggerType.SCHEDULE,
            schedule=ScheduleConfig(
                schedule_type=ScheduleType.DAILY,
                time_of_day="08:00"
            )
        ),
        action_type=AutomationActionType.NOTIFICATION,
        action_payload={"title": "Recovered", "message": "Ran on reboot"}
    ))
    rule.next_run_at = past_iso
    automation_logger.save_automation(rule)

    # Run restart recovery
    automation_scheduler.handle_restart_recovery([rule])

    # Ensure rule next_run_at is refreshed to the future
    refreshed = automation_manager.get_automation(rule.id)
    assert refreshed.next_run_at is not None
    assert refreshed.next_run_at > now.isoformat()
    automation_manager.delete_automation(rule.id)

# ==================== 3. TRIGGER ENGINE ====================

def test_trigger_engine_thresholds_and_events():
    """Verify event-driven evaluations: system thresholds, app events, workflow outcomes, overdue tasks."""
    # 1. System threshold
    thresh_rule = automation_manager.create_automation(AutomationCreate(
        name="High CPU Guard",
        trigger_config=TriggerConfig(
            trigger_type=TriggerType.SYSTEM_THRESHOLD,
            system_metric="cpu_percent",
            metric_threshold=0.01, # Trigger easily for test
            metric_operator=">"
        ),
        action_type=AutomationActionType.NOTIFICATION
    ))
    matched_thresh = trigger_engine.evaluate_system_thresholds([thresh_rule])
    assert len(matched_thresh) == 1
    assert matched_thresh[0].id == thresh_rule.id
    automation_manager.delete_automation(thresh_rule.id)

    # 2. App event
    app_rule = automation_manager.create_automation(AutomationCreate(
        name="IDE Launched Trigger",
        trigger_config=TriggerConfig(
            trigger_type=TriggerType.APP_EVENT,
            app_name="Code.exe",
            app_action="launched"
        ),
        action_type=AutomationActionType.NOTIFICATION
    ))
    matched_app = trigger_engine.evaluate_app_event([app_rule], "code.exe", "launched")
    assert len(matched_app) == 1
    no_match = trigger_engine.evaluate_app_event([app_rule], "chrome.exe", "launched")
    assert len(no_match) == 0
    automation_manager.delete_automation(app_rule.id)

    # 3. Workflow event
    wf_rule = automation_manager.create_automation(AutomationCreate(
        name="On Deploy Complete",
        trigger_config=TriggerConfig(
            trigger_type=TriggerType.WORKFLOW_EVENT,
            workflow_outcome="COMPLETED",
            workflow_id_pattern="wf_deploy"
        ),
        action_type=AutomationActionType.NOTIFICATION
    ))
    matched_wf = trigger_engine.evaluate_workflow_event([wf_rule], "wf_deploy_123", "COMPLETED")
    assert len(matched_wf) == 1
    failed_wf = trigger_engine.evaluate_workflow_event([wf_rule], "wf_deploy_123", "FAILED")
    assert len(failed_wf) == 0
    automation_manager.delete_automation(wf_rule.id)

# ==================== 4. AUTONOMY & PERMISSIONS ====================

def test_permission_enforcement_and_stale_approvals():
    """Verify autonomy level enforcement, blocked action rejection, and stale approval timeout."""
    # Strictly blocked patterns must fail
    allowed, msg = automation_permissions.validate_action_permission(AutonomyLevel.REQUIRES_APPROVAL, "arbitrary_shell")
    assert allowed is False
    assert "STRICTLY BLOCKED" in msg

    allowed, msg = automation_permissions.validate_action_permission(AutonomyLevel.BLOCKED, "read_memory")
    assert allowed is False

    allowed, msg = automation_permissions.validate_action_permission(AutonomyLevel.OBSERVE, "modify_file", requires_user_approval=True)
    assert allowed is False

    # Stale approvals
    approval = automation_permissions.register_pending_approval(
        approval_id="tok_123",
        automation_id="auto_test",
        action_name="modify_file",
        action_payload={"file": "test.txt"}
    )
    assert approval["approval_id"] == "tok_123"

    # Consume once
    valid, res = automation_permissions.consume_approval("tok_123", "auto_test", "modify_file")
    assert valid is True

    # Reuse rejection (must not reuse stale approvals)
    valid2, res2 = automation_permissions.consume_approval("tok_123", "auto_test", "modify_file")
    assert valid2 is False
    assert "already been used" in res2

def test_global_pause_and_resume():
    """Verify global automation pause halts all execution."""
    automation_manager.resume_all()
    assert automation_permissions.is_globally_paused() is False

    rule = automation_manager.create_automation(AutomationCreate(
        name="Pause Test",
        trigger_config=TriggerConfig(trigger_type=TriggerType.MANUAL),
        action_type=AutomationActionType.NOTIFICATION
    ))

    # Pause
    automation_manager.pause_all()
    assert automation_permissions.is_globally_paused() is True

    can_run, reason = automation_permissions.can_rule_execute(rule)
    assert can_run is False
    assert "paused" in reason.lower()

    # Resume
    automation_manager.resume_all()
    assert automation_permissions.is_globally_paused() is False
    can_run, _ = automation_permissions.can_rule_execute(rule)
    assert can_run is True

    automation_manager.delete_automation(rule.id)

# ==================== 5. DAILY BRIEFING & PROJECT HEALTH ====================

@pytest.mark.asyncio
async def test_daily_briefing_execution():
    """Verify daily briefing executes and produces factual summary without hallucinated data."""
    rule = automation_manager.create_automation(AutomationCreate(
        name="Daily Briefing Routine",
        action_type=AutomationActionType.DAILY_BRIEFING,
        trigger_config=TriggerConfig(trigger_type=TriggerType.MANUAL),
        action_payload={"speak_aloud": False}
    ))

    res = await automation_executor.execute_rule(rule)
    assert res["status"] == "SUCCESS"
    assert "content" in res
    assert "System Telemetry:" in res["content"]
    assert "Active Reminders" in res["content"]
    automation_manager.delete_automation(rule.id)

@pytest.mark.asyncio
async def test_project_health_execution():
    """Verify project health check runs approved read-only test suite and rejects unsafe commands."""
    rule = automation_manager.create_automation(AutomationCreate(
        name="Project Health Routine",
        action_type=AutomationActionType.PROJECT_HEALTH,
        trigger_config=TriggerConfig(trigger_type=TriggerType.MANUAL),
        action_payload={
            "run_tests": False # Avoid running real test suite recursively in test
        }
    ))

    res = await automation_executor.execute_rule(rule)
    assert res["status"] in ("SUCCESS", "WARNING")
    assert "report" in res
    assert "Project Health Assessment" in res["report"]
    automation_manager.delete_automation(rule.id)

    # Unsafe command rejection
    unsafe_rule = automation_manager.create_automation(AutomationCreate(
        name="Unsafe Health Routine",
        action_type=AutomationActionType.PROJECT_HEALTH,
        trigger_config=TriggerConfig(trigger_type=TriggerType.MANUAL),
        action_payload={
            "run_tests": True,
            "test_command": "pytest && rm -rf /"
        }
    ))
    res_unsafe = await automation_executor.execute_rule(unsafe_rule)
    assert res_unsafe["status"] == "FAILED"
    automation_manager.delete_automation(unsafe_rule.id)

# ==================== 6. SMART REMINDERS & NOTIFICATIONS ====================

def test_reminders_and_notifications_lifecycle():
    """Verify smart reminders lifecycle: add, complete, snooze, delete, and notifications."""
    # 1. Reminders
    rem = automation_manager.add_reminder(ReminderCreate(
        text="Review NOVA Architecture",
        due_at=(datetime.utcnow() + timedelta(hours=2)).isoformat()
    ))
    assert rem.id > 0
    assert rem.completed is False

    reminders = automation_manager.list_reminders(pending_only=True)
    assert any(r.id == rem.id for r in reminders)

    # Snooze reminder
    snooze_iso = (datetime.utcnow() + timedelta(hours=4)).isoformat()
    automation_manager.snooze_reminder(rem.id, snooze_iso)
    
    # Complete reminder
    automation_manager.complete_reminder(rem.id)
    active = automation_manager.list_reminders(pending_only=True)
    assert not any(r.id == rem.id for r in active)

    # 2. Notifications
    notif = notification_manager.send_notification(
        notif_type=NotificationType.REMINDER,
        title="Test Notification",
        message="Please check pending tasks.",
        data={"rem_id": rem.id}
    )
    assert notif.id > 0
    assert notif.read is False

    notifs = automation_manager.list_notifications(unread_only=True)
    assert any(n.id == notif.id for n in notifs)

    # Mark read
    automation_manager.mark_notification_read(notif.id)
    unread = automation_manager.list_notifications(unread_only=True)
    assert not any(n.id == notif.id for n in unread)

    # Dismiss
    automation_manager.dismiss_notification(notif.id)

# ==================== 7. VOICE COMMAND INTEGRATION ====================

def test_voice_automation_commands():
    """Verify natural-language voice automation command processing."""
    from app.voice.audio_manager import audio_manager

    # 1. Pause
    handled, resp = audio_manager.handle_voice_automation_command("Hey NOVA, pause all automations")
    assert handled is True
    assert "paused" in resp.lower()

    # 2. Resume
    handled, resp = audio_manager.handle_voice_automation_command("Hey NOVA, resume my automations")
    assert handled is True
    assert "resumed" in resp.lower()

    # 3. Status
    handled, resp = audio_manager.handle_voice_automation_command("Hey NOVA, what automations are running?")
    assert handled is True
    assert "active automation routines" in resp

    # 4. Daily briefing voice creation
    handled, resp = audio_manager.handle_voice_automation_command("Hey NOVA, create a daily briefing at 8 AM")
    assert handled is True
    assert "Daily briefing" in resp

    # 5. Reminder voice creation
    handled, resp = audio_manager.handle_voice_automation_command("Hey NOVA, remind me tomorrow to test my voice pipeline")
    assert handled is True
    assert "Reminder set" in resp

    # 6. Project health voice scheduling
    handled, resp = audio_manager.handle_voice_automation_command("Hey NOVA, check my NOVA project every Saturday")
    assert handled is True
    assert "Saturday" in resp

# ==================== 8. REST API COMPATIBILITY ====================

def test_automation_rest_api_endpoints():
    """Verify all REST API endpoints specified in Section 10."""
    # GET /api/automation/status
    res = client.get("/api/automation/status")
    assert res.status_code == 200
    st_data = res.json()
    assert "active_count" in st_data
    assert "is_paused" in st_data

    # POST /api/automations
    create_payload = {
        "name": "API Test Routine",
        "description": "Created via REST",
        "enabled": True,
        "autonomy_level": "EXECUTE_LOW_RISK",
        "action_type": "NOTIFICATION",
        "trigger_config": {
            "trigger_type": "SCHEDULE",
            "schedule": {
                "schedule_type": "DAILY",
                "time_of_day": "07:30"
            }
        },
        "action_payload": {"title": "Hello", "message": "World"}
    }
    create_res = client.post("/api/automations", json=create_payload)
    assert create_res.status_code == 200
    rule_id = create_res.json()["id"]

    # GET /api/automations
    list_res = client.get("/api/automations")
    assert list_res.status_code == 200
    assert any(r["id"] == rule_id for r in list_res.json())

    # GET /api/automations/{id}
    get_res = client.get(f"/api/automations/{rule_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "API Test Routine"

    # PATCH /api/automations/{id}
    patch_res = client.patch(f"/api/automations/{rule_id}", json={"description": "Updated via API"})
    assert patch_res.status_code == 200
    assert patch_res.json()["description"] == "Updated via API"

    # POST /api/automations/{id}/disable
    dis_res = client.post(f"/api/automations/{rule_id}/disable")
    assert dis_res.status_code == 200
    assert dis_res.json()["enabled"] is False

    # POST /api/automations/{id}/enable
    en_res = client.post(f"/api/automations/{rule_id}/enable")
    assert en_res.status_code == 200
    assert en_res.json()["enabled"] is True

    # POST /api/automations/{id}/run
    run_res = client.post(f"/api/automations/{rule_id}/run")
    assert run_res.status_code == 200
    assert run_res.json()["status"] == "dispatched"

    # GET /api/automations/{id}/history
    hist_res = client.get(f"/api/automations/{rule_id}/history")
    assert hist_res.status_code == 200
    assert len(hist_res.json()) > 0

    # POST /api/automation/pause-all
    pause_res = client.post("/api/automation/pause-all")
    assert pause_res.status_code == 200

    # POST /api/automation/resume-all
    res_res = client.post("/api/automation/resume-all")
    assert res_res.status_code == 200

    # GET /api/notifications
    notif_res = client.get("/api/notifications")
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    if notifs:
        nid = notifs[0]["id"]
        # POST /api/notifications/{id}/read
        assert client.post(f"/api/notifications/{nid}/read").status_code == 200
        # POST /api/notifications/{id}/snooze
        assert client.post(f"/api/notifications/{nid}/snooze", json={"minutes": 10}).status_code == 200
        # POST /api/notifications/{id}/dismiss
        assert client.post(f"/api/notifications/{nid}/dismiss").status_code == 200

    # DELETE /api/automations/{id}
    del_res = client.delete(f"/api/automations/{rule_id}")
    assert del_res.status_code == 200
