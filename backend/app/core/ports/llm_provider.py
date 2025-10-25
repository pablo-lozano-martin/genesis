# ABOUTME: LLM provider port interface defining the contract for LLM operations
# ABOUTME: Uses LangChain BaseMessage types for LangGraph-first architecture

from abc import ABC, abstractmethod
from typing import List, AsyncGenerator
from langchain_core.messages import BaseMessage


class ILLMProvider(ABC):
    """
    LLM provider port interface.

    Defines the contract for LLM operations using LangChain BaseMessage types.
    Implementations of this interface (adapters) handle the actual communication
    with different LLM providers (OpenAI, Anthropic, Google, Ollama, etc.) without
    the core domain knowing about provider-specific details.
    """

    @abstractmethod
    async def generate(self, messages: List[BaseMessage]) -> str:
        """
        Generate a response from the LLM based on conversation history.

        Args:
            messages: List of BaseMessage objects (HumanMessage, AIMessage, SystemMessage)
                     representing the conversation history

        Returns:
            Generated response text

        Raises:
            Exception: If LLM generation fails
        """
        pass

    @abstractmethod
    async def stream(self, messages: List[BaseMessage]) -> AsyncGenerator[str, None]:
        """
        Stream a response from the LLM token-by-token.

        Args:
            messages: List of BaseMessage objects representing the conversation history

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
