# ABOUTME: Google Gemini LLM provider implementation using LangChain
# ABOUTME: Implements ILLMProvider port interface for Google Gemini models with native BaseMessage support

from typing import List, AsyncGenerator, Callable, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage

from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class GeminiProvider(ILLMProvider):
    """
    Google Gemini LLM provider implementation.

    This adapter implements the ILLMProvider port using Google's Gemini API
    through LangChain's ChatGoogleGenerativeAI integration. Works directly with
    LangChain BaseMessage types (HumanMessage, AIMessage, SystemMessage).
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

    async def generate(self, messages: List[BaseMessage]) -> BaseMessage:
        """
        Generate a response from Gemini based on conversation history.

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
            logger.error(f"Gemini generation failed: {e}")
            raise Exception(f"Failed to generate response from Gemini: {str(e)}")

    async def stream(self, messages: List[BaseMessage]) -> AsyncGenerator[str, None]:
        """
        Stream a response from Gemini token-by-token.

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
            logger.error(f"Gemini streaming failed: {e}")
            raise Exception(f"Failed to stream response from Gemini: {str(e)}")

    async def get_model_name(self) -> str:
        """
        Get the name of the current Gemini model being used.

        Returns:
            Model name (e.g., "gemini-2.0-flash")
        """
        return settings.google_model

    def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
        """
        Bind tools to the Gemini provider for tool calling.

        Args:
            tools: List of callable tools to bind
            **kwargs: Additional keyword arguments for binding

        Returns:
            A new GeminiProvider instance with tools bound
        """
        bound_model = self.model.bind_tools(tools, **kwargs)
        # Create a new instance with the bound model
        new_provider = GeminiProvider.__new__(GeminiProvider)
        new_provider.model = bound_model
        return new_provider
