from app.tools.examples import (
    fetch_customer_schema,
    generate_sms_schema,
    get_eta_schema,
)
from app.tools.schema import ToolSchema


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSchema] = {}

    def register(self, tool: ToolSchema) -> None:
        self._tools[tool.contract.name] = tool

    def get(self, name: str) -> ToolSchema | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(generate_sms_schema())
    registry.register(fetch_customer_schema())
    registry.register(get_eta_schema())

    return registry