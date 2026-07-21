from __future__ import annotations

import re
from enum import Enum
from typing import List, Literal, Optional

from jinja2 import (
    TemplateSyntaxError,
    meta,
    nodes,
)
from jinja2.sandbox import SandboxedEnvironment
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
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
# Shared Jinja environment
# ==========================================================


_SAFE_JINJA_ENVIRONMENT = SandboxedEnvironment()

# Managed prompt templates do not need Jinja's default globals,
# such as range, cycler, joiner, or namespace.
_SAFE_JINJA_ENVIRONMENT.globals.clear()


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


def _reject_unsafe_jinja_nodes(
    parsed_template,
) -> None:
    """
    Reject access to Python dunder names.

    Examples rejected:

        {{ customer.__class__ }}
        {{ customer["__class__"] }}
        {{ __builtins__ }}
    """

    for node in parsed_template.find_all(
        nodes.Name
    ):
        if "__" in node.name:
            raise ValueError(
                "Unsafe Jinja access is not permitted."
            )

    for node in parsed_template.find_all(
        nodes.Getattr
    ):
        if "__" in node.attr:
            raise ValueError(
                "Unsafe Jinja access is not permitted."
            )

    for node in parsed_template.find_all(
        nodes.Getitem
    ):
        argument = getattr(
            node,
            "arg",
            None,
        )

        if (
            isinstance(argument, nodes.Const)
            and isinstance(
                argument.value,
                str,
            )
            and "__" in argument.value
        ):
            raise ValueError(
                "Unsafe Jinja access is not permitted."
            )


def _parse_template(
    template_source: str,
):
    """
    Parse one Jinja template and reject unsafe syntax.
    """

    try:
        parsed = (
            _SAFE_JINJA_ENVIRONMENT.parse(
                template_source
            )
        )

    except TemplateSyntaxError:
        raise ValueError(
            "Invalid Jinja syntax."
        ) from None

    _reject_unsafe_jinja_nodes(
        parsed
    )

    return parsed


def _validate_jinja_variables(
    body: str,
    variables: List[str],
    title: Optional[str] = None,
) -> None:
    """
    Validate Jinja syntax and declared variables.

    Rules:

    - Variable names must be valid identifiers.
    - Duplicate declarations are rejected.
    - Dunder names are rejected.
    - Every referenced variable must be declared.
    - Every declared variable must be referenced.
    """

    normalized_variables: list[str] = []

    for variable in variables:
        if not isinstance(
            variable,
            str,
        ):
            raise ValueError(
                "Template variables must be strings."
            )

        normalized = variable.strip()

        if "__" in normalized:
            raise ValueError(
                "Unsafe variable names are not permitted."
            )

        if not re.fullmatch(
            r"[a-zA-Z_][a-zA-Z0-9_]*",
            normalized,
        ):
            raise ValueError(
                "A declared variable is not a valid identifier."
            )

        normalized_variables.append(
            normalized
        )

    if (
        len(normalized_variables)
        != len(set(normalized_variables))
    ):
        raise ValueError(
            "Duplicate variable names are not permitted."
        )

    body_ast = _parse_template(
        body
    )

    referenced_variables = set(
        meta.find_undeclared_variables(
            body_ast
        )
    )

    if title is not None:
        title_ast = _parse_template(
            title
        )

        referenced_variables.update(
            meta.find_undeclared_variables(
                title_ast
            )
        )

    declared_variables = set(
        normalized_variables
    )

    missing_declarations = (
        referenced_variables
        - declared_variables
    )

    if missing_declarations:
        raise ValueError(
            "Undeclared variables referenced in template."
        )

    unused_declarations = (
        declared_variables
        - referenced_variables
    )

    if unused_declarations:
        raise ValueError(
            "Declared variables are not referenced in template."
        )


# ==========================================================
# Base model
# ==========================================================


class PromptTemplateBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
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

    variables: List[str] = Field(
        default_factory=list
    )

    is_active: bool = True

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
        str_strip_whitespace=True,
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
        List[str]
    ] = None

    is_active: Optional[bool] = None

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
        str_strip_whitespace=True,
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

    variables: List[str] = Field(
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