from app.tools.schema import (
    ToolParameter,
    ToolReturn,
    ToolContract,
    ToolSchema,
)
from jsonschema import Draft202012Validator
from app.tools.registry import create_default_registry
import pytest

from app.tools.examples import (
    generate_sms_schema,
    fetch_customer_schema,
    get_eta_schema,
)


def test_tool_parameter_creation():
    parameter = ToolParameter(
        name="message",
        type="string",
        description="SMS message",
        required=True,
    )

    assert parameter.name == "message"
    assert parameter.type == "string"
    assert parameter.description == "SMS message"
    assert parameter.required is True

def test_tool_return_creation():
    result = ToolReturn(
        type="string",
        description="Generated SMS",
        schema={"type": "string"},
    )

    assert result.type == "string"
    assert result.description == "Generated SMS"
    assert result.return_schema == {"type": "string"}
    assert result.model_dump(by_alias=True)["schema"] == {
        "type": "string"
    }


def test_tool_contract_creation():
    contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS",
        version="v1",
        parameters=[
            ToolParameter(
                name="message",
                type="string",
                description="SMS content",
                required=True,
            )
        ],
        required=["message"],
        returns=ToolReturn(
            type="string",
            description="Generated SMS",
            schema={"type": "string"},
        ),
    )

    assert contract.name == "generate_sms"
    assert contract.description == "Generate an SMS"
    assert contract.version == "v1"
    assert len(contract.parameters) == 1
    assert contract.required == ["message"]
    assert contract.returns.type == "string"

def test_generate_json_schema():
    contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS",
        parameters=[
            ToolParameter(
                name="message",
                type="string",
                description="SMS content",
                required=True,
            ),
            ToolParameter(
                name="priority",
                type="string",
                description="Message priority",
                default="normal",
            ),
        ],
        required=["message"],
        returns=ToolReturn(
            type="string",
            description="Generated SMS",
            schema={"type": "string"},
        ),
    )

    tool_schema = ToolSchema(contract)
    schema = tool_schema.generate_json_schema()

    assert schema["name"] == "generate_sms"
    assert schema["description"] == "Generate an SMS"

    assert schema["parameters"]["type"] == "object"
    assert "message" in schema["parameters"]["properties"]
    assert "priority" in schema["parameters"]["properties"]

    assert schema["parameters"]["properties"]["message"]["type"] == "string"
    assert schema["parameters"]["properties"]["priority"]["default"] == "normal"

    assert schema["parameters"]["required"] == ["message"]

def test_validate_input_rejects_missing_required_parameter():
    contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS",
        parameters=[
            ToolParameter(
                name="message",
                type="string",
                description="SMS content",
                required=True,
            )
        ],
        required=["message"],
        returns=ToolReturn(
            type="string",
            description="Generated SMS",
            schema={"type": "string"},
        ),
    )

    tool_schema = ToolSchema(contract)

    result = tool_schema.validate_input({})

    assert result.valid is False
    assert result.data is None
    assert len(result.errors) == 1
    assert "required property" in result.errors[0]


def test_validate_input_accepts_valid_data():
    contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS",
        parameters=[
            ToolParameter(
                name="message",
                type="string",
                description="SMS content",
                required=True,
            )
        ],
        required=["message"],
        returns=ToolReturn(
            type="string",
            description="Generated SMS",
            schema={"type": "string"},
        ),
    )

    tool_schema = ToolSchema(contract)

    result = tool_schema.validate_input(
        {"message": "Hello customer"}
    )

    assert result.valid is True
    assert result.errors == []
    assert result.data == {"message": "Hello customer"}


def test_validate_input_applies_default_value():
    contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS",
        parameters=[
            ToolParameter(
                name="message",
                type="string",
                description="SMS content",
                required=True,
            ),
            ToolParameter(
                name="priority",
                type="string",
                description="Message priority",
                default="normal",
            ),
        ],
        required=["message"],
        returns=ToolReturn(
            type="string",
            description="Generated SMS",
            schema={"type": "string"},
        ),
    )

    tool_schema = ToolSchema(contract)

    result = tool_schema.validate_input(
        {"message": "Hello customer"}
    )

    assert result.valid is True
    assert result.errors == []
    assert result.data == {
        "message": "Hello customer",
        "priority": "normal",
    }

def test_validate_input_rejects_invalid_type():
    contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS",
        parameters=[
            ToolParameter(
                name="message",
                type="string",
                description="SMS content",
                required=True,
            )
        ],
        required=["message"],
        returns=ToolReturn(
            type="string",
            description="Generated SMS",
            schema={"type": "string"},
        ),
    )

    tool_schema = ToolSchema(contract)

    result = tool_schema.validate_input(
        {"message": 12345}
    )

    assert result.valid is False
    assert result.data is None
    assert len(result.errors) == 1
    assert "is not of type 'string'" in result.errors[0]

def test_tool_parameter_rejects_invalid_json_type():
    with pytest.raises(ValueError, match="Invalid JSON Schema type"):
        ToolParameter(
            name="age",
            type="wrong",
            description="Age",
        )
    
    
