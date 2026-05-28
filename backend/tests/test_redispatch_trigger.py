import pytest
from datetime import datetime, timezone, timedelta
from app.services.re_dispatch_trigger import ReDispatchTriggerService

class MockJob:
    def __init__(self, priority, status="ASSIGNED", sla_offset_mins=60, updated_offset_secs=0):
        self.priority = priority
        self.status = status
        now = datetime.now(timezone.utc)
        self.sla_deadline = now + timedelta(minutes=sla_offset_mins)
        self.updated_at = now - timedelta(seconds=updated_offset_secs)
        
class MockTech:
    def __init__(self, status="AVAILABLE"):
        self.technician_status = status

def test_p1_trigger_on_offline():
    job = MockJob(priority="P1")
    tech = MockTech(status="OFFLINE")
    res = ReDispatchTriggerService.detect_trigger(job, tech, timer_exists=True, timer_ttl=500)
    assert res is not None
    assert res["type"] == "trigger"
    assert res["reason"] == "tech_offline"

def test_p5_manual_only():
    job = MockJob(priority="P5")
    tech = MockTech(status="OFFLINE")
    res = ReDispatchTriggerService.detect_trigger(job, tech, timer_exists=False, timer_ttl=0)
    assert res is None

def test_p1_timeout_trigger():
    job = MockJob(priority="P1", updated_offset_secs=15)
    tech = MockTech()
    res = ReDispatchTriggerService.detect_trigger(job, tech, timer_exists=False, timer_ttl=0)
    assert res is not None
    assert res["type"] == "trigger"
    assert res["reason"] == "timeout"

def test_p3_pre_alert_timing():
    job = MockJob(priority="P3")
    tech = MockTech()
    # P3 pre-alert is 60s
    res = ReDispatchTriggerService.detect_trigger(job, tech, timer_exists=True, timer_ttl=59)
    assert res is not None
    assert res["type"] == "pre_alert"
    
    # At 61s, no pre-alert
    res_none = ReDispatchTriggerService.detect_trigger(job, tech, timer_exists=True, timer_ttl=61)
    assert res_none is None

def test_sla_risk_detection():
    job = MockJob(priority="P2", sla_offset_mins=25)
    tech = MockTech()
    res = ReDispatchTriggerService.detect_trigger(job, tech, timer_exists=True, timer_ttl=300)
    assert res is not None
    assert res["type"] == "trigger"
    assert res["reason"] == "sla_risk"
    assert res["urgency"] == "high"

def test_no_sla_risk_for_p3():
    job = MockJob(priority="P3", sla_offset_mins=25)
    tech = MockTech()
    res = ReDispatchTriggerService.detect_trigger(job, tech, timer_exists=True, timer_ttl=300)
    assert res is None
