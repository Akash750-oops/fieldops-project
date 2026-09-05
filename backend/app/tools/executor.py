from typing import Any

from app.tools.registry import ToolRegistry, RegisteredTool
from app.tools.validation import ToolInputValidator
from app.tools.schema import ValidationResult


class ToolExecutor:
    """
    Validates and executes registered tools.

    Execution flow:
        Registry -> Validation -> Handler
    """

    def __init__(
        self,
        registry: ToolRegistry,
        validator: ToolInputValidator | None = None,
    ):
        self.registry = registry
        self.validator = validator or ToolInputValidator()

    def execute(
        self,
        tool_id: str,
        parameters: dict[str, Any],
        tenant_id: str,
    ) -> Any:
        registered_tool = self.registry.get_tool(tool_id)

        if registered_tool is None:
            raise ValueError(f"Tool '{tool_id}' not found")

        if registered_tool.handler is None:
            raise ValueError(
                f"Tool '{tool_id}' has no executable handler"
            )

        validation_result = self.validator.validate(
            parameters=parameters,
            schema=registered_tool.schema.generate_json_schema()[
                "parameters"
            ],
            tenant_id=tenant_id,
        )

        if not validation_result.valid:
            raise ValueError(
                "; ".join(validation_result.errors)
            )

        return registered_tool.handler(
            **(validation_result.data or {})
        )