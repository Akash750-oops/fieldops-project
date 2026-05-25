import pytest
from unittest.mock import MagicMock
from app.services.skill import SkillScoringService

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_redis():
    mock = MagicMock()
    # Simulate cache miss so it uses DEFAULT_TAXONOMY
    mock.get.return_value = None
    return mock

@pytest.fixture
def skill_service(monkeypatch, mock_redis):
    monkeypatch.setattr("app.services.skill.get_redis_client", lambda: mock_redis)
    return SkillScoringService()

def test_empty_requirements(skill_service, mock_db):
    res = skill_service.calculate_skill_score("", "HVAC_CERT", mock_db)
    assert res["score"] == 100.0
    assert res["qualified"] is True
    assert len(res["missing_skills"]) == 0

def test_empty_technician_skills(skill_service, mock_db):
    res = skill_service.calculate_skill_score("HVAC_CERT", "", mock_db)
    assert res["score"] == 0.0
    # Because they are missing HVAC_CERT which requires ELECTRICAL_LV (which they also don't have)
    # Wait, the logic checks for missing prerequisite. 
    # required = HVAC_CERT
    # prereqs = ELECTRICAL_LV
    # prereq not in held -> Disqualified missing prerequisite!
    assert res["qualified"] is False

def test_exact_match(skill_service, mock_db):
    res = skill_service.calculate_skill_score("HVAC_CERT, ELECTRICAL_LV", "hvac_cert, electrical_lv", mock_db)
    assert res["score"] == 100.0
    assert res["qualified"] is True

def test_partial_match(skill_service, mock_db):
    # Job requires AC MECHANIC and PLUMBING. 
    # Tech has AC MECHANIC, so 1/2 match (50%)
    res = skill_service.calculate_skill_score("AC MECHANIC, PLUMBING", "AC MECHANIC", mock_db)
    assert res["score"] == 50.0
    assert res["qualified"] is True
    assert "PLUMBING" in res["missing_skills"]

def test_missing_prerequisite_disqualification(skill_service, mock_db):
    # Job requires HVAC_CERT. HVAC_CERT requires ELECTRICAL_LV.
    # Tech has HVAC_CERT but DOES NOT have ELECTRICAL_LV.
    res = skill_service.calculate_skill_score("HVAC_CERT", "HVAC_CERT", mock_db)
    assert res["score"] == 0.0
    assert res["qualified"] is False
    assert "Missing prerequisite: ELECTRICAL_LV" in res["reason"]

def test_prerequisite_satisfied(skill_service, mock_db):
    # Job requires HVAC_CERT. Tech has HVAC_CERT AND ELECTRICAL_LV.
    res = skill_service.calculate_skill_score("HVAC_CERT", "HVAC_CERT, ELECTRICAL_LV", mock_db)
    assert res["score"] == 100.0
    assert res["qualified"] is True

def test_equivalence_mapping(skill_service, mock_db):
    # Job requires AC MECHANIC.
    # AC MECHANIC has an equivalent "HVAC_CERT".
    # Tech has HVAC_CERT (and ELECTRICAL_LV to satisfy its prereq just in case).
    res = skill_service.calculate_skill_score("AC MECHANIC", "HVAC_CERT, ELECTRICAL_LV", mock_db)
    
    # Tech should get credit for AC MECHANIC because of equivalence!
    assert res["score"] == 100.0
    assert res["qualified"] is True
    assert "AC MECHANIC" in res["matched_skills"]
