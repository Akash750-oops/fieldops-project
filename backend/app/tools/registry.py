import importlib
import json
import pkgutil
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable

from app.redis_client import get_redis_client

from app.tools.examples import (
    fetch_customer_schema,
    generate_sms_schema,
    get_eta_schema,
)
from app.tools.schema import ToolSchema


@dataclass
class RegisteredTool:
    schema: ToolSchema
    handler: Callable[..., Any] | None = None
    category: str = "general"
    capabilities: set[str] = field(default_factory=set)
    dependencies: set[str] = field(default_factory=set)
    permissions: set[str] = field(default_factory=set)
    health: str = "healthy"
    cacheable: bool = True
    cache_ttl: int = 60


class ToolRegistry:
    def __init__(self, redis_client=None):
        self._tools: dict[str, ToolSchema] = {}
        self._registered_tools: dict[str, RegisteredTool] = {}
        self._tool_versions: dict[str, dict[str, RegisteredTool]] = {}

        self._redis = (
            redis_client
            if redis_client is not None
            else get_redis_client()
        )

    def tool(
        self,
        schema: ToolSchema,
        category: str = "general",
        capabilities: set[str] | None = None,
        dependencies: set[str] | None = None,
        permissions: set[str] | None = None,
        cacheable: bool = True,
        cache_ttl: int = 60,
    ):
        def decorator(func: Callable[..., Any]):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            self.register_tool(
                tool=schema,
                handler=wrapper,
                category=category,
                capabilities=capabilities,
                dependencies=dependencies,
                permissions=permissions,
                cacheable=cacheable,
                cache_ttl=cache_ttl,
            )

            return wrapper

        return decorator

    def register(self, tool: ToolSchema) -> None:
        self._tools[tool.contract.name] = tool

    def get(self, name: str) -> ToolSchema | None:
        return self._tools.get(name)

    def discover(self, package_name: str) -> list[str]:
        """Discover and import tool modules under a package."""
        package = importlib.import_module(package_name)

        if not hasattr(package, "__path__"):
            return [package_name]

        discovered: list[str] = []

        for module_info in pkgutil.walk_packages(
            package.__path__,
            prefix=f"{package_name}.",
        ):
            module_name = module_info.name
            importlib.import_module(module_name)
            discovered.append(module_name)

        return discovered

    def register_tool(
        self,
        tool: ToolSchema,
        handler: Callable[..., Any] | None = None,
        category: str = "general",
        capabilities: set[str] | None = None,
        dependencies: set[str] | None = None,
        permissions: set[str] | None = None,
        cacheable: bool = True,
        cache_ttl: int = 60,
    ) -> str:

        if cache_ttl <= 0:
            raise ValueError("cache_ttl must be greater than 0")

        tool_id = tool.contract.name

        self._tools[tool_id] = tool

        registered_tool = RegisteredTool(
            schema=tool,
            handler=handler,
            category=category,
            capabilities=capabilities or set(),
            dependencies=dependencies or set(),
            permissions=permissions or set(),
            cacheable=cacheable,
            cache_ttl=cache_ttl,
        )

        self._registered_tools[tool_id] = registered_tool

        version = tool.contract.version

        self._tool_versions.setdefault(
            tool_id,
            {},
        )[version] = registered_tool

        return tool_id

    def get_tool(self, tool_id: str) -> RegisteredTool | None:
        return self._registered_tools.get(tool_id)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def cache_catalog(self, ttl_seconds: int = 300) -> bool:
        """Cache the current tool catalog in Redis."""
        if self._redis is None:
            return False

        catalog = []

        for tool in self._registered_tools.values():
            catalog.append(
                {
                    "id": tool.schema.contract.name,
                    "name": tool.schema.contract.name,
                    "description": tool.schema.contract.description,
                    "version": tool.schema.contract.version,
                    "category": tool.category,
                    "capabilities": sorted(tool.capabilities),
                    "dependencies": sorted(tool.dependencies),
                    "permissions": sorted(tool.permissions),
                    "health": tool.health,
                }
            )

        try:
            return self._redis.setex(
                "fieldops:tools:catalog",
                ttl_seconds,
                json.dumps(catalog),
            )
        except Exception:
            return False

    def search_tools(
        self,
        name: str | None = None,
        category: str | None = None,
        capability: str | None = None,
    ) -> list[RegisteredTool]:
        results = list(self._registered_tools.values())

        if name is not None:
            results = [
                tool
                for tool in results
                if tool.schema.contract.name == name
            ]

        if category is not None:
            results = [
                tool
                for tool in results
                if tool.category == category
            ]

        if capability is not None:
            results = [
                tool
                for tool in results
                if capability in tool.capabilities
            ]

        return results

    def get_health(self, tool_id: str) -> str | None:
        tool = self._registered_tools.get(tool_id)

        if tool is None:
            return None

        return tool.health

    def set_health(self, tool_id: str, health: str) -> bool:
        tool = self._registered_tools.get(tool_id)

        if tool is None:
            return False

        tool.health = health
        return True

    def get_dependencies(self, tool_id: str) -> set[str] | None:
        tool = self._registered_tools.get(tool_id)

        if tool is None:
            return None

        return set(tool.dependencies)

    def dependency_graph(self) -> dict[str, set[str]]:
        return {
            tool_id: set(tool.dependencies)
            for tool_id, tool in self._registered_tools.items()
        }

    def validate_dependencies(self, tool_id: str) -> list[str]:
        """Return dependencies that are not registered."""
        tool = self._registered_tools.get(tool_id)

        if tool is None:
            return []

        return [
            dependency
            for dependency in tool.dependencies
            if dependency not in self._registered_tools
        ]

    def check_permission(
        self,
        tool_id: str,
        permission: str,
    ) -> bool:
        tool = self._registered_tools.get(tool_id)

        if tool is None:
            return False

        return permission in tool.permissions

    def get_version(self, tool_id: str) -> str | None:
        tool = self._registered_tools.get(tool_id)

        if tool is None:
            return None

        return tool.schema.contract.version

    def get_tool_version(
        self,
        tool_id: str,
        version: str,
    ) -> RegisteredTool | None:
        return self._tool_versions.get(tool_id, {}).get(version)


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register_tool(generate_sms_schema())
    registry.register_tool(fetch_customer_schema())
    registry.register_tool(get_eta_schema())

    return registry