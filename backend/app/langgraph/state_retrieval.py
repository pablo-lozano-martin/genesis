# ABOUTME: LangGraph state retrieval utilities for accessing checkpoint data
# ABOUTME: Provides helpers to retrieve messages from LangGraph checkpoints

from typing import List
from langgraph.types import RunnableConfig
from langchain_core.messages import BaseMessage
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def get_conversation_messages(graph, conversation_id: str) -> List[BaseMessage]:
    """
    Retrieve messages from LangGraph checkpoint for a conversation.

    Args:
        graph: Compiled LangGraph instance with checkpointing
        conversation_id: UUID of the conversation (maps to thread_id)

    Returns:
        List of BaseMessage objects (HumanMessage, AIMessage, SystemMessage, ToolMessage)
        representing the complete conversation history. Note: Callers should filter
        tool messages and intermediate AI tool-call messages before exposing to frontend.
    """
    try:
        # Create config with thread_id (conversation.id)
        config = RunnableConfig(
            configurable={"thread_id": conversation_id}
        )

        # Get state from checkpoint
        state = await graph.aget_state(config)

        # Extract messages from state
        messages = state.values.get("messages", [])

        logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
        
        return messages

    except Exception as e:
        logger.error(f"Failed to retrieve messages for conversation {conversation_id}: {e}")
        return []
