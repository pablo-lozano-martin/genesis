# ABOUTME: MongoDB database connection and Beanie ODM initialization
# ABOUTME: Handles database connection lifecycle and document model registration

from typing import List, Type
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, init_beanie

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class MongoDB:
    """MongoDB connection manager."""

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
            logger.info(f"Connecting to MongoDB at {settings.mongodb_url}")
            cls.client = AsyncIOMotorClient(settings.mongodb_url)
            cls.database = cls.client[settings.mongodb_db_name]

            await init_beanie(
                database=cls.database,
                document_models=document_models
            )

            logger.info(f"Successfully connected to MongoDB database: {settings.mongodb_db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def close(cls) -> None:
        """Close the MongoDB connection."""
        if cls.client:
            logger.info("Closing MongoDB connection")
            cls.client.close()
