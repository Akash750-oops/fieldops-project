import redis
from redis.exceptions import ConnectionError, TimeoutError
import os
import time
from typing import Optional

class RedisCacheManager:
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        
        self.pool = redis.ConnectionPool(
            host=redis_host, 
            port=redis_port, 
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0
        )
        self.client = redis.Redis(connection_pool=self.pool)

    def _execute_with_retry(self, operation, *args, **kwargs):
        retries = 2
        for i in range(retries):
            try:
                return operation(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                if i == retries - 1:
                    print(f"Redis connection failed after {retries} retries: {e}")
                    return None
                time.sleep(0.1)
        return None

    def get(self, key: str) -> Optional[str]:
        return self._execute_with_retry(self.client.get, key)

    def setex(self, key: str, time_seconds: int, value: str) -> bool:
        result = self._execute_with_retry(self.client.setex, key, time_seconds, value)
        return result is not None

    def delete(self, key: str) -> bool:
        result = self._execute_with_retry(self.client.delete, key)
        return result is not None

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        return self._execute_with_retry(self.client.incrby, key, amount)

    def expire(self, key: str, time_seconds: int) -> bool:
        result = self._execute_with_retry(self.client.expire, key, time_seconds)
        return result is not None

redis_manager = None

def get_redis_client():
    global redis_manager
    if redis_manager is None:
        redis_manager = RedisCacheManager()
    return redis_manager
