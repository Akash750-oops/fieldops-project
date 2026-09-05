import hashlib
import json
from typing import Any


MAX_RESULT_BYTES = 1024 * 1024  # 1 MB


class ToolResultCache:
    """Redis-backed cache for tool execution results."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.metrics = {}

    @staticmethod
    def generate_cache_key(
        tool_id: str,
        parameters: dict[str, Any],
    ) -> str:
        serialized_parameters = json.dumps(
            parameters,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )

        payload = tool_id + serialized_parameters

        return hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()

    def get(
        self,
        tool_id: str,
        parameters: dict[str, Any],
    ) -> Any | None:
        key = self.generate_cache_key(tool_id, parameters)

        value = self.redis.get(key)

        tool_metrics = self.metrics.setdefault(
            tool_id,
            {"hits": 0, "misses": 0},
        )

        if value is None:
            tool_metrics["misses"] += 1
            return None

        tool_metrics["hits"] += 1

        if isinstance(value, bytes):
            value = value.decode("utf-8")

        return json.loads(value)

    def get_metrics(self, tool_id: str) -> dict[str, int]:
        return self.metrics.get(
            tool_id,
            {"hits": 0, "misses": 0},
        )

    def clear(
    self,
    tool_id: str,
    parameters: dict[str, Any],
) -> bool:
        key = self.generate_cache_key(tool_id, parameters)

        return bool(self.redis.delete(key))

    def set(
        self,
        tool_id: str,
        parameters: dict[str, Any],
        result: Any,
        ttl: int = 60,
    ) -> bool:
        key = self.generate_cache_key(tool_id, parameters)

        serialized_result = json.dumps(
            result,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )

        result_size = len(serialized_result.encode("utf-8"))

        if result_size > MAX_RESULT_BYTES:
            return False

        self.redis.setex(
            key,
            ttl,
            serialized_result,
        )

        return True