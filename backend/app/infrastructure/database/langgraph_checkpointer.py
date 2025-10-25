# ABOUTME: LangGraph checkpointer setup and factory for MongoDB-based checkpoint storage
# ABOUTME: Provides checkpointer instance for LangGraph graph compilation

from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def get_checkpointer() -> AsyncMongoDBSaver:
    """
    Get LangGraph checkpointer instance for MongoDB-based state persistence.

    Uses from_conn_string() as per LangGraph documentation and manually enters
    the async context manager to keep the checkpointer alive for the application lifetime.

    Returns:
        AsyncMongoDBSaver: Checkpointer for LangGraph state persistence
    """
    logger.info("Creating LangGraph AsyncMongoDBSaver checkpointer")

    # Use from_conn_string as shown in LangGraph documentation
    # Manually enter the context manager for long-running applications
    conn_string = settings.mongodb_langgraph_url
    checkpointer = AsyncMongoDBSaver.from_conn_string(conn_string)
    return await checkpointer.__aenter__()
