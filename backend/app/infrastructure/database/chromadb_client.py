# ABOUTME: ChromaDB vector database client initialization and lifecycle management
# ABOUTME: Manages connection to ChromaDB (embedded or HTTP) and provides global access

import chromadb
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class ChromaDBClient:
    """ChromaDB vector database client manager."""

    client = None

    @classmethod
    async def initialize(cls):
        """Initialize ChromaDB client based on configuration."""
        try:
            if settings.chroma_mode == "embedded":
                logger.info(f"Initializing embedded ChromaDB at {settings.chroma_persist_directory}")
                cls.client = chromadb.PersistentClient(
                    path=settings.chroma_persist_directory
                )
            elif settings.chroma_mode == "http":
                logger.info(f"Connecting to ChromaDB at {settings.chroma_host}:{settings.chroma_port}")
                cls.client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port
                )
            else:
                raise ValueError(f"Invalid chroma_mode: {settings.chroma_mode}")

            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    @classmethod
    def close(cls):
        """Close ChromaDB client if needed."""
        if cls.client:
            logger.info("Closing ChromaDB client")
            cls.client = None
