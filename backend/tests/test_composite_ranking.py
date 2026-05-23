import pytest
from hypothesis import given, settings
from app.services.composite import CompositeScoringService

@pytest.fixture
def service():
    return CompositeScoringService()

def test_exact_tie_composite(service):
    # Setup: 3 techs with identical scores (80, 80, 80)
    # Actually wait, the requirement is 3 techs with identical scores but we need them to tie.
    # If they are totally identical in all tie-breakers, tech_id breaks the tie.
    techs = [
        {"tech_id": "T3", "composite_score": 80.0, "distance_km": 10.0, "active_jobs": 2},
        {"tech_id": "T1", "composite_score": 80.0, "distance_km": 10.0, "active_jobs": 2},
        {"tech_id": "T2", "composite_score": 80.0, "distance_km": 10.0, "active_jobs": 2},
    ]
    
    # Run ranking multiple times to ensure deterministic order
    for _ in range(1000):
        ranked = service.rank_technicians(techs.copy())
        assert [t["tech_id"] for t in ranked] == ["T1", "T2", "T3"]

def test_tie_break_by_distance(service):
    techs = [
        {"tech_id": "T1", "composite_score": 75.0, "distance_km": 20.0, "active_jobs": 1},
        {"tech_id": "T2", "composite_score": 75.0, "distance_km": 10.0, "active_jobs": 1},
    ]
    ranked = service.rank_technicians(techs)
    assert ranked[0]["tech_id"] == "T2"
    assert ranked[1]["tech_id"] == "T1"

def test_tie_break_by_workload(service):
    techs = [
        {"tech_id": "T1", "composite_score": 75.0, "distance_km": 15.0, "active_jobs": 2},
        {"tech_id": "T2", "composite_score": 75.0, "distance_km": 15.0, "active_jobs": 1},
    ]
    ranked = service.rank_technicians(techs)
    assert ranked[0]["tech_id"] == "T2"
    assert ranked[1]["tech_id"] == "T1"

def test_tie_break_by_tech_id(service):
    techs = [
        {"tech_id": "T2", "composite_score": 75.0, "distance_km": 15.0, "active_jobs": 1},
        {"tech_id": "T1", "composite_score": 75.0, "distance_km": 15.0, "active_jobs": 1},
    ]
    ranked = service.rank_technicians(techs)
    assert ranked[0]["tech_id"] == "T1"
    assert ranked[1]["tech_id"] == "T2"

def test_all_zero_scores(service):
    techs = [
        {"tech_id": "T1", "composite_score": 0.0, "distance_km": 20.0, "active_jobs": 5},
        {"tech_id": "T2", "composite_score": 0.0, "distance_km": 10.0, "active_jobs": 1},
    ]
    ranked = service.rank_technicians(techs)
    # T2 wins on distance
    assert ranked[0]["tech_id"] == "T2"
    assert ranked[1]["tech_id"] == "T1"

def test_all_perfect_scores(service):
    techs = [
        {"tech_id": "T1", "composite_score": 100.0, "distance_km": 5.0, "active_jobs": 0},
        {"tech_id": "T2", "composite_score": 100.0, "distance_km": 2.0, "active_jobs": 0},
    ]
    ranked = service.rank_technicians(techs)
    # T2 wins on distance
    assert ranked[0]["tech_id"] == "T2"

def test_single_technician(service):
    techs = [
        {"tech_id": "T1", "composite_score": 85.0, "distance_km": 10.0, "active_jobs": 2}
    ]
    ranked = service.rank_technicians(techs)
    assert len(ranked) == 1
    assert ranked[0]["tech_id"] == "T1"

def test_empty_pool(service):
    techs = []
    ranked = service.rank_technicians(techs)
    assert ranked == []

def test_weight_configuration_change(service):
    # Setup: admin changes weights to 50/30/20
    # The actual implementation of get_weights returns fixed weights right now:
    # {"proximity": 0.4, "skill": 0.4, "workload": 0.2}
    # We can mock this or just test the composite_score calculation.
    weights = {"proximity": 0.5, "skill": 0.3, "workload": 0.2}
    
    # Calculate for some inputs
    # prox: 80, skill: 90, work: 100
    res = service.composite_score(80.0, 90.0, 100.0, weights)
    # 80*0.5 + 90*0.3 + 100*0.2 = 40 + 27 + 20 = 87.0
    assert res["composite_score"] == 87.0

# Using Hypothesis for property-based testing of deterministic ordering
from hypothesis import HealthCheck
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.lists(
    st.fixed_dictionaries({
        "tech_id": st.text(min_size=1),
        "composite_score": st.floats(min_value=0, max_value=100, allow_nan=False),
        "distance_km": st.floats(min_value=0, max_value=1000, allow_nan=False),
        "active_jobs": st.integers(min_value=0, max_value=10)
    }),
    unique_by=lambda x: x["tech_id"],
    max_size=50
))
def test_deterministic_ordering_property(service, techs):
    # Sorting the same list multiple times or reversed versions should yield the same output
    ranked1 = service.rank_technicians(list(techs))
    ranked2 = service.rank_technicians(list(reversed(techs)))
    
    # Check that both rankings produce the exact same order of tech_ids
    assert [t["tech_id"] for t in ranked1] == [t["tech_id"] for t in ranked2]
