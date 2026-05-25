import aiohttp
import math
import os
import time
import json
import logging

logger = logging.getLogger("fieldops")

# Circuit breaker config
CB_FAILURE_THRESHOLD = 5  # Failures
CB_RECOVERY_TIMEOUT = 60  # Seconds

class CircuitBreaker:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_failures = "cb:failures:gmaps"
        self.key_state = "cb:state:gmaps"

    def is_open(self):
        state = self.redis.get(self.key_state)
        return state == "OPEN"

    def record_failure(self):
        failures = self.redis.incr(self.key_failures)
        if failures is None:
            return
            
        if failures == 1:
            self.redis.expire(self.key_failures, CB_RECOVERY_TIMEOUT)
        
        if failures >= CB_FAILURE_THRESHOLD:
            # Open the circuit for the recovery timeout
            self.redis.setex(self.key_state, CB_RECOVERY_TIMEOUT, "OPEN")
            self.redis.delete(self.key_failures)
            logger.warning("Google Maps Circuit Breaker OPENED")

    def record_success(self):
        if not self.is_open():
            self.redis.delete(self.key_failures)

class RateLimiter:
    def __init__(self, redis_client, rate_limit=100, window=60):
        self.redis = redis_client
        self.rate_limit = rate_limit
        self.window = window

    def allow_request(self) -> bool:
        """Token bucket inspired rate limiter using redis INCR and EXPIRE."""
        current_minute = int(time.time() // self.window)
        key = f"rate_limit:gmaps:{current_minute}"
        
        count = self.redis.incr(key)
        if count is None:
            return True
            
        if count == 1:
            self.redis.expire(key, self.window + 10)
            
        if count > self.rate_limit:
            logger.warning(f"Google Maps Rate limit exceeded: {count}/{self.rate_limit}")
            return False
        return True


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371 # Radius of earth in kilometers
    return c * r


class GoogleMapsClient:
    def __init__(self, redis_client):
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        self.base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        self.redis = redis_client
        self.cb = CircuitBreaker(redis_client)
        self.rate_limiter = RateLimiter(redis_client)

    async def get_distance(self, origin: dict, dest: dict) -> float:
        """
        Returns distance in km between origin and dest.
        Uses Redis cache, Rate Limiting, Circuit Breaker, and Haversine fallback.
        """
        origin_lat, origin_lng = origin.get("lat"), origin.get("lng")
        dest_lat, dest_lng = dest.get("lat"), dest.get("lng")

        # Basic coordinate validation
        if not (-90 <= origin_lat <= 90 and -180 <= origin_lng <= 180):
            return haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
        if not (-90 <= dest_lat <= 90 and -180 <= dest_lng <= 180):
            return haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)

        cache_key = f"proximity:{origin_lat},{origin_lng}:{dest_lat},{dest_lng}"
        
        # 1. Check Cache
        cached_result = self.redis.get(cache_key)
        if cached_result:
            return float(cached_result)

        # 2. Check Circuit Breaker
        if self.cb.is_open() or not self.api_key:
            return haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)

        # 3. Check Rate Limit
        if not self.rate_limiter.allow_request():
            return haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)

        # 4. API Call
        try:
            params = {
                "origins": f"{origin_lat},{origin_lng}",
                "destinations": f"{dest_lat},{dest_lng}",
                "mode": "driving",
                "key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=2.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Parse Google Maps response
                        if data.get("status") == "OK" and data["rows"][0]["elements"][0]["status"] == "OK":
                            # distance in meters -> km
                            distance_meters = data["rows"][0]["elements"][0]["distance"]["value"]
                            distance_km = distance_meters / 1000.0
                            
                            # Cache the successful result (300 seconds TTL)
                            self.redis.setex(cache_key, 300, str(distance_km))
                            self.cb.record_success()
                            return distance_km
                        else:
                            # API returned an error payload
                            self.cb.record_failure()
                            logger.error(f"Google Maps API error response: {data.get('status')}")
                            return haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
                    else:
                        # HTTP error
                        self.cb.record_failure()
                        logger.error(f"Google Maps API HTTP Error: {resp.status}")
                        return haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)

        except Exception as e:
            # Network error or timeout
            self.cb.record_failure()
            logger.error(f"Google Maps API request failed: {str(e)}")
            return haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
