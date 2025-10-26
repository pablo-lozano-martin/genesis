# ABOUTME: Application settings and configuration management using Pydantic Settings
# ABOUTME: Loads environment variables and provides type-safe access to configuration values

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application Settings
    app_name: str = "Genesis"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Database Settings
    mongodb_url: str = "mongodb://mongodb:27017"  # Kept for backward compatibility
    mongodb_db_name: str = "genesis"  # Kept for backward compatibility

    # Dual Database Settings
    mongodb_app_url: str = "mongodb://mongodb:27017"
    mongodb_app_db_name: str = "genesis_app"
    mongodb_langgraph_url: str = "mongodb://mongodb:27017"
    mongodb_langgraph_db_name: str = "genesis_langgraph"

    # Security Settings
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # LLM Provider Settings
    llm_provider: str = "openai"  # openai, anthropic, gemini, ollama

    # OpenAI Settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"

    # Anthropic Settings
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"

    # Google Settings
    google_api_key: Optional[str] = None
    google_model: str = "gemini-pro"

    # Ollama Settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    # CORS Settings
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://frontend:3000",
        "http://frontend:5173"
    ]

    # Logging Settings
    log_level: str = "INFO"

    # ChromaDB Settings
    chroma_mode: str = "embedded"  # "embedded" or "http"
    chroma_persist_directory: str = "./chroma_db"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_collection_name: str = "genesis_documents"

    # Retrieval Settings
    retrieval_top_k: int = 5
    retrieval_similarity_threshold: float = 0.5
    retrieval_chunk_size: int = 512
    retrieval_chunk_overlap: int = 50


# Global settings instance
settings = Settings()
