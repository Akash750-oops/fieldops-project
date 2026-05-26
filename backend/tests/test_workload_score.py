import pytest
from unittest.mock import MagicMock
from app.services.workload import WorkloadScoringService
from app.models import Technician

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_redis():
    mock = MagicMock()
    mock.get.return_value = None
    return mock

@pytest.fixture
def workload_service():
    return WorkloadScoringService()

def test_workload_score_calculations(workload_service, mock_db, monkeypatch, mock_redis):
    # Mock redis
    monkeypatch.setattr("app.services.workload.get_redis_client", lambda: mock_redis)
    
    mock_tech = MagicMock(spec=Technician)
    mock_db.query().filter().first.return_value = mock_tech
    
    # Test 0 jobs = 100
    mock_tech.current_jobs = 0
    res = workload_service.calculate_workload_score(mock_db, 1)
    assert res["score"] == 100.0
    assert res["qualified"] is True
    
    # Test 1 job = 67
    mock_tech.current_jobs = 1
    res = workload_service.calculate_workload_score(mock_db, 1)
    assert res["score"] == 66.67
    
    # Test 2 jobs = 33
    mock_tech.current_jobs = 2
    res = workload_service.calculate_workload_score(mock_db, 1)
    assert res["score"] == 33.33
    
    # Test 3 jobs = 0 (Disqualified)
    mock_tech.current_jobs = 3
    res = workload_service.calculate_workload_score(mock_db, 1)
    assert res["score"] == 0.0
    assert res["qualified"] is False
    assert "Maximum capacity" in res["reason"]
    
    # Test 4 jobs = 0 (Data Inconsistency)
    mock_tech.current_jobs = 4
    res = workload_service.calculate_workload_score(mock_db, 1)
    assert res["score"] == 0.0
    assert res["qualified"] is False

def test_increment_workload_atomic(workload_service, mock_db, monkeypatch, mock_redis):
    monkeypatch.setattr("app.services.workload.get_redis_client", lambda: mock_redis)
    
    mock_tech = MagicMock(spec=Technician)
    mock_tech.current_jobs = 1
    
    # Mock query chain to return tech
    query_mock = MagicMock()
    mock_db.query.return_value = query_mock
    filter_mock = MagicMock()
    query_mock.filter.return_value = filter_mock
    with_for_update_mock = MagicMock()
    filter_mock.with_for_update.return_value = with_for_update_mock
    with_for_update_mock.first.return_value = mock_tech
    
    new_jobs = workload_service.increment_workload(mock_db, 1)
    
    assert new_jobs == 2
    assert mock_tech.current_jobs == 2
    mock_db.commit.assert_called_once()
    mock_redis.delete.assert_called_once_with("workload:tech:1")
    # Verify with_for_update was called!
    with_for_update_mock.first.assert_called_once()

def test_decrement_workload_atomic(workload_service, mock_db, monkeypatch, mock_redis):
    monkeypatch.setattr("app.services.workload.get_redis_client", lambda: mock_redis)
    
    mock_tech = MagicMock(spec=Technician)
    mock_tech.current_jobs = 0  # Test floor of 0
    
    # Mock query chain
    query_mock = MagicMock()
    mock_db.query.return_value = query_mock
    filter_mock = MagicMock()
    query_mock.filter.return_value = filter_mock
    with_for_update_mock = MagicMock()
    filter_mock.with_for_update.return_value = with_for_update_mock
    with_for_update_mock.first.return_value = mock_tech
    
    new_jobs = workload_service.decrement_workload(mock_db, 1)
    
    # Should not drop below 0
    assert new_jobs == 0
    assert mock_tech.current_jobs == 0
    mock_db.commit.assert_called_once()
    mock_redis.delete.assert_called_once_with("workload:tech:1")
