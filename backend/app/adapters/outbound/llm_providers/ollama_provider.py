# ABOUTME: Ollama LLM provider implementation using LangChain
# ABOUTME: Implements ILLMProvider port interface for local Ollama models

from typing import List, AsyncGenerator
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.ports.llm_provider import ILLMProvider
from app.core.domain.message import Message, MessageRole
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class OllamaProvider(ILLMProvider):
    """
    Ollama LLM provider implementation.

    This adapter implements the ILLMProvider port using local Ollama models
    through LangChain's ChatOllama integration.
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

    def _convert_messages(self, messages: List[Message]) -> List:
        """
        Convert domain Message objects to LangChain message format.

        Args:
            messages: List of domain message objects

        Returns:
            List of LangChain message objects
        """
        langchain_messages = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == MessageRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=msg.content))

        return langchain_messages

    async def generate(self, messages: List[Message]) -> str:
        """
        Generate a response from Ollama based on conversation history.

        Args:
            messages: List of messages representing the conversation history

        Returns:
            Generated response text

        Raises:
            Exception: If LLM generation fails
        """
        try:
            langchain_messages = self._convert_messages(messages)
            response = await self.model.ainvoke(langchain_messages)
            return response.content
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise Exception(f"Failed to generate response from Ollama: {str(e)}")

    async def stream(self, messages: List[Message]) -> AsyncGenerator[str, None]:
        """
        Stream a response from Ollama token-by-token.

        Args:
            messages: List of messages representing the conversation history

        Yields:
            Response tokens as they are generated

        Raises:
            Exception: If LLM streaming fails
        """
        try:
            langchain_messages = self._convert_messages(messages)
            async for chunk in self.model.astream(langchain_messages):
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
