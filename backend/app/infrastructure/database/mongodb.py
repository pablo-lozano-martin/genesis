# ABOUTME: MongoDB database connection and Beanie ODM initialization
# ABOUTME: Handles database connection lifecycle and document model registration for both App and LangGraph databases

from typing import List, Type
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, init_beanie

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class AppDatabase:
    """Application database connection manager for users and conversations metadata."""

    client: AsyncIOMotorClient = None
    database = None

    @classmethod
    async def connect(cls, document_models: List[Type[Document]]) -> None:
        """
        Connect to MongoDB and initialize Beanie with document models.

        Args:
            document_models: List of Beanie document model classes to register
        """
        try:
            logger.info(f"Connecting to App Database at {settings.mongodb_app_url}")
            cls.client = AsyncIOMotorClient(settings.mongodb_app_url)
            cls.database = cls.client[settings.mongodb_app_db_name]

            await init_beanie(
                database=cls.database,
                document_models=document_models
            )

            logger.info(f"Successfully connected to App Database: {settings.mongodb_app_db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to App Database: {e}")
            raise

    @classmethod
    async def close(cls) -> None:
        """Close the App Database connection."""
        if cls.client:
            logger.info("Closing App Database connection")
            cls.client.close()


class LangGraphDatabase:
    """LangGraph database connection manager for checkpoints and message history."""

    client: AsyncIOMotorClient = None
    database = None

    @classmethod
    async def connect(cls) -> None:
        """Connect to LangGraph database for checkpointing."""
        try:
            logger.info(f"Connecting to LangGraph Database at {settings.mongodb_langgraph_url}")
            cls.client = AsyncIOMotorClient(settings.mongodb_langgraph_url)
            cls.database = cls.client[settings.mongodb_langgraph_db_name]

            logger.info(f"Successfully connected to LangGraph Database: {settings.mongodb_langgraph_db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to LangGraph Database: {e}")
            raise

    @classmethod
    async def close(cls) -> None:
        """Close the LangGraph Database connection."""
        if cls.client:
            logger.info("Closing LangGraph Database connection")
            cls.client.close()


# Backward compatibility alias
MongoDB = AppDatabase
