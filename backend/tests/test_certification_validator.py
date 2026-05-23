import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from app.services.certification_validator import CertificationValidator
from app.models import Technician, Job, AuditEvent

@pytest.fixture
def validator():
    return CertificationValidator()

def test_missing_required_skill(validator):
    job = Job(required_skill="HVAC_CERT")
    tech = Technician(technician_skill="PLUMBING")
    
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is False
    assert res["reason"] == "missing_skills"
    assert "HVAC_CERT" in res["details"]

def test_missing_prerequisite(validator):
    job = Job(required_skill="HVAC_CERT")
    tech = Technician(technician_skill="HVAC_CERT") # missing ELEC_LV
    
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is False
    assert res["reason"] == "missing_prerequisite"
    assert res["missing_prerequisite"] == "ELEC_LV"

def test_all_certifications_present(validator):
    job = Job(required_skill="HVAC_CERT")
    tech = Technician(technician_skill="HVAC_CERT, ELEC_LV")
    
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is True

def test_expired_certification_disqualifies(validator):
    job = Job(required_skill="HVAC_CERT")
    past_date = (datetime.now() - timedelta(days=1)).isoformat()
    tech = Technician(
        technician_skill="HVAC_CERT, ELEC_LV",
        certifications_data={"HVAC_CERT": past_date}
    )
    
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is False
    assert res["reason"] == "expired_certifications"
    assert "HVAC_CERT" in res["details"]

def test_valid_expiration_date(validator):
    job = Job(required_skill="HVAC_CERT")
    future_date = (datetime.now() + timedelta(days=10)).isoformat()
    tech = Technician(
        technician_skill="HVAC_CERT, ELEC_LV",
        certifications_data={"HVAC_CERT": future_date}
    )
    
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is True

def test_prerequisite_chain(validator):
    job = Job(required_skill="A")
    tech = Technician(technician_skill="A, B") # missing C
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is False
    assert res["missing_prerequisite"] == "C"

def test_audit_log_records_disqualification(validator):
    job = Job(id=1, required_skill="A")
    tech = Technician(technician_id=1, tech_id="uuid", tenant_id="t1", technician_skill="A, B")
    
    res = validator.validate_certifications(job, tech)
    
    db_mock = MagicMock()
    validator.log_disqualification(db_mock, job.id, tech, res)
    
    db_mock.add.assert_called_once()
    audit = db_mock.add.call_args[0][0]
    assert isinstance(audit, AuditEvent)
    assert audit.event_type == "CERT_REJECTED"
    assert audit.new_status == "DISQUALIFIED"
    assert audit.old_status == "missing_prerequisite"

# Testing the Admin Override API
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routes.dispatch import router
from app.database import get_db
from app.routes.dispatch import verify_jwt_token

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def override_get_db():
    db = MagicMock()
    tech = Technician(technician_id=99, tech_id="tech-123", tenant_id="test")
    job = Job(id=1, assigned_technician_id=None)
    
    def mock_query(model):
        m = MagicMock()
        if model == Job:
            m.filter.return_value.first.return_value = job
        elif model == Technician:
            m.filter.return_value.first.return_value = tech
        return m
        
    db.query = mock_query
    yield db

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[verify_jwt_token] = lambda: "Bearer valid"

def test_admin_override():
    response = client.post(
        "/technicians/assignments/1/override",
        json={"technician_id": "tech-123", "justification": "Emergency repair"},
        headers={"X-Tenant-ID": "test", "Authorization": "Bearer token"}
    )
    print(response.text)
    assert response.status_code == 200
    assert response.json()["message"] == "Override applied successfully"
