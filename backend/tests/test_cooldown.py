import pytest
from datetime import datetime, timezone, timedelta
import json
from app.services.cooldown_service import CooldownService

class MockRedisCooldown:
    def __init__(self):
        self.data = {}
        
    def setex(self, key, time, value):
        self.data[key] = value
        return True
        
    def delete(self, key):
        if key in self.data:
            del self.data[key]
            return 1
        return 0
        
    def get(self, key):
        return self.data.get(key)
        
    def exists(self, key):
        return key in self.data

def test_cooldown_set_on_rejection():
    redis_client = MockRedisCooldown()
    
    res = CooldownService.set_cooldown(redis_client, "job-1", "tech-1", 120)
    assert res is True
    assert redis_client.exists("job:cooldown:job-1:tech-1")

def test_technician_excluded_during_cooldown_in_planning():
    redis_client = MockRedisCooldown()
    CooldownService.set_cooldown(redis_client, "job-1", "tech-1", 120)
    
    # Check cooldown
    check = CooldownService.check_cooldown(redis_client, "job-1", "tech-1")
    assert check is not None
    assert check["remaining_seconds"] <= 120
    assert "cooldown_expires_at" in check

def test_cooldown_auto_expires():
    redis_client = MockRedisCooldown()
    
    # Set an expired cooldown
    expired_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    redis_client.data["job:cooldown:job-1:tech-1"] = expired_time
    
    check = CooldownService.check_cooldown(redis_client, "job-1", "tech-1")
    assert check is None

def test_manual_override_clears_cooldown():
    redis_client = MockRedisCooldown()
    CooldownService.set_cooldown(redis_client, "job-1", "tech-1", 120)
    
    res = CooldownService.clear_cooldown(redis_client, "job-1", "tech-1")
    assert res is True
    
    check = CooldownService.check_cooldown(redis_client, "job-1", "tech-1")
    assert check is None
