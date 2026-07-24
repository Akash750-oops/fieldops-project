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
from app.services.ai.FieldOpsAI.services.prompt_locale_service import (
    normalize_locale,
    InvalidLocaleError,
)


# ==========================================================
# Supported values
# ==========================================================


TemplateFormat = Literal["text", "html"]

_VALID_FORMATS: frozenset[str] = frozenset({"text", "html"})


def _validate_format_value(value: str) -> str:
    """
    Normalize and validate a template format.

    Accepts surrounding whitespace and uppercase, then
    rejects any value that is not ``text`` or ``html``.
    """
    if not isinstance(value, str):
        raise ValueError("Format must be a string.")

    normalized = value.strip().lower()

    if normalized not in _VALID_FORMATS:
        raise ValueError(
            "Format must be 'text' or 'html'."
        )

    return normalized


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
    except PromptVariableInjectionError:
        raise ValueError("Template validation failed.") from None

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

    language: str

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        try:
            return normalize_locale(value)
        except InvalidLocaleError:
            raise ValueError("Template validation failed.") from None

    status: str = Field(
        ...,
        min_length=1,
    )

    body: str = Field(
        ...,
        min_length=1,
    )

    format: TemplateFormat = Field(
        default="text",
    )

    @field_validator(
        "format",
        mode="before",
    )
    @classmethod
    def validate_format(
        cls,
        value: str,
    ) -> str:
        return _validate_format_value(value)

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




# ==========================================================
# Create
# ==========================================================


class PromptTemplateCreate(
    PromptTemplateBase
):
    @model_validator(mode="after")
    def validate_create_content(
        self,
    ) -> "PromptTemplateCreate":
        _validate_jinja_variables(
            body=self.body,
            variables=self.variables,
            title=self.title,
        )

        return self


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

    language: Optional[str] = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            return normalize_locale(value)
        except InvalidLocaleError:
            raise ValueError("Template validation failed.") from None

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

    format: Optional[TemplateFormat] = None

    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Name cannot be blank."
            )

        return normalized

    @field_validator(
        "format",
        mode="before",
    )
    @classmethod
    def validate_format(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        return _validate_format_value(value)

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

    language: str

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        try:
            return normalize_locale(value)
        except InvalidLocaleError:
            raise ValueError("Template validation failed.") from None

    status: str = Field(
        min_length=1
    )

    body: str = Field(
        min_length=1
    )

    format: TemplateFormat = Field(
        default="text",
    )

    @field_validator(
        "format",
        mode="before",
    )
    @classmethod
    def validate_format(
        cls,
        value: str,
    ) -> str:
        return _validate_format_value(value)

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