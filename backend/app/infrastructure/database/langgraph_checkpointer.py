# ABOUTME: LangGraph checkpointer setup and factory for MongoDB-based checkpoint storage
# ABOUTME: Provides checkpointer instance for LangGraph graph compilation

from typing import Tuple
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def get_checkpointer() -> Tuple[AsyncMongoDBSaver, AsyncMongoDBSaver]:
    """
    Get LangGraph checkpointer instance for MongoDB-based state persistence.

    Uses from_conn_string() as per LangGraph documentation and manually enters
    the async context manager to keep the checkpointer alive for the application lifetime.

    Returns:
        Tuple of (context_manager, checkpointer_instance):
        - context_manager: The async context manager for proper cleanup on shutdown
        - checkpointer_instance: The actual AsyncMongoDBSaver to use for checkpointing
    """
    logger.info("Creating LangGraph AsyncMongoDBSaver checkpointer")

    # Use from_conn_string as shown in LangGraph documentation
    # Manually manage the context for long-running applications
    conn_string = settings.mongodb_langgraph_url
    checkpointer_context = AsyncMongoDBSaver.from_conn_string(conn_string)

    # Enter the context and return both the context and the actual checkpointer
    checkpointer_instance = await checkpointer_context.__aenter__()

    return checkpointer_context, checkpointer_instance
