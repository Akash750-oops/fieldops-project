from __future__ import annotations

import re
from enum import Enum
from typing import List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.services.ai.FieldOpsAI.schemas.prompt_variable import PromptVariableDeclaration
from app.services.ai.FieldOpsAI.services.prompt_variable_injector import (
    PromptVariableInjector,
    PromptVariableInjectionError,
)



# ==========================================================
# Supported values
# ==========================================================


class AgentType(str, Enum):
    CommsAgent = "CommsAgent"
    SentimentAgent = "SentimentAgent"


class PromptChannel(str, Enum):
    sms = "sms"
    email = "email"
    push = "push"
    portal = "portal"

    @classmethod
    def _missing_(
        cls,
        value,
    ):
        # The existing database uses "in_app".
        # The Task 5.1 API exposes it as "portal".
        if value == "in_app":
            return cls.portal

        return super()._missing_(value)


class PromptLanguage(str, Enum):
    en = "en"
    es = "es"
    ta = "ta"
    hi = "hi"


# ==========================================================
# Shared validation helpers
# ==========================================================


def _validate_status_value(
    value: str,
) -> str:
    """
    Normalize and validate a prompt status.
    """

    normalized = value.strip().lower()

    if not normalized:
        raise ValueError(
            "Status cannot be blank."
        )

    if not re.fullmatch(
        r"[a-z0-9_]+",
        normalized,
    ):
        raise ValueError(
            "Status must use lowercase snake_case."
        )

    return normalized


def _validate_jinja_variables(
    body: str,
    variables: list[PromptVariableDeclaration],
    title: Optional[str] = None,
) -> None:
    try:
        PromptVariableInjector().validate(body, variables, title)
    except PromptVariableInjectionError as e:
        raise ValueError(str(e)) from None

# ==========================================================
# Base model
# ==========================================================


class PromptTemplateBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    name: str = Field(
        ...,
        min_length=1,
    )

    agent_type: AgentType

    channel: PromptChannel

    language: PromptLanguage

    status: str = Field(
        ...,
        min_length=1,
    )

    body: str = Field(
        ...,
        min_length=1,
    )

    title: Optional[str] = None

    variables: List[PromptVariableDeclaration] = Field(
        default_factory=list
    )

    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Name cannot be blank."
            )

        return normalized

    @field_validator("status")
    @classmethod
    def validate_status(
        cls,
        value: str,
    ) -> str:
        return _validate_status_value(
            value
        )

    @model_validator(mode="after")
    def validate_template_content(
        self,
    ) -> "PromptTemplateBase":
        _validate_jinja_variables(
            body=self.body,
            variables=self.variables,
            title=self.title,
        )

        return self


# ==========================================================
# Create
# ==========================================================


class PromptTemplateCreate(
    PromptTemplateBase
):
    version: int = Field(
        default=1,
        ge=1,
    )


# ==========================================================
# Update
# ==========================================================


class PromptTemplateUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    name: Optional[str] = Field(
        default=None,
        min_length=1,
    )

    agent_type: Optional[
        AgentType
    ] = None

    channel: Optional[
        PromptChannel
    ] = None

    language: Optional[
        PromptLanguage
    ] = None

    status: Optional[str] = Field(
        default=None,
        min_length=1,
    )

    body: Optional[str] = Field(
        default=None,
        min_length=1,
    )

    title: Optional[str] = None

    variables: Optional[
        List[PromptVariableDeclaration]
    ] = None

    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            return value.strip()
        return value

    @field_validator("status")
    @classmethod
    def validate_status(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        return _validate_status_value(
            value
        )


# ==========================================================
# Standard response
# ==========================================================


class PromptTemplateResponse(
    PromptTemplateBase
):
    id: int

    version: int = Field(
        ge=1
    )


# ==========================================================
# Lookup response
# ==========================================================


class PromptTemplateLookupResponse(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid",
    )

    id: Optional[int]

    name: str = Field(
        min_length=1
    )

    agent_type: AgentType

    channel: PromptChannel

    language: PromptLanguage

    status: str = Field(
        min_length=1
    )

    body: str = Field(
        min_length=1
    )

    title: Optional[str] = None

    variables: List[PromptVariableDeclaration] = Field(
        default_factory=list
    )

    version: Optional[int] = Field(
        default=None,
        ge=1,
    )

    is_active: bool

    source: Literal[
        "tenant",
        "platform",
        "builtin_default",
    ]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("status")
    @classmethod
    def validate_status(
        cls,
        value: str,
    ) -> str:
        return _validate_status_value(
            value
        )

    @model_validator(mode="after")
    def validate_lookup_template(
        self,
    ) -> "PromptTemplateLookupResponse":
        _validate_jinja_variables(
            body=self.body,
            variables=self.variables,
            title=self.title,
        )

        return self

def test_whitespace_only_name_returns_400(
    api_client,
):
    payload = prompt_payload()
    payload["name"] = "   "

    response = api_client.post(
        "/admin/prompts",
        json=payload,
        headers=get_headers(),
    )

    assert response.status_code == 400