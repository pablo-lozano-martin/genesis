# ABOUTME: Message REST API endpoints for conversation message history
# ABOUTME: Retrieves messages from LangGraph checkpoints instead of message repository

from typing import List
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Query, Request
from app.adapters.inbound.message_schemas import MessageResponse, MessageRole
from app.infrastructure.security.dependencies import CurrentUser
from app.adapters.outbound.repositories.mongo_conversation_repository import MongoConversationRepository
from app.langgraph.state_retrieval import get_conversation_messages
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["messages"])

conversation_repository = MongoConversationRepository()


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages_endpoint(
    conversation_id: str,
    request: Request,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0, description="Number of messages to skip"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of messages to return")
):
    """
    Get all messages for a specific conversation from LangGraph checkpoint.

    Returns messages ordered by creation time (oldest first).
    Only the conversation owner can access the messages.
    Messages are retrieved from LangGraph checkpoint state.
    """
    logger.info(f"Getting messages for conversation {conversation_id} (skip={skip}, limit={limit})")

    # Verify conversation ownership (authorization at App DB layer)
    conversation = await conversation_repository.get_by_id(conversation_id)

    if not conversation:
        logger.warning(f"Conversation {conversation_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted to access messages in conversation {conversation_id} owned by {conversation.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get compiled graph from app state
    graph = request.app.state.chat_graph

    # Retrieve messages from LangGraph checkpoint
    base_messages = await get_conversation_messages(graph, conversation_id)

    # Convert BaseMessage objects to MessageResponse format
    # Filter out internal execution details (tool calls/responses)
    messages = []
    for msg in base_messages:
        # Skip tool messages (internal LangGraph execution details)
        if msg.type == "tool":
            continue

        # Skip AI messages that only contain tool_calls without content
        # These are intermediate execution steps, not user-facing responses
        if msg.type == "ai":
            has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
            has_content = msg.content and msg.content.strip()
            if has_tool_calls and not has_content:
                continue

        # Map LangChain message types to our MessageRole
        if msg.type == "human":
            role = MessageRole.USER
        elif msg.type == "ai":
            role = MessageRole.ASSISTANT
        elif msg.type == "system":
            role = MessageRole.SYSTEM
        else:
            role = MessageRole.USER  # Default fallback

        messages.append(
            MessageResponse(
                id=str(uuid4()),  # Generate ID since BaseMessage doesn't have one
                conversation_id=conversation_id,
                role=role,
                content=msg.content,
                created_at=datetime.utcnow(),  # BaseMessage doesn't store timestamp
                metadata=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {}
            )
        )

    # Apply pagination
    paginated_messages = messages[skip:skip + limit]

    logger.info(f"Retrieved {len(paginated_messages)} messages (out of {len(messages)} total) for conversation {conversation_id}")

    return paginated_messages
