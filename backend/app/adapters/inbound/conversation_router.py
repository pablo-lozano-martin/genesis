# ABOUTME: Conversation REST API endpoints for conversation management
# ABOUTME: Provides CRUD operations for user conversations

from typing import List
from fastapi import APIRouter, HTTPException, status, Query
from app.core.domain.conversation import ConversationCreate, ConversationUpdate, ConversationResponse
from app.core.domain.user import User
from app.infrastructure.security.dependencies import CurrentUser
from app.adapters.outbound.repositories.mongo_conversation_repository import MongoConversationRepository
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

conversation_repository = MongoConversationRepository()


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Maximum number of conversations to return")
):
    """
    List all conversations for the current user.

    Returns conversations ordered by most recently updated first.
    """
    logger.info(f"Listing conversations for user {current_user.id} (skip={skip}, limit={limit})")

    conversations = await conversation_repository.get_by_user_id(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

    return [
        ConversationResponse(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=conv.message_count
        )
        for conv in conversations
    ]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: CurrentUser
):
    """
    Create a new conversation for the current user.
    """
    logger.info(f"Creating conversation for user {current_user.id}")

    conversation = await conversation_repository.create(
        user_id=current_user.id,
        conversation_data=conversation_data
    )

    logger.info(f"Created conversation {conversation.id} for user {current_user.id}")

    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=conversation.message_count
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: CurrentUser
):
    """
    Get a specific conversation by ID.

    Returns 404 if conversation doesn't exist or doesn't belong to the user.
    """
    logger.info(f"Getting conversation {conversation_id} for user {current_user.id}")

    conversation = await conversation_repository.get_by_id(conversation_id)

    if not conversation:
        logger.warning(f"Conversation {conversation_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted to access conversation {conversation_id} owned by {conversation.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=conversation.message_count
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    conversation_data: ConversationUpdate,
    current_user: CurrentUser
):
    """
    Update a conversation's details.

    Currently supports updating the title.
    """
    logger.info(f"Updating conversation {conversation_id} for user {current_user.id}")

    conversation = await conversation_repository.get_by_id(conversation_id)

    if not conversation:
        logger.warning(f"Conversation {conversation_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted to update conversation {conversation_id} owned by {conversation.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    updated_conversation = await conversation_repository.update(conversation_id, conversation_data)

    logger.info(f"Updated conversation {conversation_id}")

    return ConversationResponse(
        id=updated_conversation.id,
        user_id=updated_conversation.user_id,
        title=updated_conversation.title,
        created_at=updated_conversation.created_at,
        updated_at=updated_conversation.updated_at,
        message_count=updated_conversation.message_count
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser
):
    """
    Delete a conversation and all its messages.

    This operation is irreversible.
    """
    logger.info(f"Deleting conversation {conversation_id} for user {current_user.id}")

    conversation = await conversation_repository.get_by_id(conversation_id)

    if not conversation:
        logger.warning(f"Conversation {conversation_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted to delete conversation {conversation_id} owned by {conversation.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    await conversation_repository.delete(conversation_id)

    logger.info(f"Deleted conversation {conversation_id}")
