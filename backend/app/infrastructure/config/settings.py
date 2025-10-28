# ABOUTME: Application settings and configuration management using Pydantic Settings
# ABOUTME: Loads environment variables and provides type-safe access to configuration values

import json
from pathlib import Path
from typing import Optional
from pydantic import field_validator
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

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

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

    # MCP Settings
    mcp_enabled: bool = False
    mcp_config_path: str = "./genesis_mcp.json"

    @property
    def get_mcp_servers(self) -> list[dict]:
        """
        Load MCP servers from config file in standard format.

        Expected format (standard MCP format):
        {
          "mcpServers": {
            "server-name": {
              "command": "python",
              "args": ["-m", "mcp_server_fetch"],
              "env": {"KEY": "value"}  // optional
            }
          }
        }

        Returns list of server configs with normalized structure:
        [
          {
            "name": "server-name",
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "mcp_server_fetch"],
            "env": {"KEY": "value"}
          }
        ]
        """
        if not self.mcp_enabled:
            return []

        config_path = Path(self.mcp_config_path)
        if not config_path.exists():
            return []

        try:
            from app.infrastructure.config.logging_config import get_logger
            logger = get_logger(__name__)

            config = json.loads(config_path.read_text())

            # Parse standard MCP format
            if "mcpServers" not in config:
                logger.error("Invalid MCP config: missing 'mcpServers' key")
                return []

            servers = []
            for server_name, server_config in config["mcpServers"].items():
                # Validate required fields
                if "command" not in server_config:
                    logger.error(f"MCP server '{server_name}' missing required 'command' field")
                    continue

                # Normalize to internal format
                normalized = {
                    "name": server_name,
                    "transport": "stdio",  # Default transport
                    "command": server_config["command"],
                    "args": server_config.get("args", []),
                    "env": server_config.get("env", {})
                }
                servers.append(normalized)

            logger.info(f"Loaded {len(servers)} MCP server(s) from config")
            return servers

        except Exception as e:
            from app.infrastructure.config.logging_config import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to load MCP config: {e}")
            return []


# Global settings instance
settings = Settings()
