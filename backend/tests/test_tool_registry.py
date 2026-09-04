from app.tools.examples import generate_sms_schema
from app.tools.registry import ToolRegistry
from app.tools.schema import ToolSchema
from app.tools.examples import (
    fetch_customer_schema,
    get_eta_schema,
)

def test_tool_decorator_registers_function():
    registry = ToolRegistry()

    @registry.tool(
        schema=generate_sms_schema(),
        category="communication",
        capabilities={"sms"},
    )
    def generate_sms(message: str, priority: str = "normal"):
        return message

    registered = registry.get_tool("generate_sms")

    assert registered is not None
    assert registered.schema.contract.name == "generate_sms"
    assert registered.handler is not None
    assert registered.category == "communication"
    assert "sms" in registered.capabilities

    assert generate_sms("Hello") == "Hello"

def test_registry_search_by_category():
    registry = ToolRegistry()

    registry.register_tool(
        generate_sms_schema(),
        category="communication",
        capabilities={"sms"},
    )

    results = registry.search_tools(category="communication")

    assert len(results) == 1
    assert results[0].schema.contract.name == "generate_sms"


def test_registry_search_by_capability():
    registry = ToolRegistry()

    registry.register_tool(
        generate_sms_schema(),
        category="communication",
        capabilities={"sms"},
    )

    results = registry.search_tools(capability="sms")

    assert len(results) == 1
    assert results[0].schema.contract.name == "generate_sms"


def test_registry_search_by_name():
    registry = ToolRegistry()

    registry.register_tool(
        generate_sms_schema(),
        category="communication",
        capabilities={"sms"},
    )

    results = registry.search_tools(name="generate_sms")

    assert len(results) == 1
    assert results[0].schema.contract.name == "generate_sms"


def test_registry_get_health():
    registry = ToolRegistry()

    registry.register_tool(
        generate_sms_schema(),
        category="communication",
        capabilities={"sms"},
    )

    assert registry.get_health("generate_sms") == "healthy"

def test_registry_set_health():
    registry = ToolRegistry()

    registry.register_tool(
        generate_sms_schema(),
        category="communication",
        capabilities={"sms"},
    )

    result = registry.set_health("generate_sms", "unhealthy")

    assert result is True
    assert registry.get_health("generate_sms") == "unhealthy"


def test_registry_health_unknown_tool():
    registry = ToolRegistry()

    assert registry.get_health("unknown_tool") is None
    assert registry.set_health("unknown_tool", "unhealthy") is False




def test_registry_get_dependencies():
    registry = ToolRegistry()

    registry.register_tool(
        generate_sms_schema(),
        category="communication",
        capabilities={"sms"},
        dependencies={"redis", "groq"},
    )

    dependencies = registry.get_dependencies("generate_sms")

    assert dependencies == {"redis", "groq"}


def test_registry_dependency_graph():
    registry = ToolRegistry()

    registry.register_tool(
        generate_sms_schema(),
        category="communication",
        capabilities={"sms"},
        dependencies={"redis"},
    )

    from app.tools.examples import fetch_customer_schema

    registry.register_tool(
        fetch_customer_schema(),
        category="customer",
        capabilities={"customer"},
        dependencies={"postgres"},
    )

    graph = registry.dependency_graph()

    assert graph["generate_sms"] == {"redis"}
    assert graph["fetch_customer"] == {"postgres"}


def test_registry_check_permission():
    registry = ToolRegistry()

    registry.register_tool(
        generate_sms_schema(),
        category="communication",
        capabilities={"sms"},
        permissions={"tools.sms.generate"},
    )

    assert registry.check_permission(
        "generate_sms",
        "tools.sms.generate",
    ) is True

    assert registry.check_permission(
        "generate_sms",
        "tools.sms.delete",
    ) is False

def test_registry_get_version():
    registry = ToolRegistry()

    registry.register_tool(generate_sms_schema())

    assert registry.get_version("generate_sms") == "v1"

def test_registry_get_tool_version():
    registry = ToolRegistry()

    registry.register_tool(generate_sms_schema())

    tool = registry.get_tool_version("generate_sms", "v1")

    assert tool is not None
    assert tool.schema.contract.version == "v1"

def test_registry_returns_none_for_wrong_version():
    registry = ToolRegistry()

    registry.register_tool(generate_sms_schema())

    assert registry.get_tool_version("generate_sms", "v2") is None

def test_discover_tools_package():
    registry = ToolRegistry()

    discovered = registry.discover("app.tools")

    assert "app.tools.examples" in discovered
    assert "app.tools.registry" in discovered

def test_validate_dependencies():
    registry = ToolRegistry()

    registry.register_tool(
        get_eta_schema(),
        dependencies={"fetch_customer", "missing_tool"},
    )

    registry.register_tool(fetch_customer_schema())

    missing = registry.validate_dependencies("get_eta")

    assert missing == ["missing_tool"]

def test_cache_catalog():
    class FakeRedis:
        def __init__(self):
            self.data = {}

        def setex(self, key, ttl, value):
            self.data[key] = {
                "ttl": ttl,
                "value": value,
            }
            return True

    redis = FakeRedis()
    registry = ToolRegistry(redis_client=redis)

    registry.register_tool(get_eta_schema())

    result = registry.cache_catalog(ttl_seconds=300)

    assert result is True
    assert "fieldops:tools:catalog" in redis.data

def test_cache_catalog_without_redis():
    registry = ToolRegistry()

    registry._redis = None

    result = registry.cache_catalog()

    assert result is False

def test_multiple_tool_versions():
    registry = ToolRegistry()

    v1 = get_eta_schema()

    v2_contract = v1.contract.model_copy(update={"version": "v2"})
    v2 = ToolSchema(v2_contract)

    registry.register_tool(v1)
    registry.register_tool(v2)

    assert registry.get_tool_version("get_eta", "v1") is not None
    assert registry.get_tool_version("get_eta", "v2") is not None


def test_register_and_get_tool():
    registry = ToolRegistry()

    tool = generate_sms_schema()

    registry.register(tool)

    result = registry.get("generate_sms")

    assert result is tool


def test_discover_single_module():
    registry = ToolRegistry()

    result = registry.discover("app.tools.schema")

    assert result == ["app.tools.schema"]


def test_cache_catalog_redis_failure():
    class FailingRedis:
        def setex(self, key, ttl, value):
            raise RuntimeError("Redis unavailable")

    registry = ToolRegistry(redis_client=FailingRedis())

    registry.register_tool(get_eta_schema())

    result = registry.cache_catalog()

    assert result is False

def test_unknown_tool_branches():
    registry = ToolRegistry()

    assert registry.get_dependencies("unknown_tool") is None
    assert registry.validate_dependencies("unknown_tool") == []
    assert registry.check_permission("unknown_tool", "admin") is False
    assert registry.get_version("unknown_tool") is None
    assert registry.get_tool_version("unknown_tool", "v1") is None


def test_list_tools():
    registry = ToolRegistry()

    registry.register_tool(generate_sms_schema())
    registry.register_tool(get_eta_schema())

    result = registry.list_tools()

    assert result == ["generate_sms", "get_eta"]