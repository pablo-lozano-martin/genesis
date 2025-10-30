# ABOUTME: Ollama LLM provider implementation using LangChain
# ABOUTME: Implements ILLMProvider port interface for local Ollama models with native BaseMessage support

from typing import List, AsyncGenerator, Callable, Any
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel

from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class OllamaProvider(ILLMProvider):
    """
    Ollama LLM provider implementation.

    This adapter implements the ILLMProvider port using local Ollama models
    through LangChain's ChatOllama integration. Works directly with
    LangChain BaseMessage types (HumanMessage, AIMessage, SystemMessage).
    """

    def __init__(self):
        """Initialize the Ollama provider with configured model."""
        if not settings.ollama_model:
            raise ValueError(
                "OLLAMA_MODEL is not configured. "
                "Please set OLLAMA_MODEL in your .env file (e.g., llama2)."
            )

        if not settings.ollama_base_url:
            raise ValueError(
                "OLLAMA_BASE_URL is not configured. "
                "Please set OLLAMA_BASE_URL in your .env file (e.g., http://localhost:11434)."
            )

        self.model = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.7
        )
        logger.info(f"Initialized Ollama provider with model: {settings.ollama_model} at {settings.ollama_base_url}")

    async def generate(self, messages: List[BaseMessage]) -> BaseMessage:
        """
        Generate a response from Ollama based on conversation history.

        Args:
            messages: List of BaseMessage objects representing the conversation history

        Returns:
            Generated response as AIMessage (may include tool_calls)

        Raises:
            Exception: If LLM generation fails
        """
        try:
            response = await self.model.ainvoke(messages)
            return response
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise Exception(f"Failed to generate response from Ollama: {str(e)}")

    async def stream(self, messages: List[BaseMessage]) -> AsyncGenerator[str, None]:
        """
        Stream a response from Ollama token-by-token.

        Args:
            messages: List of BaseMessage objects representing the conversation history

        Yields:
            Response tokens as they are generated

        Raises:
            Exception: If LLM streaming fails
        """
        try:
            async for chunk in self.model.astream(messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise Exception(f"Failed to stream response from Ollama: {str(e)}")

    async def get_model_name(self) -> str:
        """
        Get the name of the current Ollama model being used.

        Returns:
            Model name (e.g., "llama2")
        """
        return settings.ollama_model

    def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
        """
        Bind tools to the Ollama provider for tool calling.

        Args:
            tools: List of callable tools to bind
            **kwargs: Additional keyword arguments for binding

        Returns:
            A new OllamaProvider instance with tools bound
        """
        bound_model = self.model.bind_tools(tools, **kwargs)
        # Create a new instance with the bound model
        new_provider = OllamaProvider.__new__(OllamaProvider)
        new_provider.model = bound_model
        return new_provider

    def get_model(self) -> BaseChatModel:
        """
        Get the underlying LangChain ChatModel instance.

        Used by LangGraph prebuilt agents that require native LangChain models.

        Returns:
            Underlying ChatOllama model instance
        """
        return self.model
