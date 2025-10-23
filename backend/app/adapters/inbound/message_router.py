# ABOUTME: Message REST API endpoints for conversation message history
# ABOUTME: Provides read access to conversation messages

from typing import List
from fastapi import APIRouter, HTTPException, status, Query
from app.core.domain.message import MessageResponse, MessageCreateRequest, MessagePairResponse
from app.infrastructure.security.dependencies import CurrentUser
from app.adapters.outbound.repositories.mongo_message_repository import MongoMessageRepository
from app.adapters.outbound.repositories.mongo_conversation_repository import MongoConversationRepository
from app.infrastructure.config.logging_config import get_logger
from app.core.use_cases.send_message import SendMessage
from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider

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


@router.post(
    "/{conversation_id}/messages",
    response_model=MessagePairResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_message(
    conversation_id: str,
    message_data: MessageCreateRequest,
    current_user: CurrentUser
):
    """
    Create a message in a conversation and generate LLM response.

    This endpoint:
    1. Validates user owns the conversation
    2. Saves the user's message
    3. Calls the LLM provider with conversation history
    4. Saves the assistant's response
    5. Updates conversation message count

    Returns both messages (user and assistant) in the response.

    Args:
        conversation_id: ID of the conversation
        message_data: Request body with message content
        current_user: Authenticated user from dependency

    Returns:
        MessagePairResponse with user and assistant messages

    Raises:
        HTTPException:
            - 404 if conversation not found
            - 403 if user doesn't own conversation
            - 422 if validation fails
            - 500 if LLM provider fails
    """
    logger.info(f"Creating message in conversation {conversation_id} for user {current_user.id}")

    conversation = await conversation_repository.get_by_id(conversation_id)

    if not conversation:
        logger.warning(f"Conversation {conversation_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id:
        logger.warning(
            f"User {current_user.id} attempted to access conversation "
            f"{conversation_id} owned by {conversation.user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    llm_provider = get_llm_provider()
    send_message_use_case = SendMessage(
        message_repository=message_repository,
        conversation_repository=conversation_repository,
        llm_provider=llm_provider
    )

    try:
        user_message, assistant_message = await send_message_use_case.execute(
            conversation_id=conversation_id,
            user_message_content=message_data.content
        )

        logger.info(f"Created message pair in conversation {conversation_id}")

        return MessagePairResponse(
            user_message=MessageResponse(
                id=user_message.id,
                conversation_id=user_message.conversation_id,
                role=user_message.role,
                content=user_message.content,
                created_at=user_message.created_at,
                metadata=user_message.metadata
            ),
            assistant_message=MessageResponse(
                id=assistant_message.id,
                conversation_id=assistant_message.conversation_id,
                role=assistant_message.role,
                content=assistant_message.content,
                created_at=assistant_message.created_at,
                metadata=assistant_message.metadata
            )
        )

    except ValueError as e:
        logger.error(f"Validation error creating message: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating message in conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response"
        )
