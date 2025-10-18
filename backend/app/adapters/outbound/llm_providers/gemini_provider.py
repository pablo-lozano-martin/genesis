# ABOUTME: Google Gemini LLM provider implementation using LangChain
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

    This adapter implements the ILLMProvider port using Google's Gemini API
    through LangChain's ChatGoogleGenerativeAI integration.
    """

    def __init__(self):
        """Initialize the Gemini provider with configured model."""
        if not settings.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not configured. "
                "Please set GOOGLE_API_KEY in your .env file."
            )

        if not settings.google_model:
            raise ValueError(
                "GOOGLE_MODEL is not configured. "
                "Please set GOOGLE_MODEL in your .env file (e.g., gemini-2.0-flash)."
            )

        self.model = ChatGoogleGenerativeAI(
            model=settings.google_model,
            google_api_key=settings.google_api_key,
            temperature=0.7,
            streaming=True
        )
        logger.info(f"Initialized Gemini provider with model: {settings.google_model}")

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
        Generate a response from Gemini based on conversation history.

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
            logger.error(f"Gemini generation failed: {e}")
            raise Exception(f"Failed to generate response from Gemini: {str(e)}")

    async def stream(self, messages: List[Message]) -> AsyncGenerator[str, None]:
        """
        Stream a response from Gemini token-by-token.

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
            logger.error(f"Gemini streaming failed: {e}")
            raise Exception(f"Failed to stream response from Gemini: {str(e)}")

    async def get_model_name(self) -> str:
        """
        Get the name of the current Gemini model being used.

        Returns:
            Model name (e.g., "gemini-2.0-flash")
        """
        return settings.google_model
