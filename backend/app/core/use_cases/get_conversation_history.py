# ABOUTME: GetConversationHistory use case implementing conversation history retrieval business logic
# ABOUTME: Handles fetching messages for a conversation with pagination

from typing import List

from app.core.domain.message import Message
from app.core.ports.message_repository import IMessageRepository
from app.core.ports.conversation_repository import IConversationRepository


class GetConversationHistory:
    """
    Use case for retrieving conversation history.

    This use case encapsulates the business logic for retrieving
    all messages in a conversation with pagination support.
    It depends only on port interfaces, not concrete implementations.
    """

    def __init__(
        self,
        message_repository: IMessageRepository,
        conversation_repository: IConversationRepository
    ):
        """
        Initialize the GetConversationHistory use case.

        Args:
            message_repository: Message repository port for data operations
            conversation_repository: Conversation repository port for validation
        """
        self.message_repository = message_repository
        self.conversation_repository = conversation_repository

    async def execute(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """
        Execute the get conversation history use case.

        Args:
            conversation_id: ID of the conversation
            skip: Number of messages to skip (for pagination)
            limit: Maximum number of messages to return

        Returns:
            List of messages ordered by creation time

        Raises:
            ValueError: If conversation doesn't exist
        """
        conversation = await self.conversation_repository.get_by_id(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        messages = await self.message_repository.get_by_conversation_id(
            conversation_id,
            skip=skip,
            limit=limit
        )

        return messages
