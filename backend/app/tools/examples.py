from app.tools.schema import (
    ToolContract,
    ToolParameter,
    ToolReturn,
    ToolSchema,
)


def generate_sms_schema() -> ToolSchema:
    contract = ToolContract(
        name="generate_sms",
        description="Generate an SMS message for a customer",
        version="v1",
        parameters=[
            ToolParameter(
                name="message",
                type="string",
                description="SMS message content",
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
            description="Generated SMS message",
            schema={"type": "string"},
        ),
    )

    return ToolSchema(contract)


def fetch_customer_schema() -> ToolSchema:
    contract = ToolContract(
        name="fetch_customer",
        description="Fetch customer information using the customer ID",
        version="v1",
        parameters=[
            ToolParameter(
                name="customer_id",
                type="string",
                description="Unique customer identifier",
                required=True,
            ),
        ],
        required=["customer_id"],
        returns=ToolReturn(
            type="object",
            description="Customer information",
            schema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                },
            },
        ),
    )

    return ToolSchema(contract)


def get_eta_schema() -> ToolSchema:
    contract = ToolContract(
        name="get_eta",
        description="Calculate the estimated arrival time for a technician",
        version="v1",
        parameters=[
            ToolParameter(
                name="job_id",
                type="string",
                description="Unique job identifier",
                required=True,
            ),
            ToolParameter(
                name="latitude",
                type="number",
                description="Customer latitude",
                required=True,
            ),
            ToolParameter(
                name="longitude",
                type="number",
                description="Customer longitude",
                required=True,
            ),
        ],
        required=["job_id", "latitude", "longitude"],
        returns=ToolReturn(
            type="object",
            description="Estimated arrival information",
            schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "eta_minutes": {"type": "integer"},
                },
            },
        ),
    )

    return ToolSchema(contract)