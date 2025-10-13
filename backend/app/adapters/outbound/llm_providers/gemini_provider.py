# ABOUTME: Google Gemini LLM provider implementation using langchain-google-genai
# ABOUTME: Implements ILLMProvider port interface for Google Gemini models

from typing import List, AsyncGenerator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.ports.llm_provider import ILLMProvider
from app.core.domain.message import Message, MessageRole
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class GeminiProvider(ILLMProvider):
    """
    Google Gemini LLM provider implementation.

    Uses langchain-google-genai to communicate with Google's Gemini models.
    This adapter implements the ILLMProvider port.
    """

    def __init__(self):
        """Initialize Gemini provider with settings."""
        if not settings.google_api_key:
            raise ValueError("Google API key is required but not set in environment")

        self.model = ChatGoogleGenerativeAI(
            google_api_key=settings.google_api_key,
            model=settings.google_model,
            temperature=0.7,
            convert_system_message_to_human=True
        )
        logger.info(f"Initialized Gemini provider with model: {settings.google_model}")

    def _convert_to_langchain_messages(self, messages: List[Message]):
        """Convert domain messages to LangChain message format."""
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
        Generate a response from Google Gemini based on conversation history.

        Args:
            messages: List of messages representing the conversation history

        Returns:
            Generated response text

        Raises:
            Exception: If Gemini generation fails
        """
        try:
            langchain_messages = self._convert_to_langchain_messages(messages)
            response = await self.model.ainvoke(langchain_messages)
            return response.content
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    async def stream(self, messages: List[Message]) -> AsyncGenerator[str, None]:
        """
        Stream a response from Google Gemini token-by-token.

        Args:
            messages: List of messages representing the conversation history

        Yields:
            Response tokens as they are generated

        Raises:
            Exception: If Gemini streaming fails
        """
        try:
            langchain_messages = self._convert_to_langchain_messages(messages)

            async for chunk in self.model.astream(langchain_messages):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            raise

    async def get_model_name(self) -> str:
        """
        Get the name of the current Gemini model being used.

        Returns:
            Model name (e.g., "gemini-pro")
        """
        return settings.google_model
