"""
groq_provider.py

Concrete implementation of BaseAIProvider using the Groq API.

Responsibilities
----------------
- Connect to the Groq API.
- Send prompts to the configured model.
- Return the model response.

This provider contains NO business logic.
It is responsible only for communication with Groq.

The provider is intentionally provider-agnostic so that
it can later be replaced by Claude, OpenAI, Ollama,
or any other provider without changing the rest of the application.
"""

import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq
import logging

from app.services.ai.FieldOpsAI.config.config_loader import ConfigLoader
from app.services.ai.FieldOpsAI.providers.base_provider import BaseAIProvider
logger = logging.getLogger(__name__)

load_dotenv()


class GroqProvider(BaseAIProvider):
    """
    Groq implementation of the AI provider interface.
    """

    def __init__(self):
        """
        Initialize the Groq client using the configured API key.
        """

        self.config = ConfigLoader()

        self.api_key = os.getenv("GROQ_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable was not found."
            )

        self.client = Groq(
            api_key=self.api_key
        )

        self.model = self.config.model_name

        self.default_temperature = self.config.temperature

        self.default_max_tokens = self.config.max_tokens

    # ---------------------------------------------------------

    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send a completion request to Groq.

        Parameters
        ----------
        messages
            Chat messages for the model.

        temperature
            Optional temperature override.

        max_tokens
            Optional max token override.

        Returns
        -------
        str
            Model response.
        """
        logger.info(
            "Sending request to Groq model '%s'.",
            self.model,
        )
        try:

            response = self.client.chat.completions.create(

                model=self.model,

                messages=messages,

                temperature=(
                    temperature
                    if temperature is not None
                    else self.default_temperature
                ),

                max_tokens=(
                    max_tokens
                    if max_tokens is not None
                    else self.default_max_tokens
                ),

            )
            

            if not response.choices:
                raise RuntimeError(
                    "Groq returned no choices."
                )

            content = response.choices[0].message.content

            if content is None:
                raise RuntimeError(
                    "Groq returned an empty response."
                )
            logger.info(
                "Groq response received successfully."
            )

            return content.strip()

        except Exception as ex:
            logger.exception(
                "Groq API request failed."
            )

            raise RuntimeError(
                f"Groq API Error: {str(ex)}"
            )

    # ---------------------------------------------------------

    def provider_name(self) -> str:
        """
        Returns the provider name.
        """

        return "Groq"

    # ---------------------------------------------------------

    def model_name(self) -> str:
        """
        Returns the configured model.
        """

        return self.model

    # ---------------------------------------------------------

    def health_check(self) -> bool:
        """
        Verify that Groq is reachable.

        Returns
        -------
        bool
            True if reachable.
        """

        try:

            self.client.chat.completions.create(

                model=self.model,

                messages=[
                    {
                        "role": "user",
                        "content": "health check"
                    }
                ],

                temperature=0,

                max_tokens=5,

            )

            return True

        except Exception:

            return False