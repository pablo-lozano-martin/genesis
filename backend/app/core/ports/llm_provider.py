# ABOUTME: LLM provider port interface defining the contract for LLM operations
# ABOUTME: Abstract interface following hexagonal architecture principles

from abc import ABC, abstractmethod
from typing import List, AsyncGenerator

from app.core.domain.message import Message


class ILLMProvider(ABC):
    """
    LLM provider port interface.

    Defines the contract for LLM operations. Implementations of this
    interface (adapters) handle the actual communication with different
    LLM providers (OpenAI, Anthropic, Google, Ollama, etc.) without
    the core domain knowing about provider-specific details.
    """

    @abstractmethod
    async def generate(self, messages: List[Message]) -> str:
        """
        Generate a response from the LLM based on conversation history.

        Args:
            messages: List of messages representing the conversation history

        Returns:
            Generated response text

        Raises:
            Exception: If LLM generation fails
        """
        pass

    @abstractmethod
    async def stream(self, messages: List[Message]) -> AsyncGenerator[str, None]:
        """
        Stream a response from the LLM token-by-token.

        Args:
            messages: List of messages representing the conversation history

        Yields:
            Response tokens as they are generated

        Raises:
            Exception: If LLM streaming fails
        """
        pass

    @abstractmethod
    async def get_model_name(self) -> str:
        """
        Get the name of the current model being used.

        Returns:
            Model name (e.g., "gpt-4-turbo-preview", "claude-3-sonnet-20240229")
        """
        pass
