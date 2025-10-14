# ABOUTME: LLM provider factory for creating provider instances based on configuration
# ABOUTME: Selects appropriate provider (OpenAI, Anthropic, Gemini, Ollama) based on settings

from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.

    This factory selects the appropriate LLM provider based on the
    application configuration (LLM_PROVIDER environment variable).
    """

    @staticmethod
    def create_provider() -> ILLMProvider:
        """
        Create an LLM provider instance based on configuration.

        Returns:
            ILLMProvider instance (OpenAI, Anthropic, Gemini, or Ollama)

        Raises:
            ValueError: If the configured provider is not supported
        """
        provider_name = settings.llm_provider.lower()

        logger.info(f"Creating LLM provider: {provider_name}")

        if provider_name == "openai":
            from app.adapters.outbound.llm_providers.openai_provider import OpenAIProvider
            return OpenAIProvider()

        elif provider_name == "anthropic":
            from app.adapters.outbound.llm_providers.anthropic_provider import AnthropicProvider
            return AnthropicProvider()

        elif provider_name == "gemini":
            from app.adapters.outbound.llm_providers.gemini_provider import GeminiProvider
            return GeminiProvider()

        elif provider_name == "ollama":
            from app.adapters.outbound.llm_providers.ollama_provider import OllamaProvider
            return OllamaProvider()

        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider_name}. "
                f"Supported providers: openai, anthropic, gemini, ollama"
            )


def get_llm_provider() -> ILLMProvider:
    """
    Get the configured LLM provider instance.

    This is a convenience function that uses the factory to create
    a provider instance.

    Returns:
        ILLMProvider instance
    """
    return LLMProviderFactory.create_provider()
