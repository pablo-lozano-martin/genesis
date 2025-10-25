# ABOUTME: Anthropic (Claude) LLM provider implementation using LangChain
# ABOUTME: Implements ILLMProvider port interface for Anthropic models

from typing import List, AsyncGenerator
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage

from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class AnthropicProvider(ILLMProvider):
    """
    Anthropic (Claude) LLM provider implementation.

    This adapter implements the ILLMProvider port using Anthropic's API
    through LangChain's ChatAnthropic integration.
    """

    def __init__(self):
        """Initialize the Anthropic provider with configured model."""
        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not configured. "
                "Please set ANTHROPIC_API_KEY in your .env file."
            )

        if not settings.anthropic_model:
            raise ValueError(
                "ANTHROPIC_MODEL is not configured. "
                "Please set ANTHROPIC_MODEL in your .env file (e.g., claude-3-sonnet-20240229)."
            )

        self.model = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=0.7,
            streaming=True
        )
        logger.info(f"Initialized Anthropic provider with model: {settings.anthropic_model}")

    async def generate(self, messages: List[BaseMessage]) -> str:
        """
        Generate a response from Anthropic based on conversation history.

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
            logger.error(f"Anthropic generation failed: {e}")
            raise Exception(f"Failed to generate response from Anthropic: {str(e)}")

    async def stream(self, messages: List[BaseMessage]) -> AsyncGenerator[str, None]:
        """
        Stream a response from Anthropic token-by-token.

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
            logger.error(f"Anthropic streaming failed: {e}")
            raise Exception(f"Failed to stream response from Anthropic: {str(e)}")

    async def get_model_name(self) -> str:
        """
        Get the name of the current Anthropic model being used.

        Returns:
            Model name (e.g., "claude-3-sonnet-20240229")
        """
        return settings.anthropic_model