def test_generate_openapi_schema():
    contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS",
        version="v1",
        parameters=[
            ToolParameter(
                name="message",
                type="string",
                description="SMS content",
                required=True,
            )
        ],
        required=["message"],
        returns=ToolReturn(
            type="string",
            description="Generated SMS",
            schema={"type": "string"},
        ),
    )

    tool_schema = ToolSchema(contract)

    schema = tool_schema.generate_openapi_schema()

    assert schema["name"] == "generate_sms"
    assert schema["description"] == "Generate an SMS"

    assert schema["requestBody"]["required"] is True
    assert "application/json" in schema["requestBody"]["content"]

    request_schema = schema["requestBody"]["content"]["application/json"]["schema"]

    assert request_schema["type"] == "object"
    assert "message" in request_schema["properties"]
    assert request_schema["required"] == ["message"]

    assert "200" in schema["responses"]

    response_schema = (
        schema["responses"]["200"]["content"]["application/json"]["schema"]
    )

    assert response_schema == {"type": "string"}

def test_tool_contract_versioning():
    v1_contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS",
        version="v1",
        returns=ToolReturn(
            type="string",
            description="Generated SMS",
            schema={"type": "string"},
        ),
    )

    v2_contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS",
        version="v2",
        returns=ToolReturn(
            type="string",
            description="Generated SMS",
            schema={"type": "string"},
        ),
    )

    assert v1_contract.version == "v1"
    assert v2_contract.version == "v2"
    assert v1_contract.version != v2_contract.version

def test_tool_contract_rejects_unknown_required_parameter():
    with pytest.raises(
        ValueError,
        match="Required parameters not defined",
    ):
        ToolContract(
            name="test_tool",
            description="Test",
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="Message",
                )
            ],
            required=["unknown"],
            returns=ToolReturn(
                type="string",
                description="Result",
                schema={"type": "string"},
            ),
        )

def test_tool_contract_rejects_duplicate_parameters():
    with pytest.raises(
        ValueError,
        match="Parameter names must be unique",
    ):
        ToolContract(
            name="test_tool",
            description="Test",
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="Message",
                ),
                ToolParameter(
                    name="message",
                    type="string",
                    description="Duplicate message",
                ),
            ],
            returns=ToolReturn(
                type="string",
                description="Result",
                schema={"type": "string"},
            ),
        )


def test_tool_contract_rejects_required_flag_mismatch():
    with pytest.raises(
        ValueError,
        match="marked required but is missing",
    ):
        ToolContract(
            name="test_tool",
            description="Test",
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="Message",
                    required=True,
                )
            ],
            required=[],
            returns=ToolReturn(
                type="string",
                description="Result",
                schema={"type": "string"},
            ),
        )

def test_generate_sms_example_schema():
    tool = generate_sms_schema()

    assert tool.contract.name == "generate_sms"
    assert tool.contract.version == "v1"
    assert "message" in tool.contract.required
    assert "priority" not in tool.contract.required

def test_fetch_customer_example_schema():
    tool = fetch_customer_schema()

    assert tool.contract.name == "fetch_customer"
    assert tool.contract.version == "v1"
    assert tool.contract.required == ["customer_id"]

def test_get_eta_example_schema():
    tool = get_eta_schema()

    assert tool.contract.name == "get_eta"
    assert tool.contract.version == "v1"
    assert tool.contract.required == [
        "job_id",
        "latitude",
        "longitude",
    ]

def test_registry_discovers_all_tools():
    registry = create_default_registry()

    tools = registry.list_tools()

    assert "generate_sms" in tools
    assert "fetch_customer" in tools
    assert "get_eta" in tools
    assert len(tools) == 3

def test_registry_get_tool():
    registry = create_default_registry()

    tool = registry.get("get_eta")

    assert tool is not None
    assert tool.contract.name == "get_eta"
    assert tool.contract.version == "v1"


def test_registry_returns_none_for_unknown_tool():
    registry = create_default_registry()

    tool = registry.get("unknown_tool")

    assert tool is None

def test_get_tool_signature():
    contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS",
        parameters=[
            ToolParameter(
                name="message",
                type="string",
                description="SMS content",
                required=True,
            ),
            ToolParameter(
                name="priority",
                type="string",
                description="Message priority",
                default="normal",
            ),
        ],
        required=["message"],
        returns=ToolReturn(
            type="string",
            description="Generated SMS",
            schema={"type": "string"},
        ),
    )

    tool_schema = ToolSchema(contract)

    signature = tool_schema.get_tool_signature()

    assert signature == (
        "generate_sms("
        "message: string (required) - SMS content, "
        "priority: string (optional) - Message priority"
        ") -> string: Generated SMS"
    )


def test_generated_json_schema_is_valid():
    tool = generate_sms_schema()

    schema = tool.generate_json_schema()["parameters"]

    Draft202012Validator.check_schema(schema)


def test_all_example_schemas_are_valid():
    tools = [
        generate_sms_schema(),
        fetch_customer_schema(),
        get_eta_schema(),
    ]

    for tool in tools:
        schema = tool.generate_json_schema()["parameters"]
        Draft202012Validator.check_schema(schema)