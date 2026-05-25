import pytest
from datetime import datetime, timedelta
from app.services.certification_validator import CertificationValidator
from app.models import Technician, Job

@pytest.fixture
def validator():
    return CertificationValidator()

def test_missing_direct_skill(validator):
    job = Job(required_skill="HVAC_CERT")
    tech = Technician(technician_skill="PLUMBING")
    
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is False
    assert res["reason"] == "missing_skills"
    assert "HVAC_CERT" in res["details"]

def test_missing_prerequisite(validator):
    job = Job(required_skill="HVAC_CERT") # Requires ELEC_LV
    tech = Technician(technician_skill="HVAC_CERT")
    
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is False
    assert res["reason"] == "missing_prerequisite"
    assert res["missing_prerequisite"] == "ELEC_LV"

def test_expired_certification(validator):
    job = Job(required_skill="PLUMBING")
    
    # Expired 10 days ago
    past_date = (datetime.now() - timedelta(days=10)).isoformat()
    tech = Technician(
        technician_skill="PLUMBING",
        certifications_data={"PLUMBING": past_date}
    )
    
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is False
    assert res["reason"] == "expired_certifications"
    assert "PLUMBING" in res["details"]

def test_expiring_soon_warning(validator):
    job = Job(required_skill="PLUMBING")
    
    # Expiring in 10 days (under 30 day threshold)
    future_date = (datetime.now() + timedelta(days=10)).isoformat()
    tech = Technician(
        technician_skill="PLUMBING",
        certifications_data={"PLUMBING": future_date}
    )
    
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is True
    assert "warnings" in res
    assert any("PLUMBING" in w for w in res["warnings"])

def test_fully_qualified(validator):
    job = Job(required_skill="HVAC_CERT")
    
    # Valid for 100 days
    future_date = (datetime.now() + timedelta(days=100)).isoformat()
    tech = Technician(
        technician_skill="HVAC_CERT, ELEC_LV",
        certifications_data={"HVAC_CERT": future_date, "ELEC_LV": future_date}
    )
    
    res = validator.validate_certifications(job, tech)
    assert res["qualified"] is True
    assert not res.get("warnings")
