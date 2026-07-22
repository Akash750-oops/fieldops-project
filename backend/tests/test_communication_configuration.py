import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, ANY
import asyncio
import uuid
import datetime
import os
import alembic.config
import alembic.command
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import CommunicationChannelConfiguration, CommunicationConfigurationAudit, Technician
from app.services.ai.FieldOpsAI.schemas.communication_configuration import (
    CommunicationChannelState,
    CommunicationMessageCategory,
    DeliveryDecision,
    CommunicationChannelDisabledError,
    UnsupportedCommunicationChannelError,
    CommunicationConfigurationNotFoundError,
)
from app.services.ai.FieldOpsAI.services.communication_configuration_service import CommunicationConfigurationService
from app.services.ai.FieldOpsAI.repositories.communication_configuration_repository import CommunicationConfigurationRepository
from app.services.twilio_sms import send_job_assignment_sms
from app.main import app
from app.dependencies.prompt_admin_authorization import require_prompt_admin, PromptAdminPrincipal
from app.database import get_db
from twilio.base.exceptions import TwilioRestException
from app.models import Base

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        config = CommunicationChannelConfiguration(
            id=str(uuid.uuid4()),
            channel="SMS",
            state="ENABLED",
            revision=1,
            updated_by="system_migration",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        )
        session.add(config)
        session.commit()
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def no_sms_rate_limit(monkeypatch):
    monkeypatch.setattr(
        "app.services.twilio_sms.get_redis_client",
        lambda: None,
    )

