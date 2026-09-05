import json
import logging
import re
from typing import Any

import bleach
from jsonschema import Draft202012Validator

from app.tools.schema import ValidationResult


logger = logging.getLogger(__name__)


class PIIReport:
    def __init__(self, detected: bool, fields: list[str] | None = None):
        self.detected = detected
        self.fields = fields or []


class ToolInputValidator:
    MAX_STRING_SIZE = 1024
    MAX_OBJECT_SIZE = 10 * 1024
    RATE_LIMIT = 100
    RATE_WINDOW = 60

    SQL_PATTERNS = [
        re.compile(r"'\s*OR\s+\d+\s*=\s*\d+", re.IGNORECASE),
        re.compile(r"\bUNION\s+SELECT\b", re.IGNORECASE),
        re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
        re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
        re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
        re.compile(r"\bUPDATE\s+\w+\s+SET\b", re.IGNORECASE),
    ]

    SHELL_PATTERNS = [
        re.compile(r"\bbash\s+-c\b", re.IGNORECASE),
        re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
        re.compile(r"\bcurl\s+https?://", re.IGNORECASE),
        re.compile(r"\bwget\s+https?://", re.IGNORECASE),
        re.compile(r"\bpowershell(?:\.exe)?\b", re.IGNORECASE),
        re.compile(r"\bcmd(?:\.exe)?\s+/c\b", re.IGNORECASE),
    ]

    PII_PATTERNS = {
        "email": re.compile(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            re.IGNORECASE,
        ),
        "phone": re.compile(
            r"\b(?:\+?\d[\d\s().-]{8,}\d)\b"
        ),
        "credit_card": re.compile(
            r"\b(?:\d[ -]*?){13,19}\b"
        ),
    }

    def __init__(self, redis_client=None):
        self.redis = redis_client

    def validate_schema(
        self,
        parameters: dict[str, Any],
        schema: dict[str, Any],
    ) -> ValidationResult:
        validator = Draft202012Validator(schema)

        errors = sorted(
            validator.iter_errors(parameters),
            key=lambda error: list(error.path),
        )

        if errors:
            return ValidationResult(
                valid=False,
                errors=[error.message for error in errors],
            )

        return ValidationResult(
            valid=True,
            errors=[],
            data=parameters,
        )

    def sanitize_input(self, value: Any) -> Any:
        if isinstance(value, str):
            self._reject_malicious_input(value)

            return bleach.clean(
                value,
                tags=[],
                attributes={},
                protocols=[],
                strip=True,
            )

        if isinstance(value, dict):
            return {
                key: self.sanitize_input(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                self.sanitize_input(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return tuple(
                self.sanitize_input(item)
                for item in value
            )

        return value

    def _reject_malicious_input(self, value: str) -> None:
        for pattern in self.SQL_PATTERNS:
            if pattern.search(value):
                raise ValueError("SQL injection detected")

        for pattern in self.SHELL_PATTERNS:
            if pattern.search(value):
                raise ValueError("shell command detected")

    def check_pii(self, data: Any) -> PIIReport:
        detected_fields: list[str] = []

        def scan(value: Any, path: str = "") -> None:
            if isinstance(value, str):
                for pii_type, pattern in self.PII_PATTERNS.items():
                    if pattern.search(value):
                        detected_fields.append(
                            f"{path}:{pii_type}"
                            if path
                            else pii_type
                        )

            elif isinstance(value, dict):
                for key, item in value.items():
                    child_path = (
                        f"{path}.{key}" if path else str(key)
                    )
                    scan(item, child_path)

            elif isinstance(value, list):
                for index, item in enumerate(value):
                    scan(item, f"{path}[{index}]")

        scan(data)

        return PIIReport(
            detected=bool(detected_fields),
            fields=detected_fields,
        )

    def validate_size(self, data: Any) -> list[str]:
        errors: list[str] = []

        def walk(value: Any, path: str = "") -> None:
            if isinstance(value, str):
                if len(value.encode("utf-8")) > self.MAX_STRING_SIZE:
                    errors.append(
                        f"{path or 'input'} exceeds "
                        f"{self.MAX_STRING_SIZE} bytes"
                    )

            elif isinstance(value, dict):
                try:
                    serialized = json.dumps(
                        value,
                        ensure_ascii=False,
                    ).encode("utf-8")

                    if len(serialized) > self.MAX_OBJECT_SIZE:
                        errors.append(
                            f"{path or 'object'} exceeds "
                            f"{self.MAX_OBJECT_SIZE} bytes"
                        )
                except (TypeError, ValueError):
                    errors.append(
                        f"{path or 'object'} cannot be serialized"
                    )

                for key, item in value.items():
                    child_path = (
                        f"{path}.{key}" if path else str(key)
                    )
                    walk(item, child_path)

            elif isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")

        walk(data)

        return errors

    def check_rate_limit(self, tenant_id: str) -> bool:
        if self.redis is None:
            return True

        key = f"fieldops:tool_rate:{tenant_id}"

        try:
            count = self.redis.incr(key)

            if count == 1:
                self.redis.expire(key, self.RATE_WINDOW)

            return count <= self.RATE_LIMIT

        except Exception:
            logger.exception(
                "Tool rate-limit check failed for tenant %s",
                tenant_id,
            )

            return False

    def validate(
        self,
        parameters: dict[str, Any],
        schema: dict[str, Any],
        tenant_id: str,
    ) -> ValidationResult:
        size_errors = self.validate_size(parameters)

        if size_errors:
            self._log_failure(
                tenant_id,
                parameters,
                size_errors,
            )

            return ValidationResult(
                valid=False,
                errors=size_errors,
            )

        try:
            sanitized = self.sanitize_input(parameters)
        except ValueError as exc:
            errors = [str(exc)]

            self._log_failure(
                tenant_id,
                parameters,
                errors,
            )

            return ValidationResult(
                valid=False,
                errors=errors,
            )

        pii_report = self.check_pii(sanitized)

        if pii_report.detected:
            sanitized = self._sanitize_pii(sanitized)

        schema_result = self.validate_schema(
            sanitized,
            schema,
        )

        if not schema_result.valid:
            self._log_failure(
                tenant_id,
                parameters,
                schema_result.errors,
            )

            return schema_result

        if not self.check_rate_limit(tenant_id):
            errors = ["Tool rate limit exceeded"]

            self._log_failure(
                tenant_id,
                parameters,
                errors,
            )

            return ValidationResult(
                valid=False,
                errors=errors,
            )

        return ValidationResult(
            valid=True,
            errors=[],
            data=sanitized,
        )

    def _sanitize_pii(self, data: Any) -> Any:
        if isinstance(data, str):
            result = data

            for pattern in self.PII_PATTERNS.values():
                result = pattern.sub("[REDACTED]", result)

            return result

        if isinstance(data, dict):
            return {
                key: self._sanitize_pii(value)
                for key, value in data.items()
            }

        if isinstance(data, list):
            return [
                self._sanitize_pii(value)
                for value in data
            ]

        return data

    def _log_failure(
        self,
        tenant_id: str,
        data: Any,
        errors: list[str],
    ) -> None:
        preview = repr(data)

        if len(preview) > 200:
            preview = preview[:200] + "..."

        logger.warning(
            "Tool input validation failed "
            "tenant=%s errors=%s input_preview=%s",
            tenant_id,
            errors,
            preview,
        )