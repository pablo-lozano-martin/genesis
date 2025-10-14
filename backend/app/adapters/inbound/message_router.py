# ABOUTME: Message REST API endpoints for conversation message history
# ABOUTME: Provides read access to conversation messages

from typing import List
from fastapi import APIRouter, HTTPException, status, Query
from app.core.domain.message import MessageResponse
from app.infrastructure.security.dependencies import CurrentUser
from app.adapters.outbound.repositories.mongo_message_repository import MongoMessageRepository
from app.adapters.outbound.repositories.mongo_conversation_repository import MongoConversationRepository
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["messages"])

message_repository = MongoMessageRepository()
conversation_repository = MongoConversationRepository()


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0, description="Number of messages to skip"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of messages to return")
):
    """
    Get all messages for a specific conversation.

    Returns messages ordered by creation time (oldest first).
    Only the conversation owner can access the messages.
    """
    logger.info(f"Getting messages for conversation {conversation_id} (skip={skip}, limit={limit})")

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

    messages = await message_repository.get_by_conversation_id(
        conversation_id=conversation_id,
        skip=skip,
        limit=limit
    )

    logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")

    return [
        MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            metadata=msg.metadata
        )
        for msg in messages
    ]
