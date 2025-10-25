# ABOUTME: Unit tests for LLM provider implementations
# ABOUTME: Tests provider factory

import pytest
from unittest.mock import AsyncMock, patch

from app.adapters.outbound.llm_providers.provider_factory import LLMProviderFactory


@pytest.mark.unit
class TestLLMProviderFactory:
    """Tests for LLM provider factory."""

    @patch("app.adapters.outbound.llm_providers.provider_factory.settings")
    def test_create_openai_provider(self, mock_settings):
        """Test creating OpenAI provider."""
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4"

        provider = LLMProviderFactory.create_provider()

        assert provider is not None
        assert provider.__class__.__name__ == "OpenAIProvider"

    @patch("app.adapters.outbound.llm_providers.provider_factory.settings")
    def test_create_anthropic_provider(self, mock_settings):
        """Test creating Anthropic provider."""
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_model = "claude-3-sonnet-20240229"

        provider = LLMProviderFactory.create_provider()

        assert provider is not None
        assert provider.__class__.__name__ == "AnthropicProvider"

    @patch("app.adapters.outbound.llm_providers.provider_factory.settings")
    def test_create_gemini_provider(self, mock_settings):
        """Test creating Gemini provider."""
        mock_settings.llm_provider = "gemini"
        mock_settings.google_api_key = "test-key"
        mock_settings.google_model = "gemini-2.0-flash"

        provider = LLMProviderFactory.create_provider()

        assert provider is not None
        assert provider.__class__.__name__ == "GeminiProvider"

    @patch("app.adapters.outbound.llm_providers.provider_factory.settings")
    def test_create_ollama_provider(self, mock_settings):
        """Test creating Ollama provider."""
        mock_settings.llm_provider = "ollama"
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model = "llama2"

        provider = LLMProviderFactory.create_provider()

        assert provider is not None
        assert provider.__class__.__name__ == "OllamaProvider"

    @patch("app.adapters.outbound.llm_providers.provider_factory.settings")
    def test_create_unsupported_provider(self, mock_settings):
        """Test creating unsupported provider raises error."""
        mock_settings.llm_provider = "unsupported"

        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            LLMProviderFactory.create_provider()
