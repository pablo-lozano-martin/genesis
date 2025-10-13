# ABOUTME: LLM provider factory for creating provider instances based on configuration
# ABOUTME: Handles provider selection and instantiation with error handling

from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.

    Selects the appropriate provider based on the LLM_PROVIDER
    environment variable and instantiates it.
    """

    @staticmethod
    def create_provider() -> ILLMProvider:
        """
        Create and return an LLM provider instance.

        Returns:
            Configured LLM provider instance

        Raises:
            ValueError: If provider type is unknown or configuration is invalid
        """
        provider_type = settings.llm_provider.lower()

        logger.info(f"Creating LLM provider: {provider_type}")

        if provider_type == "openai":
            from app.adapters.outbound.llm_providers.openai_provider import OpenAIProvider
            return OpenAIProvider()

        elif provider_type == "anthropic":
            from app.adapters.outbound.llm_providers.anthropic_provider import AnthropicProvider
            return AnthropicProvider()

        elif provider_type == "gemini":
            from app.adapters.outbound.llm_providers.gemini_provider import GeminiProvider
            return GeminiProvider()

        elif provider_type == "ollama":
            from app.adapters.outbound.llm_providers.ollama_provider import OllamaProvider
            return OllamaProvider()

        else:
            raise ValueError(
                f"Unknown LLM provider: {provider_type}. "
                f"Supported providers: openai, anthropic, gemini, ollama"
            )


def get_llm_provider() -> ILLMProvider:
    """
    Convenience function to get the configured LLM provider.

    Returns:
        Configured LLM provider instance
    """
    return LLMProviderFactory.create_provider()
