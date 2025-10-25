# ABOUTME: LangGraph checkpointer setup and factory for MongoDB-based checkpoint storage
# ABOUTME: Provides checkpointer instance for LangGraph graph compilation

from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver

from app.infrastructure.database.mongodb import LangGraphDatabase
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def get_checkpointer() -> AsyncMongoDBSaver:
    """
    Get LangGraph checkpointer instance using LangGraphDatabase connection.

    Returns:
        AsyncMongoDBSaver: Checkpointer for LangGraph state persistence
    """
    if not LangGraphDatabase.client:
        raise RuntimeError("LangGraphDatabase not connected. Call LangGraphDatabase.connect() first.")

    logger.info("Creating LangGraph AsyncMongoDBSaver checkpointer")

    # Use from_conn_string as shown in LangGraph documentation
    conn_string = settings.mongodb_langgraph_url
    return await AsyncMongoDBSaver.from_conn_string(conn_string).__aenter__()
