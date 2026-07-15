"""
base_provider.py

Purpose
-------
Defines the common interface that every AI provider
(Groq, OpenAI, Anthropic, Ollama, etc.)
must implement.

The rest of the application communicates only through
this interface and never interacts with a provider
implementation directly.

Benefits
--------
- Provider independence
- Easy provider replacement
- Easier testing and mocking
- Cleaner architecture
- Better maintainability
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Sequence


class BaseAIProvider(ABC):
    """
    Abstract interface implemented by every AI provider.
    """

    @abstractmethod
    def generate_completion(
        self,
        messages: Sequence[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a chat completion.

        Parameters
        ----------
        messages
            Conversation messages in OpenAI-compatible format.

        temperature
            Optional override for model creativity.

        max_tokens
            Optional maximum response length.

        Returns
        -------
        str
            Raw AI response.
        """
        raise NotImplementedError

    @abstractmethod
    def provider_name(self) -> str:
        """
        Return the provider name.

        Examples
        --------
        Groq
        OpenAI
        Anthropic
        Ollama
        """
        raise NotImplementedError

    @abstractmethod
    def model_name(self) -> str:
        """
        Return the configured model name.

        Examples
        --------
        llama-3.3-70b-versatile
        gpt-4.1
        claude-sonnet-4
        mistral-large
        """
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verify that the provider is reachable.

        Returns
        -------
        bool
            True if the provider is healthy, otherwise False.
        """
        raise NotImplementedError