# Migration Tests
def test_real_migration():
    db_file = "test_migration.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        
    db_url = f"sqlite:///{db_file}"
    alembic_cfg = alembic.config.Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    # Override DATABASE_URL so env.py uses our sqlite db
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = db_url
    
    try:
        engine_mig = create_engine(db_url)
        with engine_mig.connect() as conn:
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"))
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('5a33c0bd93b5')"))
            conn.commit()
            
        # Upgrade to new revision
        alembic.command.upgrade(alembic_cfg, "1a2b3c4d5e6f")
        
        with engine_mig.connect() as conn:
            tables = [t[0] for t in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
            assert "communication_channel_configurations" in tables
            assert "communication_configuration_audits" in tables
            
            row = conn.execute(text("SELECT * FROM communication_channel_configurations WHERE channel='SMS'")).fetchone()
            row_dict = row._mapping
            assert row_dict["state"] == "ENABLED" # state
            assert row_dict["revision"] == 1 # revision
            assert row_dict["updated_by"] == "system_migration" # updated_by
            
            # downgrade
            alembic.command.downgrade(alembic_cfg, "5a33c0bd93b5")
            tables_after = [t[0] for t in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
            assert "communication_channel_configurations" not in tables_after
            assert "communication_configuration_audits" not in tables_after
            
    finally:
        if 'engine_mig' in locals():
            engine_mig.dispose()
        if original_db_url is not None:
            os.environ["DATABASE_URL"] = original_db_url
        else:
            del os.environ["DATABASE_URL"]
            
        if os.path.exists(db_file):
            os.remove(db_file)

# Service Tests
def test_unknown_channel_rejected(db_session):
    repo = CommunicationConfigurationRepository(db_session)
    service = CommunicationConfigurationService(repo, db_session)
    with pytest.raises(UnsupportedCommunicationChannelError):
        service.get_channel_configuration("UNKNOWN")

def test_email_rejected_in_story_14_1(db_session):
    repo = CommunicationConfigurationRepository(db_session)
    service = CommunicationConfigurationService(repo, db_session)
    with pytest.raises(UnsupportedCommunicationChannelError):
        service.get_channel_configuration("email")

def test_missing_sms_row_uses_compatibility_default(db_session):
    db_session.query(CommunicationChannelConfiguration).delete()
    db_session.commit()
    
    repo = CommunicationConfigurationRepository(db_session)
    service = CommunicationConfigurationService(repo, db_session)
    decision = service.evaluate_delivery("SMS")
    assert decision.allowed is True
    assert decision.state == CommunicationChannelState.ENABLED
    assert decision.reason_code == "COMPATIBILITY_DEFAULT"

def test_database_failure_returns_blocked_CONFIGURATION_UNAVAILABLE(db_session):
    repo = CommunicationConfigurationRepository(db_session)
    repo.get_by_channel = MagicMock(side_effect=Exception("DB Failure"))
    service = CommunicationConfigurationService(repo, db_session)
    
    decision = service.evaluate_delivery("SMS")
    assert decision.allowed is False
    assert decision.reason_code == "CONFIGURATION_UNAVAILABLE"
    assert decision.state == CommunicationChannelState.DISABLED

def test_no_op_does_not_commit_or_update_timestamp(db_session):
    repo = CommunicationConfigurationRepository(db_session)
    service = CommunicationConfigurationService(repo, db_session)
    
    config = db_session.query(CommunicationChannelConfiguration).filter_by(channel="SMS").first()
    old_updated = config.updated_at
    old_rev = config.revision
    
    service.update_channel_state("SMS", CommunicationChannelState.ENABLED, "u", "t", "valid reason")
    
    db_session.refresh(config)
    assert config.revision == old_rev
    assert config.updated_at == old_updated

def test_failed_audit_insertion_rolls_back_state_and_revision(db_session):
    repo = CommunicationConfigurationRepository(db_session)
    service = CommunicationConfigurationService(repo, db_session)
    
    config = db_session.query(CommunicationChannelConfiguration).filter_by(channel="SMS").first()
    old_rev = config.revision
    
    repo.add_audit = MagicMock(side_effect=Exception("DB Error"))
    
    with pytest.raises(Exception):
        service.update_channel_state("SMS", CommunicationChannelState.DISABLED, "u", "t", "valid reason")
        
    db_session.refresh(config)
    assert config.state == "ENABLED"
    assert config.revision == old_rev

# Authorization Tests
def test_authorization_tests():
    import jwt
    import time
    
    client = TestClient(app)
    response = client.get("/admin/communication-config/channels/SMS")
    assert response.status_code == 401
            
    # We will use dependency override to test the require_platform_super_admin logic
    def mock_require_prompt_admin_super():
        return PromptAdminPrincipal(actor_id="user1", tenant_id="**platform**", role="super_admin")
        
    def mock_require_prompt_admin_tenant():
        return PromptAdminPrincipal(actor_id="user1", tenant_id="tenant1", role="admin")

    app.dependency_overrides[get_db] = lambda: TestingSessionLocal()
    
    # Platform super_admin GET allowed
    app.dependency_overrides[require_prompt_admin] = mock_require_prompt_admin_super
    response = client.get("/admin/communication-config/channels/SMS")
    assert response.status_code == 200
    
    # Platform super_admin PUT allowed
    response = client.put("/admin/communication-config/channels/SMS", 
                          json={"state": "DISABLED", "reason": "testing valid reason longer than 10"})
    assert response.status_code == 200
    
    # tenant admin denied
    app.dependency_overrides[require_prompt_admin] = mock_require_prompt_admin_tenant
    response = client.get("/admin/communication-config/channels/SMS")
    assert response.status_code == 403
    
    # Client actor/revision fields rejected
    app.dependency_overrides[require_prompt_admin] = mock_require_prompt_admin_super
    response = client.put("/admin/communication-config/channels/SMS", 
                          json={"state": "DISABLED", "reason": "testing valid reason longer than 10", "actor_id": "hacker"})
    assert response.status_code == 400
    
    app.dependency_overrides.pop(
        get_db,
        None,
    )
    app.dependency_overrides.pop(
        require_prompt_admin,
        None,
    )

# Delivery Tests
def test_delivery_enabled_standard_calls_twilio(db_session,no_sms_rate_limit,):
    async def run_test():
        tech = Technician(technician_id=1, tech_id="tech1", technician_name="T", technician_skill="S", technician_location="L", phone_number="+1234567890", sms_opt_out=0)
        db_session.add(tech)
        db_session.commit()
        
        with patch("app.services.twilio_sms.twilio_client") as mock_twilio:
            mock_twilio.messages.create.return_value = MagicMock(sid="123")
            await send_job_assignment_sms(db_session, "job1", "Title", "Loc", "P", ["tech1"])
            mock_twilio.messages.create.assert_called_once()
    asyncio.run(run_test())

def test_delivery_disabled_standard_never_calls(db_session,no_sms_rate_limit,):
    async def run_test():
        config = db_session.query(CommunicationChannelConfiguration).filter_by(channel="SMS").first()
        config.state = "DISABLED"
        db_session.commit()
        
        tech = Technician(technician_id=1, tech_id="tech1", technician_name="T", technician_skill="S", technician_location="L", phone_number="+1234567890", sms_opt_out=0)
        db_session.add(tech)
        db_session.commit()
        
        with patch("app.services.twilio_sms.twilio_client") as mock_twilio:
            # Since standard is blocked by disabled
            result = await send_job_assignment_sms(
                db_session,
                "job1",
                "Title",
                "Loc",
                "P",
                ["tech1"],
            )
            mock_twilio.messages.create.assert_not_called()
            assert result["blocked"] == 1
            assert result["blocked_reasons"] == {
                "SMS_DISABLED": 1
            }
    asyncio.run(run_test())

def test_delivery_emergency_only_emergency_calls(db_session,no_sms_rate_limit,):
    async def run_test():
        config = db_session.query(CommunicationChannelConfiguration).filter_by(channel="SMS").first()
        config.state = "EMERGENCY_ONLY"
        db_session.commit()
        
        tech = Technician(technician_id=1, tech_id="tech1", technician_name="T", technician_skill="S", technician_location="L", phone_number="+1234567890", sms_opt_out=0)
        db_session.add(tech)
        db_session.commit()
        
        with patch("app.services.twilio_sms.twilio_client") as mock_twilio:
            mock_twilio.messages.create.return_value = MagicMock(sid="123")
            await send_job_assignment_sms(db_session, "job1", "Title", "Loc", "P", ["tech1"], category=CommunicationMessageCategory.EMERGENCY)
            mock_twilio.messages.create.assert_called_once()
    asyncio.run(run_test())
        
def test_delivery_state_change_during_batch(db_session,no_sms_rate_limit,):
    async def run_test():
        tech1 = Technician(technician_id=1, tech_id="tech1", technician_name="T1", technician_skill="S", technician_location="L", phone_number="+1234567890", sms_opt_out=0)
        tech2 = Technician(technician_id=2, tech_id="tech2", technician_name="T2", technician_skill="S", technician_location="L", phone_number="+1234567891", sms_opt_out=0)
        db_session.add(tech1)
        db_session.add(tech2)
        db_session.commit()
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                config = db_session.query(CommunicationChannelConfiguration).filter_by(channel="SMS").first()
                config.state = "DISABLED"
                db_session.commit()
            return MagicMock(sid="123")
                
        with patch("app.services.twilio_sms.twilio_client") as mock_twilio:
            mock_twilio.messages.create.side_effect = side_effect
            res = await send_job_assignment_sms(db_session, "job1", "Title", "Loc", "P", ["tech1", "tech2"])
            assert mock_twilio.messages.create.call_count == 1 # Only one call should succeed
    asyncio.run(run_test())

def test_delivery_state_change_during_retry(db_session,no_sms_rate_limit,):
    async def run_test():
        tech = Technician(technician_id=1, tech_id="tech1", technician_name="T", technician_skill="S", technician_location="L", phone_number="+1234567890", sms_opt_out=0)
        db_session.add(tech)
        db_session.commit()
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                config = db_session.query(CommunicationChannelConfiguration).filter_by(channel="SMS").first()
                config.state = "DISABLED"
                db_session.commit()
                raise TwilioRestException(status=500, uri="x") # retryable
            return MagicMock(sid="123")
                
        with patch("app.services.twilio_sms.twilio_client") as mock_twilio:
            mock_twilio.messages.create.side_effect = side_effect
            await send_job_assignment_sms(db_session, "job1", "Title", "Loc", "P", ["tech1"])
            assert mock_twilio.messages.create.call_count == 1 # First attempt fails, next retry sees DISABLED and breaks
    asyncio.run(run_test())

def test_delivery_emergency_only_standard_never_calls(
    db_session,no_sms_rate_limit,
):
    async def run_test():
        config = (
            db_session.query(
                CommunicationChannelConfiguration
            )
            .filter_by(channel="SMS")
            .first()
        )
        config.state = "EMERGENCY_ONLY"
        db_session.commit()

        tech = Technician(
            technician_id=1,
            tech_id="tech1",
            technician_name="T",
            technician_skill="S",
            technician_location="L",
            phone_number="+1234567890",
            sms_opt_out=0,
        )
        db_session.add(tech)
        db_session.commit()

        with patch(
            "app.services.twilio_sms.twilio_client"
        ) as mock_twilio:
            result = await send_job_assignment_sms(
                db_session,
                "job1",
                "Title",
                "Loc",
                "P",
                ["tech1"],
            )

            mock_twilio.messages.create.assert_not_called()

            assert result["blocked"] == 1
            assert result["blocked_reasons"] == {
                "SMS_EMERGENCY_REQUIRED": 1
            }

    asyncio.run(run_test())
# Audit Tests
def test_audit_immutability(db_session,no_sms_rate_limit,):
    audit = CommunicationConfigurationAudit(
        channel="SMS",
        new_state="DISABLED",
        new_revision=2,
        actor_id="user",
        actor_tenant_id="tenant",
        reason="test"
    )
    db_session.add(audit)
    db_session.commit()
    db_session.refresh(audit)
    
    with pytest.raises(Exception):
        audit.reason = "new reason"
        db_session.commit()
    db_session.rollback()
        
    with pytest.raises(Exception):
        db_session.delete(audit)
        db_session.commit()
    db_session.rollback()

# Route duplication test
def test_route_duplication(db_session,no_sms_rate_limit,):
    # Assert exactly one registration for GET and PUT endpoints
    get_count = sum(1 for route in app.routes if getattr(route, "path", None) == "/admin/communication-config/channels/{channel}" and "GET" in route.methods)
    put_count = sum(1 for route in app.routes if getattr(route, "path", None) == "/admin/communication-config/channels/{channel}" and "PUT" in route.methods)
    assert get_count == 1
    assert put_count == 1
