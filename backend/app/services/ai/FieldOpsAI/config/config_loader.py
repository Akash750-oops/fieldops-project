"""
config_loader.py

Loads the AI configuration from ai.yaml.

This class acts as the single source of truth for all
AI-related configuration such as runtime, provider,
model, prompts, logging, and guardrails.
"""

from pathlib import Path
from typing import Any, Dict

import yaml


class ConfigLoader:
    """
    Loads and exposes AI configuration values.
    """

    def __init__(self) -> None:
        """
        Load the AI configuration file.
        """

        config_path = (
            Path(__file__).resolve().parent / "ai.yaml"
        )

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}"
            )

        config = yaml.safe_load(
            config_path.read_text(encoding="utf-8")
        )

        if not isinstance(config, dict):
            raise ValueError(
                "Invalid ai.yaml: configuration is empty or malformed."
            )

        self._config: Dict[str, Any] = config

    # ---------------------------------------------------------

    def _section(self, name: str) -> Dict[str, Any]:
        """
        Return a configuration section.

        Raises
        ------
        KeyError
            If the section is missing.
        """

        if name not in self._config:
            raise KeyError(
                f"Missing configuration section: '{name}'"
            )

        return self._config[name]

    # ---------------------------------------------------------

    @property
    def runtime(self) -> Dict[str, Any]:
        return self._section("runtime")

    @property
    def provider(self) -> Dict[str, Any]:
        return self._section("provider")

    @property
    def model(self) -> Dict[str, Any]:
        return self._section("model")

    @property
    def prompt(self) -> Dict[str, Any]:
        return self._section("prompt")

    @property
    def logging(self) -> Dict[str, Any]:
        return self._section("logging")

    @property
    def guardrails(self) -> Dict[str, Any]:
        return self._section("guardrails")

    # ---------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return self.provider["name"]

    @property
    def model_name(self) -> str:
        return self.model["name"]

    @property
    def temperature(self) -> float:
        return self.model["temperature"]

    @property
    def max_tokens(self) -> int:
        return self.model["max_tokens"]

    @property
    def runtime_engine(self) -> str:
        return self.runtime["engine"]