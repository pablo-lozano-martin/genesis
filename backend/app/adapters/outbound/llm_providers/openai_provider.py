# ABOUTME: OpenAI LLM provider implementation using LangChain
# ABOUTME: Implements ILLMProvider port interface for OpenAI models with native BaseMessage support

from typing import List, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage

from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class OpenAIProvider(ILLMProvider):
    """
    OpenAI LLM provider implementation.

    This adapter implements the ILLMProvider port using OpenAI's API
    through LangChain's ChatOpenAI integration. Works directly with
    LangChain BaseMessage types (HumanMessage, AIMessage, SystemMessage).
    """

    def __init__(self):
        """Initialize the OpenAI provider with configured model."""
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Please set OPENAI_API_KEY in your .env file."
            )

        if not settings.openai_model:
            raise ValueError(
                "OPENAI_MODEL is not configured. "
                "Please set OPENAI_MODEL in your .env file (e.g., gpt-4-turbo-preview)."
            )

        self.model = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.7,
            streaming=True
        )
        logger.info(f"Initialized OpenAI provider with model: {settings.openai_model}")

    async def generate(self, messages: List[BaseMessage]) -> str:
        """
        Generate a response from OpenAI based on conversation history.

        Args:
            messages: List of BaseMessage objects representing the conversation history

        Returns:
            Generated response text

        Raises:
            Exception: If LLM generation fails
        """
        try:
            response = await self.model.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise Exception(f"Failed to generate response from OpenAI: {str(e)}")

    async def stream(self, messages: List[BaseMessage]) -> AsyncGenerator[str, None]:
        """
        Stream a response from OpenAI token-by-token.

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
            logger.error(f"OpenAI streaming failed: {e}")
            raise Exception(f"Failed to stream response from OpenAI: {str(e)}")

    async def get_model_name(self) -> str:
        """
        Get the name of the current OpenAI model being used.

        Returns:
            Model name (e.g., "gpt-4-turbo-preview")
        """
        return settings.openai_model
