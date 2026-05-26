import pytest
from app.services.composite import CompositeScoringService

@pytest.fixture
def composite_service():
    return CompositeScoringService()

def test_composite_score_math(composite_service):
    # Proximity=100, Skill=100, Workload=0
    # Expected: (100 * 0.4) + (100 * 0.4) + (0 * 0.2) = 40 + 40 + 0 = 80
    res = composite_service.composite_score(100.0, 100.0, 0.0)
    assert res["composite_score"] == 80.0
    
    assert res["breakdown"]["proximity"]["weighted"] == 40.0
    assert res["breakdown"]["skill"]["weighted"] == 40.0
    assert res["breakdown"]["workload"]["weighted"] == 0.0

def test_composite_score_normalization(composite_service):
    # Negative proximity, over-max skill, None workload
    res = composite_service.composite_score(-50.0, 150.0, None)
    # Expected bounds: prox=0, skill=100, work=0
    # Expected: 0 + 40 + 0 = 40.0
    assert res["composite_score"] == 40.0

def test_configurable_weights(composite_service):
    custom_weights = {"proximity": 0.8, "skill": 0.1, "workload": 0.1}
    res = composite_service.composite_score(100.0, 100.0, 100.0, custom_weights)
    assert res["composite_score"] == 100.0
    assert res["breakdown"]["proximity"]["weighted"] == 80.0

def test_tie_breaking(composite_service):
    techs = [
        # Tech A: Score 90, Dist 5, Jobs 1 (Wins tie over B by distance)
        {"tech_id": "A", "composite_score": 90.0, "distance_km": 5.0, "active_jobs": 1},
        # Tech B: Score 90, Dist 10, Jobs 1
        {"tech_id": "B", "composite_score": 90.0, "distance_km": 10.0, "active_jobs": 1},
        # Tech C: Score 80, Dist 5, Jobs 1 (Loses to A and B by score)
        {"tech_id": "C", "composite_score": 80.0, "distance_km": 5.0, "active_jobs": 1},
        # Tech D: Score 90, Dist 5, Jobs 0 (Wins tie over A by jobs!)
        {"tech_id": "D", "composite_score": 90.0, "distance_km": 5.0, "active_jobs": 0},
        # Tech E: Score 90, Dist 5, Jobs 0 (Same as D, but ID "E" comes after "D")
        {"tech_id": "E", "composite_score": 90.0, "distance_km": 5.0, "active_jobs": 0},
        # Tech None: Missing data entirely
        {"tech_id": "Z"}
    ]
    
    ranked = composite_service.rank_technicians(techs)
    
    # Expected Order:
    # 1. D (Score 90, Dist 5, Jobs 0, ID D)
    # 2. E (Score 90, Dist 5, Jobs 0, ID E)
    # 3. A (Score 90, Dist 5, Jobs 1)
    # 4. B (Score 90, Dist 10, Jobs 1)
    # 5. C (Score 80)
    # 6. Z (Score 0)
    
    assert ranked[0]["tech_id"] == "D"
    assert ranked[1]["tech_id"] == "E"
    assert ranked[2]["tech_id"] == "A"
    assert ranked[3]["tech_id"] == "B"
    assert ranked[4]["tech_id"] == "C"
    assert ranked[5]["tech_id"] == "Z"
