"""
provider_factory.py

Factory responsible for creating the configured AI provider.

The rest of the application should NEVER instantiate
GroqProvider or AnthropicProvider directly.

Always use:

    ProviderFactory.create_provider()
"""

from app.services.ai.FieldOpsAI.config.config_loader import ConfigLoader

from app.services.ai.FieldOpsAI.providers.base_provider import BaseAIProvider
from app.services.ai.FieldOpsAI.providers.groq_provider import GroqProvider

# Production provider
# (we'll build this later)
# from app.services.ai.FieldOpsAI.providers.anthropic_provider import AnthropicProvider


class ProviderFactory:
    """
    Factory for creating AI providers.
    """

    @staticmethod
    def create_provider() -> BaseAIProvider:

        config = ConfigLoader()

        provider_name = config.provider_name.lower()

        if provider_name == "groq":
            return GroqProvider()

        # Future production provider
        # if provider_name == "anthropic":
        #     return AnthropicProvider()

        raise ValueError(
            f"Unsupported AI provider: {provider_name}"
        )