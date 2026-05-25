import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.google_maps_client import GoogleMapsClient, CircuitBreaker, RateLimiter, haversine_distance
from app.services.distance import DistanceScoringService

@pytest.fixture
def mock_redis():
    mock = MagicMock()
    mock.get.return_value = None
    mock.incr.return_value = 1
    return mock

@pytest.fixture
def gmaps_client(mock_redis):
    return GoogleMapsClient(mock_redis)

@pytest.fixture
def distance_service():
    return DistanceScoringService()

def test_haversine_distance():
    # NYC to LA (approx 3940 km)
    dist = haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
    assert 3900 < dist < 4000

@pytest.mark.asyncio
async def test_invalid_coordinates_fallback(gmaps_client):
    # Latitude out of bounds
    origin = {"lat": 100, "lng": 0}
    dest = {"lat": 0, "lng": 0}
    dist = await gmaps_client.get_distance(origin, dest)
    assert dist > 0
    # Ensure redis get wasn't even called (immediate fallback)
    gmaps_client.redis.get.assert_not_called()

@pytest.mark.asyncio
async def test_cache_hit(gmaps_client):
    gmaps_client.redis.get.return_value = "42.5"
    origin = {"lat": 10, "lng": 10}
    dest = {"lat": 20, "lng": 20}
    
    dist = await gmaps_client.get_distance(origin, dest)
    assert dist == 42.5

@pytest.mark.asyncio
async def test_circuit_breaker_open_fallback(gmaps_client):
    gmaps_client.cb.is_open = MagicMock(return_value=True)
    
    origin = {"lat": 10, "lng": 10}
    dest = {"lat": 20, "lng": 20}
    
    dist = await gmaps_client.get_distance(origin, dest)
    assert dist > 0 # Returns haversine distance
    gmaps_client.cb.is_open.assert_called_once()

@pytest.mark.asyncio
async def test_rate_limit_fallback(gmaps_client):
    gmaps_client.rate_limiter.allow_request = MagicMock(return_value=False)
    
    origin = {"lat": 10, "lng": 10}
    dest = {"lat": 20, "lng": 20}
    
    dist = await gmaps_client.get_distance(origin, dest)
    assert dist > 0 # Returns haversine distance

@pytest.mark.asyncio
@patch('aiohttp.ClientSession.get')
async def test_google_maps_api_success(mock_get, gmaps_client):
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {
        "status": "OK",
        "rows": [{"elements": [{"status": "OK", "distance": {"value": 15000}}]}]
    }
    mock_get.return_value.__aenter__.return_value = mock_resp
    gmaps_client.api_key = "test_key"
    
    origin = {"lat": 10, "lng": 10}
    dest = {"lat": 20, "lng": 20}
    
    dist = await gmaps_client.get_distance(origin, dest)
    
    assert dist == 15.0
    gmaps_client.redis.setex.assert_called_once()
    
@pytest.mark.asyncio
@patch('app.services.google_maps_client.GoogleMapsClient.get_distance')
async def test_scoring_formula(mock_get_distance, distance_service, mock_redis):
    # Test 0km = 100
    mock_get_distance.return_value = 0.0
    res = await distance_service.calculate_distance_score({"lat": 0, "lng": 0}, [{"id": 1}], mock_redis)
    assert res[0]["score"] == 100.0
    
    # Test 50km = 50
    mock_get_distance.return_value = 50.0
    res = await distance_service.calculate_distance_score({"lat": 0, "lng": 0}, [{"id": 1}], mock_redis)
    assert res[0]["score"] == 50.0
    
    # Test 100km = 0
    mock_get_distance.return_value = 100.0
    res = await distance_service.calculate_distance_score({"lat": 0, "lng": 0}, [{"id": 1}], mock_redis)
    assert res[0]["score"] == 0.0
    
    # Test 150km = 0
    mock_get_distance.return_value = 150.0
    res = await distance_service.calculate_distance_score({"lat": 0, "lng": 0}, [{"id": 1}], mock_redis)
    assert res[0]["score"] == 0.0
